from __future__ import print_function

try:
    console_input = raw_input
except NameError:
    console_input = input

"""Console front end. Input and output are injected so the loop can be tested."""
from .game import Game, GameStatus
from .move import Move
from .notation import parse_move
from .renderer import BoardRenderer
END_MESSAGES = {GameStatus.STALEMATE: 'STALEMATE! Draw.', GameStatus.INSUFFICIENT_MATERIAL: 'DRAW: insufficient material.', GameStatus.FIVEFOLD_REPETITION: 'DRAW: fivefold repetition.', GameStatus.SEVENTY_FIVE_MOVE_RULE: 'DRAW: 75-move rule.'}
HELP_TEXT = 'Enter moves like e2e4 (from e2 to e4).\nCastling: O-O or O-O-O (or e1g1 / e1c1).\nPromotion: e7e8q (q=queen, r=rook, b=bishop, n=knight).\nWithout a promotion letter, a queen is selected.\nmoves: show legal moves; undo: take back the last move.\nclaim: claim a draw (3 repetitions or 50-move rule).\nquit: exit the game.'

class ConsoleUI(object):

    def __init__(self, game=None, input_fn=console_input, output_fn=print, renderer=None):
        self.game = game or Game()
        self._input = input_fn
        self._print = output_fn
        self._renderer = renderer or BoardRenderer()
        self._commands = {'quit': self._quit, 'quitter': self._quit, 'exit': self._quit, 'help': self._help, 'aide': self._help, 'moves': self._list_moves, 'coups': self._list_moves, 'undo': self._undo, 'annuler': self._undo, 'claim': self._claim, 'nul': self._claim}

    def run(self):
        self._print('=== LOCAL CHESS GAME ===')
        self._print('Moves: e2e4, g1f3, e7e8q, O-O, O-O-O')
        self._print('Commands: help, moves, undo, claim, quit')
        while True:
            self._print(self._renderer.render(self.game.state.board))
            if self._announce_end_or_warnings():
                return
            side = self.game.state.turn.label
            try:
                entered = self._input('{0} to move > '.format(side)).strip()
            except EOFError:
                self._print('Game over.')
                return
            handler = self._commands.get(entered.lower())
            if handler is not None:
                if handler():
                    return
                continue
            self._play_text_move(entered)

    def _announce_end_or_warnings(self):
        status = self.game.status()
        if status is GameStatus.CHECKMATE:
            self._print('CHECKMATE! {0} wins.'.format(self.game.winner().label))
        elif status is not GameStatus.ONGOING:
            self._print(END_MESSAGES[status])
        else:
            if self.game.in_check():
                self._print('CHECK!')
            if self.game.can_claim_draw():
                self._print('You may claim a draw: type claim.')
        return status is not GameStatus.ONGOING

    def _play_text_move(self, text):
        request = parse_move(text, self.game.state)
        move = self.game.find_move(request) if request else None
        if move is None:
            self._print('Illegal move. Type moves or help.')
            return
        self._print('Move played: {0}'.format(move))
        self.game.play(move)

    def _quit(self):
        self._print('Game over.')
        return True

    def _help(self):
        self._print(HELP_TEXT)
        return False

    def _list_moves(self):
        self._print('Legal moves: ' + ' '.join(sorted((str(m) for m in self.game.legal_moves()))))
        return False

    def _undo(self):
        self._print('Last move undone.' if self.game.undo() else 'No move to undo.')
        return False

    def _claim(self):
        if self.game.can_claim_draw():
            self._print('DRAW!')
            return True
        self._print('You cannot claim a draw yet.')
        return False
