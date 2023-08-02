import re
from copy import deepcopy
from itertools import product

import cachecontrol
import requests
import yaml

from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS
from model.build_group import BuildGroup

# Matches ${{ matrix.(name) }}, where (name) is anything that isn't a space or '}'.
# match.group(1) is the name of the matrix variable.
MATRIX_INTERPOLATE_REGEX = re.compile(r'\${{\s*matrix\.([^\s}]+)\s*}}')


class RecoverableException(Exception):
    pass


def flatten_dict_keys(d, prefix=None):
    """
    Given a nested dict {'a': {'b': {'c': 1}, {'d': 2}}, 'e'}, yields the
    key of each leaf node in dot notation ('a.b.c', 'a.b.d', 'a.e').
    """
    if isinstance(d, dict):
        for k, v in d.items():
            next_prefix = k if prefix is None else '{}.{}'.format(prefix, k)
            yield from flatten_dict_keys(v, next_prefix)
    else:
        yield prefix


def flatten_elements(item, result):
    if isinstance(item, list):
        for i in item:
            flatten_elements(i, result)
    elif isinstance(item, dict):
        for i in item.values():
            flatten_elements(i, result)
    elif isinstance(item, bool):
        result.append(str(item).lower())
    else:
        result.append(str(item))


def get_job_api_name(base_name: str, matrix_combination, default_keys, job_matrix):
    """
    Finds the job's API name by interpolating the appropriate matrix variables.
    """

    # If a job's name has no interpolated variables, it defaults to the name
    # followed by a comma-separated list of the default matrix values.
    interpolations = []
    for key in default_keys:
        if key in matrix_combination and matrix_combination[key] != '':
            # Handle nested dicts, e.g. https://github.com/Robert-Furth/actions-test/actions/runs/2835879042
            for flattened_key in flatten_dict_keys(matrix_combination[key], key):
                interpolations.append('${{{{ matrix.{} }}}}'.format(flattened_key))

    # Fix test_expand_config_matrix_with_includes_4,5,6
    add_non_defaults_key = False
    for key, val in matrix_combination.items():
        if key in default_keys:
            if val not in job_matrix.get(key, {}):
                add_non_defaults_key = True
        elif add_non_defaults_key:
            if val != '':
                for flattened_key in flatten_dict_keys(matrix_combination[key], key):
                    interpolations.append('${{{{ matrix.{} }}}}'.format(flattened_key))

    intermediate_name = base_name
    if interpolations and not re.search(MATRIX_INTERPOLATE_REGEX, intermediate_name):
        intermediate_name = '{} ({})'.format(base_name, ', '.join(interpolations))

    # Find the start/end indexes of all interpolated matrix variables.
    indexes = []
    for match in re.finditer(MATRIX_INTERPOLATE_REGEX, intermediate_name):
        # Handle dot-indexing of nested dicts.
        # e.g. ${{ matrix.foo.bar }} -> matrix_combination['foo']['bar']
        keys = [key.lower() for key in match.group(1).split('.')]
        value = matrix_combination
        for key in keys:
            value = value[key] if isinstance(value, dict) and key in value else ''

        value_list = []
        flatten_elements(value, value_list)
        value = ', '.join(value_list)
        indexes.append((match.start(), match.end(), str(value)))

    # Interpolate
    job_name = intermediate_name
    for start, end, value in reversed(indexes):
        job_name = job_name[:start] + value + job_name[end:]

    job_name = job_name.strip()

    # Job names over 100 characters are truncated, *even in the API*
    # https://api.github.com/repos/apache/zookeeper/actions/runs/1189465687/jobs
    if len(job_name) > 100:
        job_name = job_name[:97] + '...'

    return job_name


def partial_match(d1, d2):
    if not isinstance(d1, dict) or not isinstance(d2, dict):
        return d1 == d2

    for key, val in d1.items():
        if key in d2 and not partial_match(val, d2[key]):
            return False
    return True


def lowercase_dict_keys(d):
    """
    Recursively convert all string keys in `d` to lowercase.
    """
    if isinstance(d, dict):
        lowercased = {}
        for k, v in d.items():
            if isinstance(k, str):
                k = k.lower()
            lowercased[k] = lowercase_dict_keys(v)
        return lowercased
    elif isinstance(d, list):
        return [lowercase_dict_keys(x) for x in d]
    else:
        return d


