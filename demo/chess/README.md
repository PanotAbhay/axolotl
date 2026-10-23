# local-chess: Axolotl migration input

Two players, one computer, no runtime dependencies. This source targets
**Python 2.7** as the input for Axolotl's migration to Python 3.14.

From this directory, run with Python 2.7:

```console
python2.7 -m local_chess
python2.7 -m unittest discover -s tests -v
```

On Windows with Python 2.7 registered in the Python launcher, use `py -2.7`
instead of `python2.7`. The application and tests use only the standard library.
Optional installation uses `setup.py` with Python 2.7-compatible setuptools
(44.1.1).

## Layout

| Module | Responsibility |
|---|---|
| `common.py` | Colors, squares, board geometry |
| `move.py` | Immutable move and move-request records |
| `pieces.py` | Piece movement and attacks |
| `board.py` | Board storage, attack and check detection |
| `game_state.py` | Immutable position record and move application |
| `rules.py` | Legal moves, material checks, repetition keys |
| `game.py` | History, undo, game status |
| `notation.py` | Typed moves such as `e2e4` and `O-O` |
| `renderer.py` | Plain-text board rendering |
| `cli.py` | Console interaction using Python 2's `raw_input` |
| `legacy_enum.py` | Dependency-free named constants |

The tests cover four reference move-count positions, special moves, checkmate,
draw detection, undo, parsing, and a scripted console session. After migration,
run the same suite with `python3.14 -m unittest discover -s tests -v`.

The source also runs on Python 3.14 for comparison. Legacy constructs include
explicit `super` arguments, `__metaclass__`, namedtuple record classes, and
`setup.py`. Python 2.7 compatibility does not itself require a conversion to
run on Python 3.14; this fixture can demonstrate modernization, but is not a
fixture of Python-2-only syntax failures.

Validation in this workspace: all eight test methods pass under Python 2.7.18
using a temporary runtime. The suite also passes under Python 3.14.

Use this directory as Axolotl's input. `../local-chess.zip` remains the original
Python 3 archive and has not been updated.
