from .common import BOARD_SIZE, Color, inside
from .pieces import King, Piece, piece_from_symbol
INITIAL_ROWS = ['rnbqkbnr', 'pppppppp', '........', '........', '........', '........', 'PPPPPPPP', 'RNBQKBNR']

class Board(object):
    """An 8x8 grid of optional pieces. Mutable, but ``copy()`` is cheap."""

    def __init__(self, grid):
        self._grid = grid

    @classmethod
    def from_rows(cls, rows):
        return cls([[None if ch == '.' else piece_from_symbol(ch) for ch in row] for row in rows])

    @classmethod
    def initial(cls):
        return cls.from_rows(INITIAL_ROWS)

    def copy(self):
        return Board([row[:] for row in self._grid])

    def piece_at(self, square):
        return self._grid[square[0]][square[1]]

    def place(self, square, piece):
        self._grid[square[0]][square[1]] = piece

    def pieces(self, color=None):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self._grid[row][col]
                if piece is not None and (color is None or piece.color is color):
                    yield ((row, col), piece)

    def find_king(self, color):
        for square, piece in self.pieces(color):
            if isinstance(piece, King):
                return square
        return None

    def is_attacked(self, square, by):
        return any((square in piece.attacks(self, origin) for origin, piece in self.pieces(by)))

    def is_in_check(self, color):
        king = self.find_king(color)
        return True if king is None else self.is_attacked(king, color.opposite)

    def rows(self):
        """Text rows, ``.`` for empty squares (white uppercase, black lowercase)."""
        return [''.join(('.' if p is None else p.symbol for p in row)) for row in self._grid]
