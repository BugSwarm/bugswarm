# Run this script after generating folders for all image-tags by running main.py
#
# This script will generate:
#
#     * a folder '[type-of-error]_results' which contains:
#         reports_[type].tsv : contains details for each tag processed
#         not_[type] : list of tags not classified as [type-of-error]
#         reports_[type] : Same info as report.tsv, pretty printed
#       where [type-of-error] or [type] can be 'build', 'code', or 'test'
#
#     * a JSON file which contains all results calculated in this script (classification.json)
#
#     * a JSON file containing counts of all errors detected per language
#
#     * TSV files for:
#         -   classification results (results.tsv, results-details.tsv)
#         -   all errors, standard errors, user-defined errors
#
# USAGE:  python3 classify_bugs.py
#         python3 classify_bugs.py -h (Will display all optional arguments)
#
# REQUIREMENTS:
#     1. This script is run with Python3.x
#     2. main.py has been run

import re
import sys
import time
import os
import json
import argparse
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common import log
from .exception_lists import python_exceptions, python_nonstd, java_all, java_nonstd, not_errors


# Extracts filenames from the diff
def process_diff(diff_file):
    files_changed = list()
    files_added = list()
    files_deleted = list()
    re_filename = r'[a-zA-Z0-9\/\.\-\_\{\}]*'
    with open(diff_file) as f:
        diff = f.readlines()
    count = 0
    for line in diff:
        count = count + 1
        matches_change = re.match(r"Files (passed|failed)\/(?P<file_pass>" + re_filename +
                                  r") and (passed|failed)\/(?P<file_fail>" + re_filename + ") differ", line)
        if matches_change:
            matches = matches_change.groupdict()
            if matches.get('file_pass', 'default_pass') == matches.get('file_fail', 'default_fail'):
                files_changed.append(matches.get('file_pass', ''))
        matches_add_del = re.match(r"Only in (?P<fail_or_pass>(passed|failed))\/(?P<file_path>" +
                                   re_filename + r"): (?P<filename>[\w.]+)$", line)
        if matches_add_del:
            matches = matches_add_del.groupdict()
            if matches.get('fail_or_pass', '') == 'passed':
                files_added.append(matches.get('file_path', '') + matches.get('filename', ''))
            elif matches.get('fail_or_pass', '') == 'failed':
                files_deleted.append(matches.get('file_path', '') + matches.get('filename', ''))
    # if not files_changed:
    # return list(),list(),list()
    return files_changed, files_deleted, files_added


# Read cloc.csv
def process_loc(cloc_file, lang=None):
    num_lang_files = 0
    lang_loc = 0
    num_files = 0
    total_loc = 0
    with open(cloc_file) as f:
        loc = f.readlines()
    loc = [line.strip().split(',') for line in loc]
    for line in loc[1:]:
        if lang and line[1].lower() == lang:
            num_lang_files = int(line[0])
            lang_loc = int(line[4])
        num_files += int(line[0])
        total_loc += int(line[4])
    if not lang or lang_loc == 0 or num_lang_files == 0:
        lang_loc = loc[1][4]
        num_lang_files = loc[1][0]
    return lang_loc, total_loc, num_lang_files, num_files


def is_test(files_changed):
    """
    Checks if the file classifies as test error or not
    :param files_changed: the modified filename list between two commits
    :return: confidence, files_test, files_not_test
    """
    count = 0
    files_test = list()
    files_not_test = list()
    if len(files_changed) < 1:
        log.error("No files changed")
        return None, list(), list()
    for filename in files_changed:
        if re.search(r'tests?\/', filename):
            count += 1
            files_test.append(filename)
        elif re.search(r'test', filename):
            count += 0.5
            files_test.append(filename)
        else:
            files_not_test.append(filename)
    files_actually_changed = len(files_changed)
    if files_actually_changed > 0:
        confidence = count / files_actually_changed
    else:
        confidence = 0.0
    return confidence, files_test, files_not_test


