"""Dependency-free named constants for the Python 2.7 game."""


class Enum(object):
    def __new__(cls, value):
        for member in cls.__dict__.values():
            if isinstance(member, cls) and member.value == value:
                return member
        raise ValueError('%r is not a valid %s' % (value, cls.__name__))

    @classmethod
    def _member(cls, name, value):
        member = object.__new__(cls)
        member.name = name
        member.value = value
        return member

    def __repr__(self):
        return '%s.%s' % (type(self).__name__, self.name)