def build_combinations(job_matrix):
    """
    Given a GHA job matrix, generate all possible permutations of that
    matrix, taking into account include and exclude rules.
    """

    # Separate matrix includes and excludes
    job_matrix = lowercase_dict_keys(job_matrix)
    includes = excludes = []
    if 'include' in job_matrix:
        includes = job_matrix['include']
        del job_matrix['include']
    if 'exclude' in job_matrix:
        excludes = job_matrix['exclude']
        del job_matrix['exclude']

    if len(job_matrix) == 0:
        combinations = []
    else:
        # Separate matrix keys and values into their own lists
        keys, values = zip(*job_matrix.items())
        # For each combination of values, generate {key1: value1, key2: value2, ...}
        combinations = [dict(zip(keys, prod)) for prod in product(*values)]

    # Indicates whether an include needs to be appended to the end of combinations
    includes_used = [False for _ in includes]

    # Handle excludes first
    i = 0
    while i < len(combinations):
        matrix = combinations[i]
        for exclude in excludes:
            if partial_match(exclude, matrix):
                del combinations[i]
                break
        else:
            i += 1

    # Handle includes with partial matches
    for i, matrix in enumerate(combinations):
        updated_matrix = deepcopy(matrix)
        for j, include in enumerate(includes):
            if partial_match(include, matrix):
                updated_matrix.update(include)
                includes_used[j] = True
        combinations[i] = updated_matrix

    # Handle includes with no match (just append to end)
    for i, used in enumerate(includes_used):
        if not used:
            combinations.append(includes[i])

    return combinations


def expand_job_matrixes(workflow: dict):
    """
    For each job in a workflow file, expands that job into all possible
    combinations of its matrix parameters. Returns each list of
    combinations in descending order of length.

    For example, if the input is this:
    ```
    {
        job1: {strategy: {matrix: {foo: [1, 2], bar: [3, 4]}}, ...},
        job2: {strategy: {matrix: {baz: [5, 6]}}, ...}
    }
    ```

    then the output will be this:
    ```
    [
        [
            ("job1 (1, 3)", "job1", {strategy: {matrix: {foo: 1, bar: 3}}, ...}),
            ("job1 (1, 4)", "job1", {strategy: {matrix: {foo: 1, bar: 4}}, ...}),
            ("job1 (2, 3)", "job1", {strategy: {matrix: {foo: 2, bar: 3}}, ...}),
            ("job1 (2, 4)", "job1", {strategy: {matrix: {foo: 2, bar: 4}}, ...})
        ],
        [
            ("job2 (5)", "job2", {strategy: {matrix: {baz: 5}}, ...}),
            ("job2 (6)", "job2", {strategy: {matrix: {baz: 6}}, ...})
        ]
    ]
    ```
    """

    # List of lists of (<job's API name>, <job's workflow name>, <collapsed config>) tuples.
    # Tuples are grouped by job.
    names_and_configs: 'list[list[tuple[str, str, dict]]]' = []

    # Used to detect duplicates
    disambiguated = []

    for job_workflow_name, job in workflow.items():
        job_base_api_name = job['name'] if 'name' in job else job_workflow_name

        if 'strategy' in job and 'matrix' in job['strategy']:
            job_matrix = job['strategy']['matrix']

            # If a job.strategy.matrix is a string, it probably depends on the output of another job
            # (e.g. https://github.com/TechEmpower/FrameworkBenchmarks/actions/runs/2053331030/workflow).
            # Skip expanding those jobs, since we can't know what the matrix is without running it ourselves.
            if isinstance(job_matrix, str):
                log.warning("Job matrix probably depends on another job's output. Skipping.")
                continue

            # Detect duplicates that we can't disambiguate
            if (job_base_api_name, job_matrix) in disambiguated:
                raise RecoverableException()
            disambiguated.append((job_base_api_name, job_matrix))

            # All keys not added by include rules. Used to generate job_api_name.
            default_keys = [key for key in job_matrix if key not in ['include', 'exclude']]
            # If a matrix only contains 'include' rules, then Actions uses those includes to generate
            # the API name.
            default_keys_are_dynamic = default_keys == [] and 'include' in job_matrix

            # For each possible combination of matrix values, generate the corresponding API name.
            # (Note: reliant on the specific order itertools.product generates. In practice it works fine.)
            names_and_configs.append([])
            for combination in build_combinations(job_matrix):
                if default_keys_are_dynamic:
                    default_keys = list(combination.keys())
                else:
                    default_keys = [key.lower() for key in default_keys]

                config = deepcopy(job)
                config['strategy']['matrix'] = combination
                job_api_name = get_job_api_name(job_base_api_name, combination, default_keys, job_matrix)

                names_and_configs[-1].append((job_api_name, job_base_api_name, job_workflow_name, config))
        else:
            # Detect duplicates that we can't disambiguate
            if job_base_api_name in disambiguated:
                raise RecoverableException()
            disambiguated.append(job_base_api_name)

            job_api_name = get_job_api_name(job_base_api_name, {}, [], {})
            names_and_configs.append([(job_api_name, job_base_api_name, job_workflow_name, job)])

    # Sort by length in descending order.
    return sorted(names_and_configs, key=lambda lst: len(lst), reverse=True)


