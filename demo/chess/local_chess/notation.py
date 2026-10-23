"""Converting between text typed by the player and moves."""
from .common import PROMOTION_LETTERS, parse_square
from .game_state import GameState
from .move import MoveRequest
from .pieces import Pawn

def parse_move(text, state):
    text = text.lower().strip().replace(' ', '')
    home = state.turn.home_row
    castle = text.replace('-', '')
    if castle in ('oo', '00'):
        return MoveRequest((home, 4), (home, 6))
    if castle in ('ooo', '000'):
        return MoveRequest((home, 4), (home, 2))
    if len(text) not in (4, 5):
        return None
    origin, target = (parse_square(text[:2]), parse_square(text[2:4]))
    if origin is None or target is None:
        return None
    promotion = ''
    if len(text) == 5:
        promotion = text[4]
        if promotion not in PROMOTION_LETTERS:
            return None
    elif isinstance(state.board.piece_at(origin), Pawn) and target[0] in (0, 7):
        promotion = 'q'
    return MoveRequest(origin, target, promotion)
