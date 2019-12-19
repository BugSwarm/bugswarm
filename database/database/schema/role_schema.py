import enum

from typing import List
from typing import Set

from .ability_schema import Ability


class RoleInfo(object):
    """
    Contains the following information about a role:
      - Abilities:
          A list of Ability enumeration members.
      - Name.
    """
    def __init__(self, name: str, abilities: Set[Ability]):
        if not isinstance(name, str):
            raise TypeError
        if not name:
            raise ValueError
        if not isinstance(abilities, set):
            raise TypeError
        if not abilities:
            raise ValueError('A role must have at least one ability.')
        if any(not isinstance(a, Ability) for a in abilities):
            raise TypeError

        self.name = name
        self.abilities = abilities

    def __str__(self):
        return self.name


@enum.unique
class Role(enum.Enum):
    """
    An enumeration that encodes information of every Role supported for role-based access control.
    Each enumeration member value is a RoleInfo instance.

    WARNING:
    Modify this enumeration according to the following rules:
      - Role names must be unique since Eve uses plain strings to identify roles.
      - Adding a new Role is permitted.
      - Changing a Role's name is prohibited since Eve uses plain strings to identify roles. If you really need to
        change a Role's name, then make extra sure that the accounts resource in the database is updated accordingly.
      - Think carefully before removing a Role or updating a Role's abilities. If you still think that either would be a
        good idea, then think harder. Then consider whether adding a new Role would be sufficient. If you really need to
        remove a role or update a Role's abilities, make extra sure that the accounts resource in the database is
        updated accordingly.
    """
    # For project owners.
    SUPERUSER = RoleInfo('superuser', Ability.all())
    # For project developers and other non-owners with write access.
    DEVELOPER = RoleInfo('developer', Ability.all())
    # For the pipeline components.
    PIPELINE = RoleInfo('pipeline', Ability.all())
    # For the website.
    WEBSITE = RoleInfo('website', Ability.read())
    # For everyone else (external users with read access).
    USER = RoleInfo('user', Ability.read())

    def __str__(self):
        return str(self.value)

    @classmethod
    def all(cls) -> List:
        return [role for role in cls]

    @classmethod
    def all_role_names(cls) -> List:
        return list(map(str, Role.all()))

    @classmethod
    def read_roles(cls) -> List:
        """
        Returns a list of roles that have at least the Ability.read() abilities.
        """
        return list(filter(lambda r: r.value.abilities.issuperset(Ability.read()), cls.all()))

    @classmethod
    def write_roles(cls) -> List:
        """
        Returns a list of roles that have at least the Ability.write() abilities.
        """
        return list(filter(lambda r: r.value.abilities.issuperset(Ability.write()), cls.all()))