def is_dependency(files_changed, all_files_changed):
    """
    Checks if the file classifies as deoendency (build) error or not
    :param files_changed: the modified filename list between two commits
    :param all_files_changed: all filenames that been modified
    :return: confidence, files_relevant, files_not_relevant
    """
    build_config_files = ['pom.xml', 'travis.yml', 'build.gradle', '.travis/', 'build.xml']
    count = 0
    files_relevant = list()
    files_not_relevant = list()
    if len(files_changed) < 1:
        log.error("No files changed")
        return None, list(), list()
    for filename in files_changed:
        if any([x in filename for x in build_config_files]):
            count += 1
            files_relevant.append(filename)
        else:
            files_not_relevant.append(filename)
    files_actually_changed = len(all_files_changed)
    if files_actually_changed > 0:
        confidence = count / files_actually_changed
    else:
        confidence = 0.0
    return confidence, files_relevant, files_not_relevant


def generate_report(all_info=None):
    all_info = [] if not all_info else all_info
    report = "\n----------------------------------------------------------------\n"
    for tag, data in all_info:
        if isinstance(data, list):
            report = report + "\n" + tag + ": \n\t" + '\n\t'.join(map(str, data))
        else:
            report = report + "\n" + tag + ": " + str(data)
    return report


def is_code(files_changed, all_files_changed):
    """
    Checks if the file classifies as code error or not
    :param files_changed: the modified filename list between two commits
    :param all_files_changed: all files been modified
    :return: confidence, files_code, files_not_code
    """
    count = 0
    files_code = list()
    files_not_code = list()
    if len(files_changed) < 1:
        log.error("No files changed")
        return None, list(), list()
    for filename in files_changed:
        # cannot contain 'test' or 'tests' in path
        if not re.search(r'test', filename):
            # if ends with ".java", needs to have "main"
            if re.search(r'\.java$', filename) and re.search(r'src', filename):
                count += 1
                files_code.append(filename)
            # if is a python file
            elif re.search(r'\.pyx?$', filename):
                count += 1
                files_code.append(filename)
        else:
            files_not_code.append(filename)
    files_actually_changed = len(all_files_changed)
    if files_actually_changed > 0:
        confidence = count / files_actually_changed
    else:
        confidence = 0.0

    return confidence, files_code, files_not_code


def classify_test(file_modified=None):
    """
    classify if the pair is test related
    :param file_modified: the list of file has been modified
    :return: test-related or not, confidence, files_not_test
    """
    file_modified = [] if not file_modified else file_modified
    confidence, files_test, files_not_test = is_test(file_modified)

    if not confidence or confidence == 0.0:
        return False, confidence, files_not_test
    else:
        return True, confidence, files_not_test


def classify_build(remain_files=None, file_modified=None):
    """
    classify if the pair is build related
    :param remain_files: the remainning list of files
    :param file_modified: the list of file has been modified
    :return: build-related or not, confidence, files_not_build
    """
    remain_files = [] if not remain_files else remain_files
    confidence, files_build, files_not_build = is_dependency(remain_files, file_modified)

    if not confidence or confidence == 0.0:
        return False, confidence, files_not_build
    else:
        return True, confidence, files_not_build


def classify_code(remain_files=None, file_modified=None):
    """
    classify if the pair is code related
    :param remain_files: the remainning list of files
    :param file_modified: the list of file has been modified
    :return: code-related or not, confidence
    """
    remain_files = [] if not remain_files else remain_files
    confidence, files_code, files_not_code = is_code(remain_files, file_modified)

    if not confidence or confidence == 0.0:
        return False, confidence
    else:
        return True, confidence


def process_logs(root, file_list):
    """
    Returns contents of the failed log as a list
    :param root: directory
    :param file_list: [failed log, passed log]
    :return: list
    """
    file_list.sort()
    with open(root + "/" + file_list[1]) as f:
        passed = f.readlines()
    passed = list(filter(None, [line.strip() for line in passed]))
    with open(root + "/" + file_list[0]) as f:
        failed = f.readlines()
    failed = list(filter(None, [line.strip() for line in failed]))
    if "Done. Your build exited with 0." not in passed[-1]:
        # error-condition, skip classification
        if "Done. Your build exited with 0." not in failed[-1]:
            return None
        else:
            # passed and failed got interchanged
            return passed
    return failed


