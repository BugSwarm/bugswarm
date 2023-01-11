from bugswarm.common import outdated
from click import Command


class MyCommand(Command):
    """
    A subclass of Click's Command class that checks if the client is outdated after invoking the command.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def invoke(self, ctx):
        try:
            super().invoke(ctx)
        finally:
            # Ask users to consider updating if a newer version of the client is available.
            outdated.check_package_outdated('bugswarm-client')
