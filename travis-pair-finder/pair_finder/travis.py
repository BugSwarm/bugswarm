import re
import subprocess

from typing import Optional

from bugswarm.common.shell_wrapper import ShellWrapper


class Travis(object):
    def __init__(self):
        pass

    @staticmethod
    def travis_history(repo: str, history_file_path: str):
        history_command = ' '.join(['travis history --all --date -r', repo, '>', history_file_path])
        ShellWrapper.run_commands(history_command, stdout=subprocess.PIPE, shell=True)

    @staticmethod
    def travis_open(repo: str, build_num: str) -> str:
        open_command = ' '.join(['travis open --print --repo', repo, build_num])
        url, _, _ = ShellWrapper.run_commands(open_command, stdout=subprocess.PIPE, shell=True)
        return url

    @staticmethod
    def travis_show(repo: str, build_num: str) -> str:
        show_command = ' '.join(['travis show --repo', repo, build_num])
        result, _, _ = ShellWrapper.run_commands(show_command, stdout=subprocess.PIPE, shell=True)
        return result

    # ---------- Travis Wrapper Utils ----------

    @staticmethod
    def get_status_for_build(repo: str, build_num: str) -> str:
        result = Travis.travis_show(repo, build_num)
        status = re.search(r'State:\s*([A-Za-z]+)', result).group(1).lower().strip()
        return status

    @staticmethod
    def get_build_id_for_build(repo: str, build_num: str) -> Optional[str]:
        result = Travis.travis_open(repo, build_num)
        # The `travis open` command returns a url that contains either
        # 1) the job ID for the first job in the build or
        # 2) the build ID for the build
        # In the first case, we need to subtract 1 to get the actual internal build ID.
        extracted_id = re.findall(r'/(\d+)', result)[-1]
        if '/builds/' in result:
            return extracted_id
        elif '/jobs/' in result:
            return str(int(extracted_id) - 1)
        return None

    @staticmethod
    def is_travis_status_passed(status: str) -> bool:
        return status == 'passed'

    @staticmethod
    def is_travis_status_failed(status: str) -> bool:
        return status == 'failed'