def get_failed_step(failed_step_index: int, job_config: dict, api_steps: list):
    steps = job_config['steps']

    # The first step in the API is always "Set up job", which has no equivalent in the workflow file.
    # So, decrement the target index by 1.
    index = failed_step_index - 1

    api_step_names = [step['name'] for step in api_steps]

    if len(api_step_names) > 1 and api_step_names[1] == 'Set up runner':
        index -= 1

    # If a job runs in a container, one of the first API steps is always "Initialize containers".
    # No workflow file equivalent, so decrement.
    if 'container' in job_config or 'services' in job_config:
        if 'Initialize containers' in api_step_names:
            # container can be empty, need to double check using api steps.
            index -= 1

    # For each unique docker image used by a `uses` step, an API step is added to the start called "Pull <image>".
    # No workflow file equivalent, so decrement.
    dockerhub_steps = set(step['uses'] for step in steps
                          if 'uses' in step and step['uses'].startswith('docker://'))
    index -= len(dockerhub_steps)

    # Some predefined actions run in a container; if that's the case, then an API step is added to the start called
    # "Build <action name>". No workflow file equivalent, so decrement.
    build_steps = set(step['uses'] for step in steps
                      if 'uses' in step and 'Build {}'.format(step['uses']) in api_step_names)
    index -= len(build_steps)

    if steps and steps[0].get('name', '').startswith('Pre '):
        log.warning("Unable to check for pre steps (First step's name starts with 'Pre')")
    else:
        first_step_index = failed_step_index - index
        if index >= 0 and len(api_step_names) > first_step_index:
            for api_step_name in api_step_names[first_step_index:]:
                if api_step_name.startswith('Pre '):
                    index -= 1
                else:
                    break
        else:
            log.warning('Unable to check for pre steps (index: {}, first index: {})'.format(index, first_step_index))

    try:
        failed_step = steps[index]
    except IndexError:
        raise RecoverableException('Step index out of bounds (Unknown API step or wrong workflow file?)')

    failed_step_name = None
    if 'name' in failed_step:
        matrix = job_config.get('strategy', {}).get('matrix', {})
        # Interpolate matrix variables into the step's name.
        failed_step_name = get_job_api_name(failed_step['name'], matrix, {}, matrix)
    elif 'uses' in failed_step:
        failed_step_name = 'Run {}'.format(failed_step['uses'])
    elif 'run' in failed_step:
        failed_step_name = 'Run {}'.format(failed_step['run'].splitlines()[0])

    if api_steps[failed_step_index]['name'] != failed_step_name and '${{' not in failed_step_name:
        # The calculated step is different from the actual step, and it's not an interpolation issue.
        if index < 0 or api_steps[failed_step_index]['name'] == 'Set up job':
            raise RecoverableException('Cannot find failed step, maybe set up job step failed?')

        raise RecoverableException(
            'Error finding step index: names differ ("{}" != "{}")'.format(
                api_steps[failed_step_index]['name'],
                failed_step_name))

    if 'uses' in failed_step:
        return 'uses', failed_step['uses']
    elif 'run' in failed_step:
        return 'run', failed_step['run']
    raise RecoverableException('Invalid workflow file: step has neither "uses" key nor "run" key')


def find_sequence(needle, haystack):
    # Inefficient, but we're not dealing with huge lists.
    for i in range(len(haystack)):
        if haystack[i:i + len(needle)] == needle:
            return i, i + len(needle)
    return None, None


