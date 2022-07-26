

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

                if reproduced_failed_tests_set != original_failed_tests_set:
                    match = False
                    mismatched_attributes.append({
                        'attr': attr,
                        'reproduced': list(reproduced_failed_tests_set - original_failed_tests_set),
                        'orig': list(original_failed_tests_set - reproduced_failed_tests_set)
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
