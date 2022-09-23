from dataclasses import dataclass


@dataclass
class Step:
    name: str
    number: int
    custom: bool

    setup_cmd: str
    run_cmd: str
    envs: str
    step: dict

    working_dir: str = None
    filename: str = 'bugswarm_cmd.sh'
    exec_template: str = 'bash -e {}'
