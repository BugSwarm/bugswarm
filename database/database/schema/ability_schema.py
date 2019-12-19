from enum import Enum
from enum import auto


class Ability(Enum):
    """
    An enumeration that encodes information of the possible abilities that a user (i.e. a Role) could have.

    At this time, abilities are essentially the HTTP verbs supported by the database.
    However, other enum members not related to HTTP verbs could be added in the future.
    """
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()
    OPTIONS = auto()

    @classmethod
    def all(cls):
        return set(ability for ability in cls)

    @classmethod
    def read(cls):
        """
        Returns the set of abilities that read from the database.
        """
        return {cls.GET, cls.OPTIONS}

    @classmethod
    def write(cls):
        """
        Returns the set of abilities that change the database.
        """
        return {cls.POST, cls.PUT, cls.PATCH, cls.DELETE}
