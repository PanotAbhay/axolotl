from collections import namedtuple

from .board import Board
from .common import Color, parse_square
from .move import Move, MoveFlag
from .pieces import PIECE_TYPES, King, Pawn
_ROOK_CORNERS = [((7, 7), 'K'), ((7, 0), 'Q'), ((0, 7), 'k'), ((0, 0), 'q')]

class GameState(namedtuple('GameStateBase', 'board turn castling_rights en_passant halfmove fullmove')):
    __slots__ = ()

    def __new__(cls, board, turn=Color.WHITE, castling_rights='KQkq', en_passant=None, halfmove=0, fullmove=1):
        return super(GameState, cls).__new__(cls, board, turn, castling_rights, en_passant, halfmove, fullmove)
    'One position plus the extra rules data. ``apply`` returns a new state.'

    @classmethod
    def initial(cls):
        return cls(Board.initial())

    @classmethod
    def from_fen(cls, fen):
        parts = fen.split()
        rows = [''.join(('.' * int(ch) if ch.isdigit() else ch for ch in rank)) for rank in parts[0].split('/')]
        return cls(board=Board.from_rows(rows), turn=Color(parts[1]), castling_rights='' if parts[2] == '-' else parts[2], en_passant=None if parts[3] == '-' else parse_square(parts[3]), halfmove=int(parts[4]) if len(parts) > 4 else 0, fullmove=int(parts[5]) if len(parts) > 5 else 1)

    def apply(self, move):
        board = self.board.copy()
        (from_row, from_col), (to_row, to_col) = (move.origin, move.target)
        piece = board.piece_at(move.origin)
        captured = board.piece_at(move.target)
        board.place(move.origin, None)
        board.place(move.target, PIECE_TYPES[move.promotion](self.turn) if move.promotion else piece)
        if move.flag is MoveFlag.EN_PASSANT:
            board.place((from_row, to_col), None)
        if move.flag is MoveFlag.CASTLE:
            rook_from, rook_to = (7, 5) if to_col == 6 else (0, 3)
            board.place((to_row, rook_to), board.piece_at((to_row, rook_from)))
            board.place((to_row, rook_from), None)
        rights = self.castling_rights
        if isinstance(piece, King):
            for letter in piece.color.castling_letters:
                rights = rights.replace(letter, '')
        for corner, letter in _ROOK_CORNERS:
            if corner in (move.origin, move.target):
                rights = rights.replace(letter, '')
        en_passant = None
        if isinstance(piece, Pawn) and abs(to_row - from_row) == 2:
            en_passant = ((from_row + to_row) // 2, from_col)
        irreversible = isinstance(piece, Pawn) or captured is not None or move.flag is MoveFlag.EN_PASSANT
        return GameState(board=board, turn=self.turn.opposite, castling_rights=rights, en_passant=en_passant, halfmove=0 if irreversible else self.halfmove + 1, fullmove=self.fullmove + (1 if self.turn is Color.BLACK else 0))
