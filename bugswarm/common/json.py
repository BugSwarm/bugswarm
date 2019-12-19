import json
import os

from typing import Optional


class DefaultJSONEncoder(json.JSONEncoder):
    """
    Subclass of `json.JSONEncoder` that can serialize user-defined types.
    """
    def default(self, o):
        return o.__dict__


def read_json(filepath: str):
    """
    Decode JSON data from a file.

    :param filepath: Path to the file from which to read JSON data.
    :raises FileNotFoundError: If no file exists at `filepath`.
    :return: The decoded JSON object.
    """
    if not filepath:
        raise ValueError
    if not os.path.isfile(filepath):
        raise FileNotFoundError
    with open(filepath) as f:
        return json.load(f)


def write_json(filepath: str, data, overwrite: bool = True, encoder: Optional[json.JSONEncoder] = None):
    """
    Write JSON data to a file.

    :param filepath: Path to the file to which to write JSON data.
    :param data: The JSON object to encode and write to the file.
    :param overwrite: Whether to overwrite a file at `filepath` if one already exists. If `overwrite` is False and a
                      file already exists at `filepath`, FileExistsError is raised. Defaults to True.
    :param encoder: The encoder object to use for the JSON encoding. Should be a subclass of json.JSONEncoder.
                    DefaultJSONEncoder is used by default.
    :raises FileExistsError: If a file at `filepath` already exists and `overwrite` is False.
    :return: True if the write to `filepath` succeeded.
    """
    if not filepath:
        raise ValueError
    if os.path.isfile(filepath) and not overwrite:
        raise FileExistsError
    if data is None:
        raise ValueError
    with open(filepath, 'w') as f:
        json.dump(data, f, cls=encoder, indent=2)
