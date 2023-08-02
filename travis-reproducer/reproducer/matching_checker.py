

class MatchChecker(object):
    #########################################
    # Jobpair-level match type definitions. #
    #########################################

    # Match Type 1: A full match. Both the failed job and passed job reproduced logs match the original logs.
    @staticmethod
    def is_jobpair_match_type_1(jobpair):
        return jobpair.jobs[0].match.value and jobpair.jobs[1].match.value

    # Match Type 2: The pair is either a fail-pass or an error-pass pair, but at least one of the compared attributes
    #               does not match.
    @staticmethod
    def is_jobpair_match_type_2(jobpair):
        if not jobpair.jobs[0].reproduced_result or not jobpair.jobs[1].reproduced_result:
            return False
        failed_job_result = jobpair.jobs[0].reproduced_result
        passed_job_result = jobpair.jobs[1].reproduced_result
        failed_job_failed = failed_job_result['tr_log_status'] != 'ok'
        passed_job_passed = passed_job_result['tr_log_status'] == 'ok'
        return failed_job_failed and passed_job_passed

    # Match Type 3: The pair is neither a fail-pass nor an error-pass pair, but the failed job has at least one failing
    #               test and the passed job has no failing tests.
    @staticmethod
    def is_jobpair_match_type_3(jobpair):
        if not jobpair.jobs[0].reproduced_result or not jobpair.jobs[1].reproduced_result:
            return False
        failed_job_result = jobpair.jobs[0].reproduced_result
        passed_job_result = jobpair.jobs[1].reproduced_result
        # Check if the failed job has failed tests.
        failed_job_has_failed_tests = False
        if failed_job_result['tr_log_num_tests_failed'] != 'NA' and failed_job_result['tr_log_num_tests_failed'] > 0:
            failed_job_has_failed_tests = True
        # Check if the passed job has no failed tests.
        # Use a try-except block becuase values might be 'NA', which would raise an exception when comparing.
        try:
            passed_job_num_tests_run = passed_job_result['tr_log_num_tests_run']
            passed_job_num_tests_failed = passed_job_result['tr_log_num_tests_failed']
            passed_job_has_no_failed_tests = passed_job_num_tests_run > 0 and passed_job_num_tests_failed == 0
        except TypeError:
            return False
        return failed_job_has_failed_tests and passed_job_has_no_failed_tests

    ###########################################
    # Buildpair-level match type definitions. #
    ###########################################

    # Match Type 1: A full match. Both the failed build and passed build reproduced logs match the original logs.
    @staticmethod
    def is_buildpair_match_type_1(buildpair):
        for b in buildpair.builds:
            for j in b.jobs:
                if not j.match.value:
                    return False
        return True

    # Match Type 2: The pair is either a fail-pass or an error-pass pair, but at least one of the compared attributes
    #               does not match.
    @staticmethod
    def is_buildpair_match_type_2(buildpair):
        for b in buildpair.builds:
            if [1 for j in b.jobs if not j.reproduced_result]:
                return False
        # Check if the build failed.
        failed_build_failed = False
        for j in buildpair.builds[0].jobs:
            if j.reproduced_result:
                if j.reproduced_result['tr_log_status'] != 'ok':
                    failed_build_failed = True
        passed_build_passed = True
        for j in buildpair.builds[1].jobs:
            if j.reproduced_result:
                if j.reproduced_result['tr_log_status'] != 'ok':
                    passed_build_passed = False
        return failed_build_failed and passed_build_passed

    # Match Type 3: The pair is neither a fail-pass nor an error-pass pair, but the failed build has at least one
    #               failing test and the passed build has no failing tests.
    @staticmethod
    def is_buildpair_match_type_3(buildpair):
        for b in buildpair.builds:
            if [1 for j in b.jobs if not j.reproduced_result]:
                return False
        # Check if the build failed.
        failed_build_has_failed_tests = False
        for j in buildpair.builds[0].jobs:
            if j.reproduced_result:
                failed_build_num_tests_failed = j.reproduced_result['tr_log_num_tests_failed']
                if failed_build_num_tests_failed != 'NA' and failed_build_num_tests_failed > 0:
                    failed_build_has_failed_tests = True
        # Check if passed build has no failed tests.
        # Use a try-except block becuase values might be 'NA', which would raise error when comparing.
        passed_build_has_no_failed_tests = True
        for j in buildpair.builds[1].jobs:
            if j.reproduced_result:
                try:
                    passed_build_num_tests_run = j.reproduced_result['tr_log_num_tests_run']
                    passed_build_num_tests_failed = j.reproduced_result['tr_log_num_tests_failed']
                    if not (passed_build_num_tests_run > 0 and passed_build_num_tests_failed == 0):
                        passed_build_has_no_failed_tests = False
                except TypeError:
                    return False
        return failed_build_has_failed_tests and passed_build_has_no_failed_tests
