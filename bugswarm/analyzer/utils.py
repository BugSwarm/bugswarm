import os

from itertools import dropwhile
from itertools import takewhile
from typing import List
from typing import Optional


def get_fold_lines(log_path: str, start_sentinel: str, end_sentinel: str) -> Optional[List]:
    """
    Parses a Travis log to extract the lines of the log that are within a fold. If the log contains the start but not
    the end of the fold, then the lines from the start sentinel to the end of the log are returned.

    :param log_path: The path to the Travis log.
    :param start_sentinel: A string that distinguishes the starting line of the fold. To locate the start of the fold,
                           this function finds the first line in the log that contains `start_sentinel`.
    :param end_sentinel: A string that distinguishes the ending line of the fold. To locate the end of the fold,
                         this function finds the first line in the log that contains `end_sentinel`.
    :raises FileNotFoundError: If no file exists at `log_path`.
    :return: A list of strings representing the lines of the log that are within the fold. None if the the log does not
             contain the fold.
    """
    if not isinstance(log_path, str):
        raise TypeError
    if not log_path:
        raise ValueError
    if not os.path.isfile(log_path):
        raise FileNotFoundError
    if not isinstance(start_sentinel, str):
        raise TypeError
    if not start_sentinel:
        raise ValueError
    if not isinstance(end_sentinel, str):
        raise TypeError
    if not end_sentinel:
        raise ValueError

    start_sentinel = start_sentinel.strip()
    end_sentinel = end_sentinel.strip()

    with open(log_path) as f:
        # Ignore lines until we see the start of the fold.
        f = dropwhile(lambda l: start_sentinel not in l.strip(), f)
        # Ignore the actual start indicator.
        try:
            next(f)
        except StopIteration:
            # We reached the end of the log without finding the start of the fold.
            return None
        # Take lines until we see the end of the fold.
        lines = takewhile(lambda l: end_sentinel not in l.strip(), f)
        return list(lines)


def get_instance_line(worker_lines: List[str]) -> Optional[str]:
    """
    :param worker_lines: The lines from a Travis log
    :return: The line in `worker_lines` that contains information about the worker instance.
    """
    if not worker_lines:
        raise ValueError
    if any(not isinstance(l, str) for l in worker_lines):
        raise TypeError

    instance_lines = [line for line in worker_lines if 'instance' in line]
    if not instance_lines:
        return None
    return instance_lines[-1]


class TupleSortingOn0(tuple):
    def __lt__(self, rhs):
        return self[0] < rhs[0]

    def __gt__(self, rhs):
        return self[0] > rhs[0]

    def __le__(self, rhs):
        return self[0] <= rhs[0]

    def __ge__(self, rhs):
        return self[0] >= rhs[0]


def get_lines_of_pairs_matching(file, pairs_both_matching):
    lines = []
    with open(file) as f:
        for l in f:
            # Tuple expansion yields the following values:
            # project name, PR number, failed build ID, passed build ID, failed base commit, failed trigger commit,
            # passed base commit, passed trigger commit.
            _, _, fail_build_id, pass_build_id, _, _, _, _ = l.strip().split(',')
            if (fail_build_id, pass_build_id) in pairs_both_matching:
                lines.append(l)
    return lines


def to_percent(n):
    return str(int(round(n, 2) * 100)) + '%'
