import ast
import pprint
import re


class ResultComparer(object):
    @staticmethod
    def compare_attributes(reproduced, original, ignore_status=False):
        """
        :param reproduced: dict returned by Analyzer.analyze()
        :param original: dict returned by Analyzer.analyze()
        :param ignore_status:
        :return: match: bool
                 mismatched_attributes: list of dict
        """
        ignored_attributes = [
            'tr_log_testduration', 'tr_log_buildduration', 'tr_log_setup_time', 'tr_err_msg', 'tr_build_image',
            'tr_worker_instance', 'tr_connection_lines', 'tr_using_worker',
            'tr_could_not_resolve_dep', 'tr_os', 'tr_cookbook'
        ]
        if ignore_status:
            ignored_attributes.append('tr_log_status')

        match = True
        mismatched_attributes = []
        for attr in original:
            if attr == 'tr_log_tests_failed':
                reproduced_failed_tests_set = set(reproduced[attr].split('#'))
                original_failed_tests_set = set(original[attr].split('#'))
                if reproduced_failed_tests_set == set(['']):
                    reproduced_failed_tests_set = set()
                if original_failed_tests_set == set(['']):
                    original_failed_tests_set = set()

                orig_failed_normalized = ResultComparer._normalize_parameterized(original_failed_tests_set)
                repr_failed_normalized = ResultComparer._normalize_parameterized(reproduced_failed_tests_set)

                if orig_failed_normalized.keys() != repr_failed_normalized.keys():
                    match = False

                    reproduced_mismatch = ResultComparer._diff_keys_and_get_values(
                        repr_failed_normalized, orig_failed_normalized)
                    original_mismatch = ResultComparer._diff_keys_and_get_values(
                        orig_failed_normalized, repr_failed_normalized
                    )
                    mismatched_attributes.append({
                        'attr': attr,
                        'reproduced': reproduced_mismatch,
                        'orig': original_mismatch
                    })
                continue

            if attr in ignored_attributes:
                continue

            if reproduced[attr] != original[attr]:
                match = False
                mismatched_attributes.append({
                    'attr': attr,
                    'reproduced': reproduced[attr],
                    'orig': original[attr]
                })
        return match, mismatched_attributes

    @staticmethod
    def _normalize_parameterized(test_set: 'set[str]') -> 'dict[str, str]':
        """
        In failed Python tests that list the parameters to the test function
        (e.g. Nose), normalize/alphabetize any dicts passed into the test. This
        is needed for some tests run in older Python versions where dicts'
        ordering was non-deterministic.

        :param test_set: set[str]: a set of failed test functions.
        :return dict[str, str]: a mapping between the 'normalized' test
            functions and the original test functions.
        """
        # Mapping between the 'normalized' test and the original test
        norm_test_to_test = dict()

        for test in test_set:
            # Matches test_method(<params...>) (testpackage.TestClass)
            # So far I've only seen this format used in one repo, wbond/package_control_channel,
            # which uses a bespoke hack on top of `unittest` instead of `nose`.
            match = re.match(r'(?P<method>\w+)\((?P<params>.+)\) \((?P<package>[\w\.]+)\)$', test)
            if not match:
                # Matches testpackage.test_method(<params...>)
                # This is the default `nose` format.
                match = re.match(r'(?P<method>[\w\.]+)\((?P<params>.+)\)$', test)

            if match:
                groups = match.groupdict()
                test_method = groups.get('method', '')
                test_params = groups.get('params', '')
                test_package = groups.get('package', '')

                # Nose parameterized tests with a single argument have a trailing ','.
                # It breaks ast.literal_eval(), so strip it.
                if test_params.endswith(','):
                    test_params = test_params[:-1]

                try:
                    # Convert the params to a python tuple
                    params_tup = ast.literal_eval(f'({test_params},)')
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    # literal_eval failed; fall back to original test
                    norm_test_to_test[test] = test
                    continue

                # Use pformat to sort any dicts in the tuple.
                normalized_params = pprint.pformat(params_tup, sort_dicts=True)
                # Get fully qualified test method name, if not qualified already
                normalized_method = f'{test_package}.{test_method}' if test_package else test_method

                normalized_test = f'{normalized_method}({normalized_params})'
                norm_test_to_test[normalized_test] = test
            else:
                # Not a parameterized test; just map from `test` to `test`
                norm_test_to_test[test] = test

        return norm_test_to_test

    @staticmethod
    def _diff_keys_and_get_values(d1: dict, d2: dict) -> list:
        """Returns `d1[key]` for each key in `d1` and not in `d2`."""
        return [d1[key] for key in d1.keys() - d2.keys()]
