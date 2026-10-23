from .board import Board
_FILE_LABELS = '    a b c d e f g h'

class BoardRenderer(object):
    """Draws a board as plain text."""

    def render(self, board):
        lines = ['', _FILE_LABELS, '']
        for index, row in enumerate(board.rows()):
            rank = 8 - index
            lines.append(' {0}  {1}  {2}'.format(rank, ' '.join(row), rank))
        lines += ['', _FILE_LABELS, '', 'UPPERCASE = White; lowercase = Black']
        return '\n'.join(lines)
