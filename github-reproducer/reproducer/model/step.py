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
    continue_on_error: str = 'false'
    step_if: str = 'true'
    timeout_minutes: str = 360,
    filename: str = 'bugswarm_cmd.sh'
    exec_template: str = 'bash -e {}'
    id: str = None