class ConstructJobConfig:
    """
    Later stages of the pipeline check each job's `config` to ensure
    that job pairs each use the same e.g. matrix parameters. This was
    obtained from the Travis API in the Travis pipeline, but the Github
    Actions API doesn't have a direct equivalent. This step manually
    constructs a `config` for each job in a build pair by fetching the
    build's workflow YML and matching each job with a job/matrix from
    the YML.

    LIMITATIONS:
    - This does not correctly handle `jobs.<job_id>.uses`,
      which lets a workflow call other workflow files. (Example:
      https://github.com/spring-projects/spring-shell/blob/690d1d2/.github/workflows/ci.yml#L41).
      Its use is relatively rare, and it would overcomplicate an already
      complicated pipeline step. Since jobs that use `uses` never have
      their config set, they will be excluded from the output.
    - Does not correctly handle dynamic job matrices. Since we can't
      know what the matrix values were without running the workflow
      ourselves, we can't reconstruct the jobs' config.
      Example: https://github.com/TechEmpower/FrameworkBenchmarks/actions/runs/2767165179/workflow
    """

    def process(self, build_groups: 'dict[str, BuildGroup]', context):
        log.info('Constructing job config for each build pair.')
        self.repo = context['repo']

        # GitHubWrapper doesn't allow requests from raw.githubusercontent.com, and
        # anyway that site doesn't return json. Therefore, we use our own session.
        self.session = cachecontrol.CacheControl(requests.Session())

        # Assumes the first token will work (NOT GUARANTEED!)
        self.session.headers['Authorization'] = 'token {}'.format(GITHUB_TOKENS[0])

        num_jobs_processed = 0

        for group_id, group in build_groups.items():
            # Parse workflow YML for each build pair in a group.
            build_id_to_workflow = self.get_workflow_objects(group)

            log.debug('Matching API jobs to workflow file jobs for', len(build_id_to_workflow), 'workflow runs')
            for build_id, workflow in build_id_to_workflow.items():
                try:
                    # Expand each job in a workflow YML
                    job_sequences = expand_job_matrixes(workflow)
                except RecoverableException:
                    log.warning('2 jobs with same name and matrix found. Cannot disambiguate.')
                    log.warning('Skipping build', build_id, 'in repo', self.repo)
                    continue

                # Match the expanded YML jobs with the API jobs by looking for sequences
                # where the names match.
                build = group.get_build(build_id)
                unmatched_job_names = [job.job_name.strip() for job in build.jobs]

                for job_sequence in job_sequences:
                    name_sequence = [tup[0] for tup in job_sequence]
                    base_name = job_sequence[0][1]
                    start, end = find_sequence(name_sequence, unmatched_job_names)

                    if start is None:
                        if base_name in unmatched_job_names:
                            # Skipped jobs with matrixes are not expanded, and their names are not interpolated.
                            # To ensure that we keep finding configs, manually flag the API name as found.
                            # (Since the job is skipped and its config is None, this job will not appear in a job pair.)
                            unmatched_job_names[unmatched_job_names.index(base_name)] = None
                            continue
                        else:
                            log.debug('Could not find the sequence', name_sequence, 'in the remaining job names.')
                            log.debug('Remaining sequence:', unmatched_job_names)
                            break

                    # Sequence found; set job object's config.
                    for seq_idx, job_idx in enumerate(range(start, end)):
                        target_job = build.jobs[job_idx]
                        job_config = job_sequence[seq_idx][3]
                        job_workflow_id = job_sequence[seq_idx][2]
                        unmatched_job_names[job_idx] = None

                        if target_job.failed_step_index is not None:
                            try:
                                kind, command = get_failed_step(
                                    target_job.failed_step_index, job_config, target_job.steps)
                            except RecoverableException as e:
                                log.warning('Error getting failed step for job {}:'.format(target_job.job_id))
                                log.warning(e)
                                continue
                            target_job.failed_step_kind = kind
                            target_job.failed_step_command = command

                        target_job.config = job_config
                        target_job.config['id-in-workflow'] = job_workflow_id
                        num_jobs_processed += 1

                # Sanity check: if any jobs are unmatched, then it's possible the mapping
                # went wrong.
                if any(unmatched_job_names):
                    num_unmatched = len(unmatched_job_names) - unmatched_job_names.count(None)
                    log.warning(num_unmatched, 'unmatched jobs for build', build_id)

        log.info('Constructed config for', num_jobs_processed, 'jobs')
        return build_groups

    def get_workflow_objects(self, group):
        """
        For each build pair in a group, fetch and parse each build's workflow YML file.
        Returns a mapping from build IDs to the 'jobs' section of the workflow file.
        """
        # Mapping from build ID to workflow object
        build_to_workflow = {}

        for build_pair in group.pairs:
            failed_commit = build_pair.failed_build.commit
            passed_commit = build_pair.passed_build.commit
            workflow_path = group.workflow_path

            try:
                log.debug('Getting YML for workflow run', build_pair.failed_build.build_id)
                failed_workflow_text = self.get_file_from_github(failed_commit, workflow_path)
                failed_workflow_object = yaml.safe_load(failed_workflow_text)
                build_to_workflow[build_pair.failed_build.build_id] = failed_workflow_object['jobs']

                log.debug('Getting YML for workflow run', build_pair.passed_build.build_id)
                passed_workflow_text = self.get_file_from_github(passed_commit, workflow_path)
                passed_workflow_object = yaml.safe_load(passed_workflow_text)
                build_to_workflow[build_pair.passed_build.build_id] = passed_workflow_object['jobs']
            except requests.HTTPError:
                continue

        return build_to_workflow

    def get_file_from_github(self, commit, path):
        url = 'https://raw.githubusercontent.com/{}/{}/{}'.format(self.repo, commit, path)
        response = self.session.get(url)
        response.raise_for_status()
        return response.text
