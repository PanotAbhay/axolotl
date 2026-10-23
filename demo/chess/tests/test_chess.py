import unittest
from local_chess import Game, GameState, GameStatus
from local_chess.cli import ConsoleUI
from local_chess.common import Color, parse_square
from local_chess.notation import parse_move
from local_chess.rules import insufficient_material, legal_moves

def perft(state, depth):
    if depth == 0:
        return 1
    return sum((perft(state.apply(m), depth - 1) for m in legal_moves(state)))
START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
KIWIPETE = 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1'
POSITION_3 = '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1'
POSITION_4 = 'r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1'

def play_text(game, *moves):
    for text in moves:
        move = game.find_move(parse_move(text, game.state))
        assert move is not None, text
        game.play(move)

def scripted_ui(*lines):
    feed, out = (iter(lines), [])

    def fake_input(prompt):
        try:
            return next(feed)
        except StopIteration:
            raise EOFError
    ConsoleUI(input_fn=fake_input, output_fn=out.append).run()
    return '\n'.join(out)

class ChessTests(unittest.TestCase):

    def test_perft(self):
        for fen, depth, expected in [(START, 3, 8902), (KIWIPETE, 2, 2039), (POSITION_3, 3, 2812), (POSITION_4, 2, 264)]:
            assert perft(GameState.from_fen(fen), depth) == expected

    def test_fools_mate(self):
        game = Game()
        play_text(game, 'f2f3', 'e7e5', 'g2g4', 'd8h4')
        assert game.status() is GameStatus.CHECKMATE
        assert game.winner() is Color.BLACK

    def test_stalemate_and_insufficient_material(self):
        stalemate = Game(GameState.from_fen('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1'))
        assert stalemate.status() is GameStatus.STALEMATE
        assert insufficient_material(GameState.from_fen('8/8/4k3/8/8/3K4/3B4/8 w - - 0 1').board)
        assert not insufficient_material(GameState.from_fen('8/8/4k3/8/8/3K4/3R4/8 w - - 0 1').board)

    def test_castling_en_passant_promotion(self):
        game = Game(GameState.from_fen('r3k2r/8/8/3pP3/8/8/8/R3K2R w KQkq d6 0 1'))
        play_text(game, 'e5d6')
        assert game.state.board.piece_at(parse_square('d5')) is None
        play_text(game, 'O-O-O')
        assert game.state.board.piece_at(parse_square('d8')).symbol == 'r'
        promo = Game(GameState.from_fen('8/P6k/8/8/8/8/8/K7 w - - 0 1'))
        play_text(promo, 'a7a8')
        assert promo.state.board.piece_at(parse_square('a8')).symbol == 'Q'

    def test_castling_through_check_is_illegal(self):
        state = GameState.from_fen('4k3/8/8/8/8/5r2/8/4K2R w K - 0 1')
        assert not any((str(m) == 'e1g1' for m in legal_moves(state)))

    def test_undo_and_repetition_claim(self):
        game = Game()
        shuffle = ['g1f3', 'g8f6', 'f3g1', 'f6g8']
        play_text(game, *(shuffle + shuffle))
        assert game.repetitions() == 3 and game.can_claim_draw()
        assert game.undo() and game.repetitions() == 2

    def test_parse_move_rejects_garbage(self):
        state = GameState.initial()
        for text in ['', 'e2', 'z2e4', 'e9e4', 'e2e4x', 'e7e8k']:
            assert parse_move(text, state) is None

    def test_cli_session(self):
        text = scripted_ui('help', 'e2e5', 'e2e4', 'moves', 'undo', 'undo', 'claim', 'f2f3', 'e7e5', 'g2g4', 'd8h4')
        assert 'Illegal move' in text and 'No move to undo.' in text
        assert 'You cannot claim a draw yet.' in text
        assert 'CHECKMATE! Black wins.' in text

if __name__ == "__main__":
    unittest.main()
