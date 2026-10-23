from .legacy_enum import Enum
from . import rules
from .common import Color
from .game_state import GameState
from .move import Move, MoveRequest

class GameStatus(Enum):
    pass
GameStatus.ONGOING = GameStatus._member('ONGOING', 'ongoing')
GameStatus.CHECKMATE = GameStatus._member('CHECKMATE', 'checkmate')
GameStatus.STALEMATE = GameStatus._member('STALEMATE', 'stalemate')
GameStatus.INSUFFICIENT_MATERIAL = GameStatus._member('INSUFFICIENT_MATERIAL', 'insufficient material')
GameStatus.FIVEFOLD_REPETITION = GameStatus._member('FIVEFOLD_REPETITION', 'fivefold repetition')
GameStatus.SEVENTY_FIVE_MOVE_RULE = GameStatus._member('SEVENTY_FIVE_MOVE_RULE', '75-move rule')

class Game(object):
    """A game in progress: the position history, undo and end-of-game detection."""
    CLAIM_REPETITIONS = 3
    CLAIM_HALFMOVES = 100
    FORCED_REPETITIONS = 5
    FORCED_HALFMOVES = 150

    def __init__(self, state=None):
        self._history = [state or GameState.initial()]
        self._keys = [rules.position_key(self._history[0])]

    @property
    def state(self):
        return self._history[-1]

    def legal_moves(self):
        return rules.legal_moves(self.state)

    def find_move(self, request):
        return next((m for m in self.legal_moves() if m.matches(request)), None)

    def play(self, move):
        self._history.append(self.state.apply(move))
        self._keys.append(rules.position_key(self.state))

    def undo(self):
        if len(self._history) == 1:
            return False
        self._history.pop()
        self._keys.pop()
        return True

    def in_check(self):
        return rules.is_in_check(self.state)

    def repetitions(self):
        return self._keys.count(self._keys[-1])

    def can_claim_draw(self):
        return self.repetitions() >= self.CLAIM_REPETITIONS or self.state.halfmove >= self.CLAIM_HALFMOVES

    def status(self):
        if not self.legal_moves():
            return GameStatus.CHECKMATE if self.in_check() else GameStatus.STALEMATE
        if rules.insufficient_material(self.state.board):
            return GameStatus.INSUFFICIENT_MATERIAL
        if self.repetitions() >= self.FORCED_REPETITIONS:
            return GameStatus.FIVEFOLD_REPETITION
        if self.state.halfmove >= self.FORCED_HALFMOVES:
            return GameStatus.SEVENTY_FIVE_MOVE_RULE
        return GameStatus.ONGOING

    def winner(self):
        return self.state.turn.opposite if self.status() is GameStatus.CHECKMATE else None
