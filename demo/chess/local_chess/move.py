from collections import namedtuple

from .legacy_enum import Enum
from .common import square_name

class MoveFlag(Enum):
    pass
MoveFlag.NORMAL = MoveFlag._member('NORMAL', '')
MoveFlag.EN_PASSANT = MoveFlag._member('EN_PASSANT', 'ep')
MoveFlag.CASTLE = MoveFlag._member('CASTLE', 'castle')

class MoveRequest(namedtuple('MoveRequestBase', 'origin target promotion')):
    __slots__ = ()

    def __new__(cls, origin, target, promotion=''):
        return super(MoveRequest, cls).__new__(cls, origin, target, promotion)
    'What the player typed, before it is matched against the legal moves.'

class Move(namedtuple('MoveBase', 'origin target promotion flag')):
    __slots__ = ()

    def __new__(cls, origin, target, promotion='', flag=MoveFlag.NORMAL):
        return super(Move, cls).__new__(cls, origin, target, promotion, flag)

    def matches(self, request):
        return (self.origin, self.target, self.promotion) == (request.origin, request.target, request.promotion)

    def __str__(self):
        return square_name(self.origin) + square_name(self.target) + self.promotion
