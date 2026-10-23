"""Pure functions that apply the rules of chess to a ``GameState``."""
from .board import Board
from .common import square_name
from .game_state import GameState
from .move import Move, MoveFlag
from .pieces import Bishop, King

def pseudo_legal_moves(state):
    for origin, piece in state.board.pieces(state.turn):
        for item in piece.moves(state.board, origin, state):
            yield item

def legal_moves(state):
    return [move for move in pseudo_legal_moves(state) if not state.apply(move).board.is_in_check(state.turn)]

def is_in_check(state):
    return state.board.is_in_check(state.turn)

def insufficient_material(board):
    """Obvious dead positions: bare kings, king + one minor piece, or only
    bishops standing on the same square color."""
    others = [(piece, (row + col) % 2) for (row, col), piece in board.pieces() if not isinstance(piece, King)]
    if not others:
        return True
    if len(others) == 1 and others[0][0].kind in 'bn':
        return True
    first_color = others[0][1]
    return all((isinstance(piece, Bishop) and shade == first_color for piece, shade in others))

def position_key(state):
    """Identity of a position for repetition counting.

    The en passant square only counts if the capture is actually legal."""
    key = ''.join(state.board.rows()) + state.turn.value + '/' + state.castling_rights + '/'
    if state.en_passant is not None and any((m.flag is MoveFlag.EN_PASSANT for m in legal_moves(state))):
        key += square_name(state.en_passant)
    return key
