"""Piece behavior: every piece knows which squares it attacks and which moves it can make."""
from abc import ABCMeta, abstractmethod
from .common import PROMOTION_LETTERS, Color, inside
from .move import Move, MoveFlag
KNIGHT_STEPS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
STRAIGHT = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAGONAL = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
KING_STEPS = STRAIGHT + DIAGONAL

class Piece(object):
    __metaclass__ = ABCMeta
    'Immutable piece; positions live on the board, not on the piece.'

    def __init__(self, color):
        self.color = color

    @property
    def symbol(self):
        return self.kind.upper() if self.color is Color.WHITE else self.kind

    def __eq__(self, other):
        return type(self) is type(other) and self.color is other.color

    def __hash__(self):
        return hash((type(self), self.color))

    def __repr__(self):
        return '{0}({1})'.format(type(self).__name__, self.color.name)

    @abstractmethod
    def attacks(self, board, origin):
        """Squares this piece attacks (may include occupied squares of either color)."""

    def moves(self, board, origin, state):
        for target in self.attacks(board, origin):
            if self._can_land_on(board, target):
                yield Move(origin, target)

    def _can_land_on(self, board, target):
        occupant = board.piece_at(target)
        return occupant is None or (occupant.color is not self.color and (not isinstance(occupant, King)))

class LeaperPiece(Piece):

    def attacks(self, board, origin):
        row, col = origin
        for d_row, d_col in self.STEPS:
            square = (row + d_row, col + d_col)
            if inside(square):
                yield square

class SlidingPiece(Piece):

    def attacks(self, board, origin):
        row, col = origin
        for d_row, d_col in self.DIRECTIONS:
            square = (row + d_row, col + d_col)
            while inside(square):
                yield square
                if board.piece_at(square) is not None:
                    break
                square = (square[0] + d_row, square[1] + d_col)

class Knight(LeaperPiece):
    kind = 'n'
    STEPS = KNIGHT_STEPS

class Bishop(SlidingPiece):
    kind = 'b'
    DIRECTIONS = DIAGONAL

class Rook(SlidingPiece):
    kind = 'r'
    DIRECTIONS = STRAIGHT

class Queen(SlidingPiece):
    kind = 'q'
    DIRECTIONS = STRAIGHT + DIAGONAL

class King(LeaperPiece):
    kind = 'k'
    STEPS = KING_STEPS

    def moves(self, board, origin, state):
        for item in super(King, self).moves(board, origin, state):
            yield item
        for item in self._castling_moves(board, origin, state):
            yield item

    def _castling_moves(self, board, origin, state):
        home = self.color.home_row
        if origin != (home, 4) or board.is_in_check(self.color):
            return
        enemy = self.color.opposite
        rook = Rook(self.color)
        short_right, long_right = self.color.castling_letters

        def free_and_safe(empty_cols, crossed_cols):
            return all((board.piece_at((home, c)) is None for c in empty_cols)) and (not any((board.is_attacked((home, c), enemy) for c in crossed_cols)))
        if short_right in state.castling_rights and board.piece_at((home, 7)) == rook and free_and_safe([5, 6], [5, 6]):
            yield Move(origin, (home, 6), flag=MoveFlag.CASTLE)
        if long_right in state.castling_rights and board.piece_at((home, 0)) == rook and free_and_safe([1, 2, 3], [3, 2]):
            yield Move(origin, (home, 2), flag=MoveFlag.CASTLE)

class Pawn(Piece):
    kind = 'p'

    def attacks(self, board, origin):
        row, col = origin
        for d_col in (-1, 1):
            square = (row + self.color.pawn_direction, col + d_col)
            if inside(square):
                yield square

    def moves(self, board, origin, state):
        row, col = origin
        direction = self.color.pawn_direction
        ahead = (row + direction, col)
        if inside(ahead) and board.piece_at(ahead) is None:
            for item in self._pawn_moves(origin, ahead):
                yield item
            two_ahead = (row + 2 * direction, col)
            if row == self.color.pawn_start_row and board.piece_at(two_ahead) is None:
                for item in self._pawn_moves(origin, two_ahead):
                    yield item
        enemy_pawn = Pawn(self.color.opposite)
        for target in self.attacks(board, origin):
            occupant = board.piece_at(target)
            if occupant is not None and occupant.color is not self.color and (not isinstance(occupant, King)):
                for item in self._pawn_moves(origin, target):
                    yield item
            elif state.en_passant == target and board.piece_at((row, target[1])) == enemy_pawn:
                for item in self._pawn_moves(origin, target, MoveFlag.EN_PASSANT):
                    yield item

    @staticmethod
    def _pawn_moves(origin, target, flag=MoveFlag.NORMAL):
        if target[0] in (0, 7):
            for promotion in PROMOTION_LETTERS:
                yield Move(origin, target, promotion, flag)
        else:
            yield Move(origin, target, '', flag)
PIECE_TYPES = {cls.kind: cls for cls in (Pawn, Knight, Bishop, Rook, Queen, King)}

def piece_from_symbol(symbol):
    """``"N"`` -> white knight, ``"n"`` -> black knight."""
    color = Color.WHITE if symbol.isupper() else Color.BLACK
    return PIECE_TYPES[symbol.lower()](color)
