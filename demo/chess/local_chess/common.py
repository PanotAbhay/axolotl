"""Shared primitives: colors, squares and board geometry.

Squares are ``(row, col)`` tuples; row 0 is rank 8 and col 0 is file ``a``.
"""
from .legacy_enum import Enum
BOARD_SIZE = 8
FILES = 'abcdefgh'
PROMOTION_LETTERS = 'qrbn'

class Color(Enum):

    @property
    def opposite(self):
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    @property
    def label(self):
        return 'White' if self is Color.WHITE else 'Black'

    @property
    def pawn_direction(self):
        return -1 if self is Color.WHITE else 1

    @property
    def pawn_start_row(self):
        return 6 if self is Color.WHITE else 1

    @property
    def home_row(self):
        return 7 if self is Color.WHITE else 0

    @property
    def castling_letters(self):
        """(king side, queen side) letters as used in castling rights."""
        return ('K', 'Q') if self is Color.WHITE else ('k', 'q')
Color.WHITE = Color._member('WHITE', 'w')
Color.BLACK = Color._member('BLACK', 'b')

def inside(square):
    row, col = square
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

def square_name(square):
    row, col = square
    return FILES[col] + str(BOARD_SIZE - row)

def parse_square(text):
    """Turn ``"e4"`` into ``(4, 4)``; return ``None`` for invalid text."""
    if len(text) != 2 or text[0] not in FILES or text[1] not in '12345678':
        return None
    return (BOARD_SIZE - int(text[1]), FILES.index(text[0]))
