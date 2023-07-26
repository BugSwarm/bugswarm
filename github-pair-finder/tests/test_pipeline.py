import json
import re
import unittest
from os.path import join

import requests_mock
from bugswarm.common.credentials import GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.json import read_json

from model.mined_project_builder import MinedProjectBuilder
from pipeline.steps import (AlignJobPairs, CleanPairs, ConstructJobConfig,
                            ExtractAllBuildPairs, GetBuildSystemInfo,
                            GetJobsFromGitHubAPI, GroupJobs)
from pipeline.steps.construct_job_config import expand_job_matrixes

from tests.utils import DATA_DIR, pipeline_data_from_dict, to_dict


class TestPipeline(unittest.TestCase):

    # GetJobsFromGitHubAPI #

    @requests_mock.Mocker()
    def test_get_jobs_from_api(self, mock: requests_mock.Mocker):
        repo = 'orientechnologies/orientdb'
        datadir = join(DATA_DIR, repo.replace('/', '-'))

        # Set up mocks
        self.setup_get_jobs_from_github_api_mocks(repo, 2, mock)

        # Get expected output
        with open(join(datadir, 'step1-output.json')) as f:
            expected_output = json.load(f)

        input_context = {
            'repo': repo,
            'github_api': GitHubWrapper(GITHUB_TOKENS),
            'mined_project_builder': MinedProjectBuilder(),
            'original_mined_project_metrics': {
                'progression_metrics': {
                    'builds': 0,
                    'jobs': 0,
                    'failed_builds': 0,
                    'failed_jobs': 0,
                    'failed_pr_builds': 0,
                    'failed_pr_jobs': 0,
                },
            },
            'cutoff_days': 0,
        }

        step = GetJobsFromGitHubAPI()
        output = step.process(None, input_context)

        self.assertEqual(output, expected_output)

    @requests_mock.Mocker()
    def test_get_jobs_from_api_with_last_mined(self, mock: requests_mock.Mocker):
        repo = 'orientechnologies/orientdb'
        datadir = join(DATA_DIR, repo.replace('/', '-'))
        build_cutoff = 2566916244

        # Set up mocks
        self.setup_get_jobs_from_github_api_mocks(repo, 2, mock)

        # Get expected output
        with open(join(datadir, 'step1-output.json')) as f:
            expected_output = json.load(f)
        expected_output = [job for job in expected_output if job['build_id'] > build_cutoff]

        input_context = {
            'repo': repo,
            'github_api': GitHubWrapper(GITHUB_TOKENS),
            'mined_project_builder': MinedProjectBuilder(),
            'original_mined_project_metrics': {
                'last_build_mined': {'build_id': build_cutoff},
                'progression_metrics': {
                    'builds': 0,
                    'jobs': 0,
                    'failed_builds': 0,
                    'failed_jobs': 0,
                    'failed_pr_builds': 0,
                    'failed_pr_jobs': 0,
                },
            },
            'cutoff_days': 0,
        }

        step = GetJobsFromGitHubAPI()
        output = step.process(None, input_context)

        self.assertEqual(output, expected_output)

    def setup_get_jobs_from_github_api_mocks(self, repo, num_pages, mock: requests_mock.Mocker):
        datadir = join(DATA_DIR, repo.replace('/', '-'))

        url = 'https://api.github.com/repos/{}/actions/runs'.format(repo)
        for i in range(1, num_pages + 1):
            with open(join(datadir, 'runs-page{}.json'.format(i))) as f:
                page = json.load(f)

            for run in page['workflow_runs']:
                with open(join(datadir, 'jobs-responses', '{}.json'.format(run['id']))) as f:
                    mock.get(run['jobs_url'], text=f.read())

            next_url = 'https://api.github.com/repos/{}/actions/runs?page={}'.format(repo, i)
            if i < num_pages:
                headers = {'link': '<{}>; rel="next"'.format(next_url)}
            else:
                headers = {}
            mock.get(url, json=page, headers=headers)

            url = next_url

        mock.get('https://api.github.com/repos/{}/languages'.format(repo), json={'Java': 1000})

    # GroupJobs #

    def test_group_jobs(self):
        datadir = join(DATA_DIR, 'orientechnologies-orientdb')
        with open(join(datadir, 'step1-output.json')) as f:
            input = json.load(f)
        with open(join(datadir, 'step2-output.json')) as f:
            expected_output = json.load(f)

        step = GroupJobs()
        output = to_dict(step.process(input, {}))

        # Assert that the groups are equal
        self.assertEqual(output.keys(), expected_output.keys())
        # Assert that the contents of the groups are the same (barring some extra
        # values in the real output)
        self.assertRecursiveDictSubset(expected_output, output)

    # ExtractAllBuildPairs #

    def test_extract_build_pairs(self):
        datadir = join(DATA_DIR, 'orientechnologies-orientdb')
        with open(join(datadir, 'step2-output.json')) as f:
            input = pipeline_data_from_dict(json.load(f))
        with open(join(datadir, 'step3-output.json')) as f:
            expected_output = json.load(f)

        step = ExtractAllBuildPairs()
        output = to_dict(step.process(input, {}))

        self.assertEqual(output.keys(), expected_output.keys())
        self.assertRecursiveDictSubset(expected_output, output)

    def test_extract_build_pairs_2(self):
        datadir = join(DATA_DIR, 'LSPosed-LSPatch')
        with open(join(datadir, 'step2-output.json')) as f:
            input = pipeline_data_from_dict(json.load(f))
        with open(join(datadir, 'step3-output.json')) as f:
            expected_output = json.load(f)

        step = ExtractAllBuildPairs()
        output = to_dict(step.process(input, {}))

        self.assertEqual(output.keys(), expected_output.keys())
        self.assertRecursiveDictSubset(expected_output, output)

    # ConstructJobConfig #

    @requests_mock.Mocker()
    def test_construct_config(self, mock: requests_mock.Mocker):
        repo = 'raphw/byte-buddy'
        datadir = join(DATA_DIR, repo.replace('/', '-'))

        with open(join(datadir, 'workflow.yml')) as f:
            workflow_text = f.read()

        for sha in ['5ef0cdddc720ab83b79a2e2f555d84405b634999',
                    'db7aede5e68772486617dfe573ddd2306be927dc']:
            mock.get('https://raw.githubusercontent.com/{}/{}/.github/workflows/main.yml'.format(repo, sha),
                     text=workflow_text)

        with open(join(datadir, 'step3-output.json')) as f:
            input = pipeline_data_from_dict(json.load(f))
        with open(join(datadir, 'step4-output.json')) as f:
            expected_output = json.load(f)

        step = ConstructJobConfig()
        output = to_dict(step.process(input, {"repo": repo}))

        for group_id in output:
            for i in range(len(output[group_id]['pairs'])):
                expected_failed_build = expected_output[group_id]['pairs'][i]['failed_build']
                actual_failed_build = output[group_id]['pairs'][i]['failed_build']
                expected_passed_build = expected_output[group_id]['pairs'][i]['passed_build']
                actual_passed_build = output[group_id]['pairs'][i]['passed_build']
                self.assertRecursiveDictSubset(expected_failed_build['jobs'], actual_failed_build['jobs'])
                self.assertRecursiveDictSubset(expected_passed_build['jobs'], actual_passed_build['jobs'])

    def test_expand_config_matrix_with_includes_1(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2, 3, 4],
                        'include': [{'foo': 2, 'bar': True}, {'foo': 4, 'baz': 4}, {'foo': 5}, {'baz': 5}]
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1, 'baz': 5},
            {'foo': 2, 'bar': True, 'baz': 5},
            {'foo': 3, 'baz': 5},
            {'foo': 4, 'baz': 5},
            {'foo': 5}
        ]
        expected_names = [
            'job1 (1)',
            'job1 (2)',
            'job1 (3)',
            'job1 (4)',
            'job1 (5)',
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]

        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_with_includes_2(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2, 3, 4],
                        'include': [{'baz': 5}, {'foo': 2, 'bar': True}, {'foo': 4, 'baz': 4}, {'foo': 5}]
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1, 'baz': 5},
            {'foo': 2, 'bar': True, 'baz': 5},
            {'foo': 3, 'baz': 5},
            {'foo': 4, 'baz': 4},
            {'foo': 5}
        ]
        expected_names = [
            'job1 (1)',
            'job1 (2)',
            'job1 (3)',
            'job1 (4)',
            'job1 (5)',
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]

        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_with_includes_3(self):
        input_job = {
            'job1': {
                'name': 'Test',
                'strategy': {
                    'matrix': {
                        'fruit': ['apple', 'pear'],
                        'animal': ['cat', 'dog'],
                        'include': [
                            {'color': 'green'},
                            {'color': 'pink', 'animal': 'cat'},
                            {'fruit': 'apple', 'shape': 'circle'},
                            {'fruit': 'banana'},
                            {'fruit': 'banana', 'animal': 'cat'}
                        ]
                    }
                }
            }
        }
        expected_matrixes = [
            {'fruit': 'apple', 'animal': 'cat', 'color': 'pink', 'shape': 'circle'},
            {'fruit': 'apple', 'animal': 'dog', 'color': 'green', 'shape': 'circle'},
            {'fruit': 'pear', 'animal': 'cat', 'color': 'pink'},
            {'fruit': 'pear', 'animal': 'dog', 'color': 'green'},
            {'fruit': 'banana'},
            {'fruit': 'banana', 'animal': 'cat'}
        ]
        expected_names = [
            'Test (apple, cat)',
            'Test (apple, dog)',
            'Test (pear, cat)',
            'Test (pear, dog)',
            'Test (banana)',
            'Test (banana, cat)'
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]

        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_with_includes_4(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2, 3, 4],
                        'include': [{'foo': 4, 'bar': 4}, {'foo': 5, 'bar': 5}]
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1},
            {'foo': 2},
            {'foo': 3},
            {'foo': 4, 'bar': 4},
            {'foo': 5, 'bar': 5}
        ]
        expected_names = [
            'job1 (1)',
            'job1 (2)',
            'job1 (3)',
            'job1 (4)',
            'job1 (5, 5)',
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]

        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_with_includes_5(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [
                            {'a': 'A1', 'b': {'x': 1, 'y': 2}},
                            {'a': 'A2', 'b': 'B2'}
                        ],
                        'include': [
                            {'foo': {'a': 'A3', 'c': 'C'}, 'd': 'D'},
                            {'e': 'E'}
                        ]
                    }
                }
            }
        }
        expected_matrixes = [
            {
                'foo': {'a': 'A1', 'b': {'x': 1, 'y': 2}},
                'e': 'E'
            },
            {
                'foo': {'a': 'A2', 'b': 'B2'},
                'e': 'E'
            },
            {
                'foo': {'a': 'A3', 'c': 'C'},
                'd': 'D'
            }
        ]
        expected_names = [
            'job1 (A1, 1, 2)',
            'job1 (A2, B2)',
            'job1 (A3, C, D)'
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]
        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_with_includes_6(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2],
                        'bar': [3, 4],
                        'include': [
                            {'foo': 1, 'bar': 5},
                            {'foo': 6, 'bar': 7},
                            {'foo': 1, 'baz': 8},
                            {'foo': 9, 'baz': 10},
                            {'foo': 1, 'bar': 3, 'baz': 11},
                            {'foo': 1, 'bar': 12, 'baz': 13},
                            {'foo': 14, 'bar': 3, 'baz': 15},
                            {'foo': 16, 'bar': 17, 'baz': 18}
                        ]
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1, 'bar': 3, 'baz': 11},
            {'foo': 1, 'bar': 4, 'baz': 8},
            {'foo': 2, 'bar': 3},
            {'foo': 2, 'bar': 4},
            {'foo': 1, 'bar': 5},
            {'foo': 6, 'bar': 7},
            {'foo': 9, 'baz': 10},
            {'foo': 1, 'bar': 12, 'baz': 13},
            {'foo': 14, 'bar': 3, 'baz': 15},
            {'foo': 16, 'bar': 17, 'baz': 18},
        ]
        expected_names = [
            'job1 (1, 3)',
            'job1 (1, 4)',
            'job1 (2, 3)',
            'job1 (2, 4)',
            'job1 (1, 5)',
            'job1 (6, 7)',
            'job1 (9, 10)',
            'job1 (1, 12, 13)',
            'job1 (14, 3, 15)',
            'job1 (16, 17, 18)',
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]

        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_with_excludes(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2, 3],
                        'bar': [3, 4, 5],
                        'exclude': [{'foo': 3, 'bar': 3}, {'foo': 1, 'bar': 4}, {'bar': 5}]
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1, 'bar': 3},
            {'foo': 2, 'bar': 3},
            {'foo': 2, 'bar': 4},
            {'foo': 3, 'bar': 4},
        ]
        expected_names = [
            'job1 (1, 3)',
            'job1 (2, 3)',
            'job1 (2, 4)',
            'job1 (3, 4)',
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        actual_names = [tup[0] for group in output for tup in group]

        self.assertEqual(expected_matrixes, actual_matrixes)
        self.assertEqual(expected_names, actual_names)

    def test_expand_config_matrix_includes_and_excludes_1(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2, 3],
                        'bar': [3, 4],
                        'exclude': [{'foo': 3, 'bar': 3}, {'foo': 1, 'bar': 4}],
                        'include': [{'foo': 3}],
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1, 'bar': 3},
            {'foo': 2, 'bar': 3},
            {'foo': 2, 'bar': 4},
            {'foo': 3, 'bar': 4},
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        self.assertEqual(expected_matrixes, actual_matrixes)

    def test_expand_config_matrix_includes_and_excludes_2(self):
        input_job = {
            'job1': {
                'strategy': {
                    'matrix': {
                        'foo': [1, 2, 3],
                        'bar': [3, 4],
                        'exclude': [{'foo': 3}],
                        'include': [{'foo': 3, 'bar': 5}],
                    }
                }
            }
        }
        expected_matrixes = [
            {'foo': 1, 'bar': 3},
            {'foo': 1, 'bar': 4},
            {'foo': 2, 'bar': 3},
            {'foo': 2, 'bar': 4},
            {'foo': 3, 'bar': 5},
        ]

        output = expand_job_matrixes(input_job)
        actual_matrixes = [tup[3]['strategy']['matrix'] for group in output for tup in group]
        self.assertEqual(expected_matrixes, actual_matrixes)

    @requests_mock.Mocker()
    def test_step_name_interpolation(self, mock: requests_mock.Mocker):
        repo = 'exadel-inc/etoolbox-authoring-kit'
        datadir = join(DATA_DIR, repo.replace('/', '-'))

        with open(join(datadir, 'workflow.yml')) as f:
            workflow_text = f.read()

        workflow_url = re.compile(
            r'^https://raw\.githubusercontent\.com/{}/.*/\.github/workflows/tests\.yml'.format(repo))
        mock.get(workflow_url, text=workflow_text)

        input_path = join(datadir, 'extract-build-pairs-output.json')
        output_path = join(datadir, 'construct-job-config-output.json')
        input = pipeline_data_from_dict(read_json(input_path))
        expected_output = read_json(output_path)

        step = ConstructJobConfig()
        output = to_dict(step.process(input, {'repo': repo}))

        for group_id in output:
            for i in range(len(output[group_id]['pairs'])):
                expected_failed_build = expected_output[group_id]['pairs'][i]['failed_build']
                actual_failed_build = output[group_id]['pairs'][i]['failed_build']
                expected_passed_build = expected_output[group_id]['pairs'][i]['passed_build']
                actual_passed_build = output[group_id]['pairs'][i]['passed_build']
                self.assertRecursiveDictSubset(expected_failed_build['jobs'], actual_failed_build['jobs'])
                self.assertRecursiveDictSubset(expected_passed_build['jobs'], actual_passed_build['jobs'])

    # AlignJobPairs #

    def test_align_job_pairs(self):
        repo = 'raphw/byte-buddy'
        datadir = join(DATA_DIR, repo.replace('/', '-'))

        with open(join(datadir, 'step4-output.json')) as f:
            input = pipeline_data_from_dict(json.load(f))
        with open(join(datadir, 'step5-output.json')) as f:
            expected_output = json.load(f)

        step = AlignJobPairs()
        output = to_dict(step.process(input, {'repo': repo}))

        self.assertRecursiveDictSubset(expected_output, output)

    # GetBuildSystemInfo #

    @requests_mock.Mocker()
    def test_get_build_system_info(self, mock):
        params = {
            'maven': {
                'repo': 'raphw/byte-buddy',
                'inpath': 'step5-output.json',
                'outpath': 'step7-output.json'},
            'gradle': {
                'repo': 'spring-projects/spring-kafka',
                'inpath': 'step6-output.json',
                'outpath': 'step7-output.json'},
            'ant': {
                'repo': 'apache/tomcat',
                'inpath': 'step6-output.json',
                'outpath': 'step7-output.json'},
            'na': {
                'repo': 'django/django',
                'inpath': 'step6-output.json',
                'outpath': 'step7-output.json'},
            'maven (not in tree)': {
                'repo': 'geoserver/geoserver',
                'inpath': 'checkresettable_output.json',
                'outpath': 'getbuildsystem_output.json'}
        }

        for title, params in params.items():
            with self.subTest(title):
                self.subtest_get_build_system_info(mock, **params)

    def subtest_get_build_system_info(self, mock, repo, inpath, outpath):
        datadir = join(DATA_DIR, repo.replace('/', '-'))

        input = pipeline_data_from_dict(read_json(join(datadir, inpath)))
        expected_output = read_json(join(datadir, outpath))

        commits = [commit for group in input.values()
                   for pair in group.pairs
                   for commit in [pair.failed_build.commit, pair.passed_build.commit]]

        for commit in commits:
            commit_response = read_json(join(datadir, 'commit-responses', commit))
            tree_sha = commit_response['tree']['sha']
            tree_url = commit_response['tree']['url']
            tree_response = read_json(join(datadir, 'tree-responses', tree_sha))
            mock.get('https://api.github.com/repos/{}/git/commits/{}'.format(repo, commit), json=commit_response)
            mock.get(tree_url, json=tree_response)

        context = {'repo': repo, 'github_api': GitHubWrapper(GITHUB_TOKENS)}

        step = GetBuildSystemInfo()
        output = to_dict(step.process(input, context))

        self.assertRecursiveDictSubset(expected_output, output, 'expected', 'actual')

    # CleanPairs #

    # @requests_mock.Mocker()
    def test_clean_pairs_sets_repo_mined_version(self):
        repo = 'raphw/byte-buddy'
        datadir = join(DATA_DIR, repo.replace('/', '-'))
        latest_commit = '0308dfed5be3beebe9ca777fc891b78b6ecf058b'
        # with open(join(datadir, 'commits-response.json')) as f:
        #     resp = json.load(f)
        #     latest_commit = resp[0]['sha']
        #     mock.get('https://api.github.com/repos/{}/commits'.format(repo), json=resp)

        with open(join(datadir, 'step5-output.json')) as f:
            input = pipeline_data_from_dict(json.load(f))

        step = CleanPairs()
        output = step.process(input, {'repo': repo, 'head_commit': latest_commit, 'utils': None})

        for group in output.values():
            for pair in group.pairs:
                self.assertEqual(pair.repo_mined_version, latest_commit)

    # Helpers #

    def assertRecursiveDictSubset(self, subset, superset, sub_name='subset', sup_name='superset'):
        """Asserts that all non-dict elements of `subset` are in `superset`, and
        that the same holds recursively for all dict elements of subset/superset.
        WARNING: raises a RecursionError if a dictionary contains itself
        (e.g. `d = {}; d[0] = d`)."""

        if isinstance(subset, dict) and isinstance(superset, dict):
            for key in subset:
                self.assertIn(key, superset, '{} not in {}'.format(repr(key), sup_name))
                self.assertRecursiveDictSubset(
                    subset[key],
                    superset[key],
                    f'{sub_name}[{repr(key)}]',
                    f'{sup_name}[{repr(key)}]')
        elif isinstance(subset, list) and isinstance(superset, list):
            self.assertEqual(len(subset), len(superset), f'len({sub_name}) != len({sup_name})')
            for i in range(len(subset)):
                self.assertRecursiveDictSubset(
                    subset[i], superset[i], f'{sub_name}[{i}]', f'{sup_name}[{i}]')
        else:
            self.assertEqual(subset, superset, f'{sub_name} != {sup_name}')