def detect_lang(failed_log, quiet):
    build_lang = None
    py_version = None
    if type(failed_log) is not list:
        print(failed_log)
    for line in failed_log:
        if type(line) is not str:
            print(line)
            continue
        if "Build language: java" in line:
            build_lang = 'java'
            break
        elif "Build language: python" in line:
            build_lang = 'python'
            py_version = None
        if build_lang == 'python' and re.search(r"Python ([\d\.]+)", line):
            py_version = re.search(r"Python ([\d\.]+)", line).groups()[0]
            break
    if build_lang == 'java':
        if not quiet:
            print("Lang is java")
        # java processing
        return 0, {'language': "java"}
    elif build_lang == 'python':
        # python processing
        if not quiet:
            print("Lang is python")
        if py_version:
            if not quiet:
                print("Version is ", py_version)
            return 0, {'language': "python", "version": py_version}
        return 0, {'language': "python"}
    else:
        if not quiet:
            print("Error: build language not retrieved. Exiting")
        return -1, None


def update_error_dict(build_lang, err, regex, line, error_list, user_defined, non_std_list, error_dict):
    if build_lang == "python" and re.search(r"except " + regex, line):
        # Adding exception for python
        return

    for e in err:
        if e in error_list or e in user_defined or e in non_std_list:
            error_dict[e] = error_dict.get(e, 0) + 1
        elif e not in not_errors:
            user_defined.add(e)
            error_dict[e] = 1


# For code errors: detects all exceptions or errors (see err_regex) in failed Java log
def get_java_error_data(failed_log: list, error_list: list, non_std_list: list):
    """
    :param failed_log: failed_log contents as a list
    :param error_list: list of standard Java errors
    :param non_std_list: list of nonstandard Java errors
    :return: error_dict, user_defined, std_error, common_error, user_error

    Finds exceptions/errors that cause test failures in Java programs (using Maven, Gradle, or Ant).
    These consist of all errors directly preceded by an error indicator such as "<<< ERROR!",
    and all subsequent errors in the corresponding stack trace (preceded by "Caused by:").

    For example, the following has 1 IOException and 1 NullPointerException that would be counted:
        testSomethingOrOther(foo.bar.FooBar)  Time elapsed: 3.703 sec  <<< ERROR!
        java.io.IOException: [...]
            at [...]
        Caused by: java.lang.NullPointerException: [...]
            at [...]
    """
    build_lang = 'java'
    error_dict = dict()
    user_defined = set()
    std_error = common_error = user_error = 0
    basic_err_regex = r"[A-Za-z\.\$]+(\.|\$)([A-Za-z]+)(: |; |:$|\s*$| at )"
    err_indicator = [r"<<< ERROR!\s*\Z",
                     r"<<< FAILURE!\s*\Z",
                     r"\S+ FAILED\s*\Z",
                     r"\[junit\]\s+Caused an ERROR\s*\Z",
                     r"\[junit\]\s+FAILED\s*\Z",
                     r"An exception has occurred in the compiler"]
    err_regex = [r"^\s*" + basic_err_regex,
                 r"(ThreadDeath)([^\w\.]|$)",
                 r"^\s*Caused by: " + basic_err_regex,
                 r"\[[A-Za-z]+\]\s*" + basic_err_regex,
                 r"\[[A-Za-z]+\]\s*Caused by: " + basic_err_regex]

    count_causedbys = False
    saved_err = []
    line_idx = 0
    while line_idx < len(failed_log):
        line = failed_log[line_idx]

        # Count errors preceded by an error indicator ("<<< ERROR!" or equivalent)
        for regex in err_indicator:
            if line_idx + 1 >= len(failed_log) or not re.search(regex, line):
                continue
            # Since there is an error indicator, a stack trace has started. Start counting exceptions preceded by
            # 'Caused by:'.
            count_causedbys = True

            for r in err_regex:
                # Special case: Ant puts the exception name 2 lines after the error indicator, not 1.
                if (regex == err_indicator[3] or regex == err_indicator[4]) and line_idx + 2 < len(failed_log):
                    e = re.search(r, failed_log[line_idx + 2])
                    if e:
                        line_idx += 1
                # Default case (Maven and Gradle)
                else:
                    e = re.search(r, failed_log[line_idx + 1])

                if e:
                    # If the last stack trace ended with java.lang.Exception or java.lang.Error, add it to the dict
                    if saved_err:
                        update_error_dict(build_lang, saved_err, regex, failed_log[line_idx + 1], error_list,
                                          user_defined, non_std_list,
                                          error_dict)
                    e = [e.groups()[1]]
                    # Don't count java.lang.Exception or java.lang.Error unless it's at the end of a stack trace
                    if e == ['Exception'] or e == ['Error']:
                        saved_err = e
                    else:
                        saved_err = []
                        update_error_dict(build_lang, e, regex, failed_log[line_idx + 1], error_list, user_defined,
                                          non_std_list,
                                          error_dict)
                    line_idx += 2
                    break

        if line_idx >= len(failed_log):
            break
        line = failed_log[line_idx]

        # Look for "Caused by:" errors and errors that don't cause a test failure
        for regex in err_regex:
            e = re.search(regex, line)

            # Count errors preceded by "Caused by:",
            # but only if they are part of a stacktrace headed by an error indicator
            if count_causedbys and re.search(r"Caused by:", line):
                # Special case: Gradle puts the "Caused by:" on its own line, and the actual exception on the next line
                if not e and line_idx + 1 < len(failed_log):
                    e = re.search(regex, failed_log[line_idx + 1])
                    if e:
                        line_idx += 1
                        line = failed_log[line_idx]
                if e:
                    e = [e.groups()[1]]
                    # Don't count java.lang.Exception or java.lang.Error unless it's at the end of a stack trace
                    if e == ['Exception'] or e == ['Error']:
                        saved_err = e
                    else:
                        saved_err = []
                        update_error_dict(build_lang, e, regex, line, error_list, user_defined, non_std_list,
                                          error_dict)
                    break

            # An error not preceded by "Caused by:" indicates a new stacktrace.
            # Since it wasn't caught by the first FOR loop, it doesn't have an error indicator.
            # Therefore, don't count it or any "Caused by:" errors after it.
            elif e:
                # If the last stack trace ended with java.lang.Exception or java.lang.Error, add it to the dict
                if saved_err:
                    update_error_dict(build_lang, saved_err, regex, line, error_list, user_defined, non_std_list,
                                      error_dict)
                count_causedbys = False

        line_idx += 1

    # If the last stack trace ended with java.lang.Exception or java.lang.Error, add it to the dict
    if saved_err:
        update_error_dict(build_lang, saved_err, regex, line, error_list, user_defined, non_std_list, error_dict)

    return error_dict, user_defined, std_error, common_error, user_error


