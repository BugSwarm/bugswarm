import sys
from pathlib import Path

from packaging import version

from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.log_downloader import download_log
from utils import validate_input, print_error, mkdir
from python_log_parser import parse_log


_HOME_DIR = str(Path.home())
_SANDBOX_DIR = '{}/bugswarm-sandbox'.format(_HOME_DIR)
_TMP_DIR = '{}/tmp'.format(_SANDBOX_DIR)


def _print_usage():
    print('Usage: python3 select_artifacts.py <image_tags_file> <task-name>')
    print('       image_tags_file: Path to a file containing a newline-separated list of image tags to process.')
    print('       task-name: Name of current task. Results will be put in ./output/<task-name>.csv.')


def download_artifact_log(artifact):
    failed_job_id = artifact["failed_job"]["job_id"]
    passed_job_id = artifact["passed_job"]["job_id"]

    mkdir('{}/{}'.format(_TMP_DIR, failed_job_id))
    mkdir('{}/{}'.format(_TMP_DIR, passed_job_id))

    failed_job_orig_log_path = '{}/{}/log-failed.log'.format(_TMP_DIR, failed_job_id)
    passed_job_orig_log_path = '{}/{}/log-passed.log'.format(_TMP_DIR, passed_job_id)

    result = download_log(failed_job_id, failed_job_orig_log_path)
    if not result:
        print_error('Error downloading log for failed_job_id {}'.format(failed_job_id))
        return -1, failed_job_orig_log_path, passed_job_orig_log_path

    result = download_log(passed_job_id, passed_job_orig_log_path)
    if not result:
        print_error('Error downloading log for passed_job_id {}'.format(passed_job_id))
        return -1, failed_job_orig_log_path, passed_job_orig_log_path
    return 1, failed_job_orig_log_path, passed_job_orig_log_path


def check_pip_version(log_path):
    res = parse_log(log_path)
    for python_version, value in res.items():
        if "default" in value:
            default_pip_version = value["default"].split("==")[1]
            if version.parse(default_pip_version) < version.parse("8.0.0"):
                return False
            for package in value["packages"]:
                name, v = package.split("==")
                if name == "pip":
                    if version.parse(v) < version.parse("8.0.0"):
                        return False

    return True


def python_filter(artifact):
    status, failed_job_log_path, passed_job_log_path = download_artifact_log(artifact)
    if status:
        if check_pip_version(failed_job_log_path) and check_pip_version(passed_job_log_path):
            return True
    return False


def java_filter(artifact):
    if int(artifact["reproduce_successes"]) > 0:
        return True
    return False


def main(argv=None):
    argv = argv or sys.argv
    image_tags_file, output_file = validate_input(argv, _print_usage)
    bugswarmapi = DatabaseAPI(DATABASE_PIPELINE_TOKEN)
    artifact_list = list()
    with open(image_tags_file, "r") as file:
        for line in file:
            image_tag = line.strip()
            artifact = bugswarmapi.find_artifact(image_tag).json()
            res = False
            if artifact["lang"] == "Python":
                res = python_filter(artifact)
            elif artifact["lang"] == "Java":
                res = java_filter(artifact)
            if res:
                artifact_list.append(image_tag)

    with open(output_file, "w+") as file:
        for art in artifact_list:
            file.write("{}\n".format(art))


if __name__ == '__main__':
    sys.exit(main())
