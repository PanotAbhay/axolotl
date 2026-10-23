"""Local two-player chess for the console."""
from .game import Game, GameStatus
from .game_state import GameState
__all__ = ['Game', 'GameStatus', 'GameState']
__version__ = '2.0.0'