# For code errors: detects all exceptions or errors (see err_regex) in failed Python log
def get_python_error_data(failed_log: list, error_list: list, non_std_list: list):
    """
    :param failed_log: failed_log contents as a list
    :param error_list: list of standard Python errors
    :param non_std_list: list of nonstandard Python errors
    :return: error_dict, user_defined, std_error, common_error, user_error

    Finds exceptions/errors that cause test failures in Python programs (using unittest or pytest).
    These consist of all errors listed in unittest "ERROR" and "FAILURE" traces, and
    all errors in the "=== ERRORS ===" and "=== FAILURES ===" sections of pytest logs.

    For example, the following has 1 UnboundLocalError that would be counted:
        ======================================================================
        ERROR: test_CRYPT (gluon.tests.test_validators.TestValidators)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
          [...]
        UnboundLocalError: local variable 'v' referenced before assignment

    NOTE: This does NOT count exceptions that are only found in pytest's captured
    stdout/stderr calls. While they do sometimes provide useful information, they
    are also a source of many false positives (e.g. test exceptions) that we'd
    prefer to avoid.
    """
    build_lang = 'python'
    error_dict = dict()
    user_defined = set()
    std_error = common_error = user_error = 0

    # Strip ANSI color codes from lines to make the regex simpler
    # Taken from https://stackoverflow.com/a/14693789
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)
    noansi_log = [ansi_escape.sub('', line) for line in failed_log]

    # This regex matches any valid Python identifier: any string of word characters
    # (alphanumerics and the underscore) that does not start with a digit
    identifier_regex = r"(?!\d)\w+"

    err_indicator = [r"^ERROR: ",
                     r"^FAIL: ",
                     r"E\s+Traceback \(most recent call last\):",
                     r"data: .*\.test:\d+:\Z",
                     r"^>\s+.+$\Z",
                     r"^\.?Traceback \(most recent call last\):"]
    sameline_err_indicator = [r"\S*\.[a-z]+:\d+: " + identifier_regex + r"\Z"]
    err_collecting_indicator = [r"^(E\s+)?([A-Za-z]+Error)"]

    err_regex = [r"^(" + identifier_regex + r"\.)*(" + identifier_regex + r")(: |:?\Z)",
                 r"^E\s+(" + identifier_regex + r"\.)*(" + identifier_regex + r")(: |\Z)",
                 r":\d+: ()(" + identifier_regex + r")\Z",
                 r"^()(ImportError) while importing"]

    look_for_err = False
    sameline_err = False
    failed_tests_started = False
    err_found_this_test = False
    found_err = False
    err_collecting = False
    line_idx = -1
    while line_idx + 1 < len(noansi_log):
        line_idx += 1
        line = noansi_log[line_idx]

        # If the line starts with 'Traceback (most recent call last):'
        if re.search(err_indicator[-1], line):
            found_err = True

        if not failed_tests_started and not found_err:
            failed_tests_started = bool(re.search(r"={35}( FAILURES |= ERRORS =)?={35}", line))
            continue

        # This regex indicates the start of a failed pytest test. There is a specific error indicator that we should
        # only consider if no errors have been found in a specific test; otherwise, that error is redundant.
        if re.search(r"^_* (\[doctest\] )?(?!summary)[\w\.\/]+(\[.+\])?\s?_*\Z", line):
            err_found_this_test = False
            err_collecting = False
            continue

        # This regex matches the start of a part of a pytest log indicating that pytest encountered an error collecting
        # a test. (This is usually due to a SyntaxError or an ImportError.)
        # The errors listed in this part of a log use some special syntax, and the regex that captures them (found in
        # err_collecting_indicator) is too broad to be used elsewhere, so it is only considered if err_collecting is
        # True.
        if re.search(r"^_* ERROR collecting [\w\.\/]+(\[.+\])?\s?_*\Z", line):
            err_collecting = True
            continue

        all_indicators = err_indicator + sameline_err_indicator + (err_collecting_indicator if err_collecting else [])
        for regex in all_indicators:
            if not re.search(regex, line) or line_idx + 1 >= len(noansi_log) or (
                    regex in sameline_err_indicator and err_found_this_test):
                continue
            if regex == err_indicator[-1] and failed_tests_started:
                continue
            if regex in (sameline_err_indicator + err_collecting_indicator):
                sameline_err = True
            else:
                line_idx += 1
            look_for_err = True
            break

        line = noansi_log[line_idx]

        try:
            if look_for_err:
                for regex in err_regex:
                    e = re.search(regex, line)
                    if e:
                        e = [e.groups()[1]]
                        err_found_this_test = True
                        update_error_dict(build_lang, e, regex, line, error_list, user_defined, non_std_list,
                                          error_dict)
                        if not (line_idx + 1 < len(noansi_log) and noansi_log[line_idx + 1] ==
                                'Traceback (most recent call last):'):
                            look_for_err = sameline_err = found_err = False
                        break
                else:
                    if sameline_err:
                        # The line matched a regex in sameline_err_indicator, but it couldn't find a valid exception
                        # on that line. Continuing to look for exceptions on subsequent lines may cause false positives.
                        look_for_err = sameline_err = False
        except IndexError:
            pass

    return error_dict, user_defined, std_error, common_error, user_error


