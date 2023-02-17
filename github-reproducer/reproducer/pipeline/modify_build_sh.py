import re

from os.path import isfile

from bugswarm.common import log


# TODO: Update this function
def patch_build_script(build_sh_path: str):
    """
    Adds flag for Maven to force TLS 1.2 in build scripts for Java jobs using JDK 7.

    :param build_sh_path: The path to a build script.
    """

    if not isinstance(build_sh_path, str):
        raise TypeError
    if not build_sh_path:
        raise ValueError
    if not isfile(build_sh_path):
        msg = '{} is not a file.'.format(build_sh_path)
        log.error(msg)
        raise OSError(msg)

    lines = []
    try:
        with open(build_sh_path) as f:
            for line in f:
                # Matches travis_cmd mvn\ ...
                match_obj = re.search(r'mvn[^w][\\]?', line)
                if not match_obj:
                    lines.append(line)
                    continue

                # Negative look behind. Catches case of no \ before the first -
                # Ex: travis_cmd mvn\ clean\ cobertura:cobertura\ coveralls:report --echo --timing
                match_obj = re.search(r'(?<![^\\]) -', line)
                if match_obj:
                    lines.append(line.replace(' -', r' -Dhttps.protocols=TLSv1.2\ -', 1))
                    continue
                # Negative look behind. Catches case of a \ before the first -
                # Ex: travis_cmd mvn\ clean\ cobertura:cobertura\ coveralls:report\ --echo --timing
                match_obj = re.search(r'((?<![\\]) -)', line)
                if match_obj:
                    lines.append(line.replace(' -', r'\ -Dhttps.protocols=TLSv1.2 -', 1))
                    continue
    except IOError:
        log.error('Error reading {} for patching mvn commands to use TLSv1.2.'.format(build_sh_path))
        raise

    # Overwrite the original build script with the modified build script.
    try:
        with open(build_sh_path, 'w') as f:
            for l in lines:
                f.write(l)
    except IOError:
        log.error('Error writing {} for patching mvn commands to use TLSv1.2.'.format(build_sh_path))
        raise