# For code errors: detects all exceptions or errors (see err_regex) in failed log
def process_error(build_lang: str = None, failed_log: list = None):
    """
    :param build_lang: python or java
    :param failed_log: failed_log contents as a list
    :return: error_dict, userdefined, confidence

    Finds exceptions/errors that cause a test failure.
    See get_java_error_data() or get_python_error_data() for specifics.
    """
    if not build_lang or not failed_log:
        return -1, -1

    exception_dict = {
        'python': [python_exceptions, python_nonstd],
        'java': [java_all, java_nonstd]
    }
    # error_list = exception_dict[build_lang['language']]
    error_list = exception_dict[build_lang][0]
    # non_std_list = exception_dict[build_lang['version']]
    non_std_list = exception_dict[build_lang][1]
    user_defined = set()
    error_dict = dict()
    std_error = common_error = user_error = 0

    if build_lang == 'java':
        error_dict, user_defined, std_error, common_error, user_error = get_java_error_data(failed_log, error_list,
                                                                                            non_std_list)
    elif build_lang == 'python':
        error_dict, user_defined, std_error, common_error, user_error = get_python_error_data(failed_log, error_list,
                                                                                              non_std_list)

    for e in error_dict:
        if e in error_list:
            std_error += 1  # error_dict.get(e,0)
        elif e in non_std_list:
            common_error += 1  # error_dict.get(e,0)
        elif e in user_defined:
            user_error += 1  # error_dict.get(e,0)
    total_count = std_error + common_error + user_error
    if total_count > 0:
        confidence = (std_error + (0.6 * common_error) + (0.3 * user_error)) / total_count
    else:
        confidence = 0.0
    return error_dict, list(user_defined), confidence  # notdetected


# Detects language of repo, as well as version (if python)

def main(args=None):
    args = dict() if not args else args
    t_start = time.time()
    bugswarm_sandbox_path = os.getenv('HOME') + procutils.CONTAINER_SANDBOX
    final_classification = dict()
    final_error_artifact = {'python': dict(), 'java': dict()}
    all_user_defined = {'python': dict(), 'java': dict()}

    filter_count = 0
    processed_count = 0

    # Reset all result files
    files = [
        'results/test/not_test',
        'results/test/reports_test',
        'results/test/reports_test.tsv',
        'results/build/not_build',
        'results/build/reports_build',
        'results/build/reports_build.tsv',
        'results/code/reports_code.tsv',
        'results/code/not_code',
        'results/code/not_processed']

    for file in files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass
    filtered_tags_file = args.get('filter') or 'tags/filter_tags'
    with open(filtered_tags_file) as f:
        filtered_tags = f.readlines()
    filtered_tags = [tag.strip() for tag in filtered_tags]

    for root, dirs, files in os.walk(bugswarm_sandbox_path):
        if not root.count("/") == 4:  # checking depth
            if not args.get('quiet'):
                print("Incorrect depth: {} not processed".format(root))
            continue
        if not files:
            if not args.get('quiet'):
                print("{} doesn't contain files ".format(root))
            continue
        elif "diff.txt" not in files:
            if not args.get('quiet'):
                print("{} doesn't contain diff.txt".format(root))
            continue
        elif "cloc.csv" not in files:
            if not args.get('quiet'):
                print("{} doesn't contain cloc.csv".format(root))
            continue

        image_tag = re.sub(bugswarm_sandbox_path + "/", '', root)

        # Filter out tags outside of list
        if image_tag not in filtered_tags:
            filter_count += 1
            continue
        processed_count += 1

        # Extract data from files
        files_changed, files_deleted, files_added = process_diff(root + "/diff.txt")
        failed_log = process_logs(root, files)
        if not failed_log:
            if not args.get('quiet'):
                print(image_tag + " not processed, no failed log detected.")
            continue
        error, build_lang = detect_lang(failed_log, quiet=args.get('quiet'))
        main_sloc, sloc, num_main_files, num_files = process_loc(root + "/cloc.csv",
                                                                 lang=build_lang.get('language', None))

        # CLASSIFICATION
        files_modified = []
        files_modified.extend(files_changed)
        files_modified.extend(files_deleted)
        files_modified.extend(files_added)
        files_modified = list(filter(lambda x: '.git' not in x, files_modified))
        is_test, test_confidence, remain_files = classify_test(files_modified)
        is_build, build_confidence, remain_files = classify_build(remain_files, files_modified)
        is_code, code_confidence = classify_code(remain_files, files_modified)

        error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)

        # Add to error lists
        for e in userdefined:
            all_user_defined[build_lang.get('language')][e] = all_user_defined[build_lang.get('language')].get(e, 0) + 1

        for e in error_dict:
            final_error_artifact[build_lang.get('language')][e] = final_error_artifact[build_lang.get('language')].get(
                e, 0) + 1

        # Add to final classification file
        final_classification[image_tag] = dict()
        final_classification[image_tag]['language'] = build_lang.get('language', None)
        final_classification[image_tag]['type'] = dict()
        final_classification[image_tag]['diffcount'] = len(files_changed + files_deleted + files_added)
        final_classification[image_tag]['lang_loc'] = main_sloc
        final_classification[image_tag]['total_loc'] = sloc
        final_classification[image_tag]['lang_files'] = num_main_files
        final_classification[image_tag]['total_files'] = num_files
        if is_test:
            final_classification[image_tag]['type']['TEST'] = {'name': 'TEST', 'value': test_confidence}
        if is_build:
            final_classification[image_tag]['type']['BUILD'] = {'name': 'BUILD', 'value': build_confidence}
        if is_code:
            if args.get('exclude_build') and build_confidence == 1:
                pass
            elif args.get('exclude_test') and test_confidence == 1:
                pass
            else:
                final_classification[image_tag]['type']['CODE'] = {'name': 'CODE', 'value': code_confidence,
                                                                   'errors': error_dict}

    t_end = time.time()
    print("{} tags filtered out and {} tags processed".format(filter_count, processed_count))
    print('Running all images took {}s'.format(t_end - t_start))

    # Write all results to file

    # Final output file
    final_classification_filename = args.get('output') or 'final_results/classification.json'
    with open(final_classification_filename, 'w') as f:
        json.dump(final_classification, f)

    # All errors detected with count
    with open('final_results/error_artifact.json', 'w') as f:
        json.dump(final_error_artifact, f)

    # Same info in tsv format
    with open('final_results/errors_artifact.tsv', 'w') as f:
        for lang in final_error_artifact:
            for e in final_error_artifact[lang]:
                f.write("{}\t{}\t{}\n".format(lang, e, final_error_artifact[lang][e]))

    # only standard errors
    with open('final_results/errors_artifact_standard.tsv', 'w') as f:
        for lang in final_error_artifact:
            for e in final_error_artifact[lang]:
                if e in python_exceptions or e in java_all:
                    f.write("{}\t{}\t{}\n".format(lang, e, final_error_artifact[lang][e]))

    # Only userdefined/non-standard errors
    with open('final_results/userdefined_errors.tsv', 'w') as f:
        for lang in all_user_defined:
            for e in all_user_defined[lang]:
                f.write("{}\t{}\t{}\n".format(lang, e, all_user_defined[lang][e]))

    # Final overall results
    with open('final_results/results.tsv', 'w') as f:
        f.write("IMAGE_TAG\tCATEGORY")
        for image_tag in final_classification:
            classes = list(filter(None, [category for category in final_classification[image_tag]['type']]))
            f.write("\n{}\t{}".format(image_tag, ','.join(classes)))

    with open('final_results/results_details.tsv', 'w') as f:
        f.write("IMAGE_TAG\tLanguage\tTEST\tBUILD\tCODE\t")
        for image_tag in final_classification:
            test_confidence = 0
            build_confidence = 0
            code_confidence = 0
            exception_list = list()
            for category in final_classification[image_tag]['type']:
                category = final_classification[image_tag]['type'][category]
                if category.get('name') == 'TEST':
                    test_confidence = category.get('value')
                elif category.get('name') == 'BUILD':
                    build_confidence = category.get('value')
                elif category.get('name') == 'CODE':
                    code_confidence = category.get('value')
                    exception_list = category.get('errors', list())
            f.write(
                "\n{}\t{}\t{}\t{}\t{}".format(image_tag, final_classification[image_tag]['language'], test_confidence,
                                              build_confidence, code_confidence, ', '.join(exception_list)))

    print("All results written to file. Exiting. ")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--exclude-test', action='store_true', default=False,
                        help="Excludes 100%% test results from code")
    parser.add_argument('-b', '--exclude-build', action='store_true', default=False,
                        help="Excludes 100%% build results from code")
    parser.add_argument('-o', '--output', default=None, help="Specify name of output file")
    parser.add_argument('-f', '--filter', default=None, help="File containing all filtered tags.")
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help=" Will suppress all outputs except running time")
    args = parser.parse_args()
    sys.exit(main(vars(args)))
