from chess.svg import board
import utils as utils
import chess
import chess.engine

stockfish_path = "C:\\Users\\PC\\Desktop\\Tactitalyzer\\stockfish\\stockfish-windows-x86-64-avx2.exe"


def main():
    games = utils.get_all_games()
    name = "Miguel Najdorf"

    out = "games/out.pgn"

    done = 0
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        engine.configure({"Threads": 16})
        for game, moves in games:
            print("####### GAME " + str(done) + " OUT OF " + str(len(games)) + " ########")

            utils.iterate_game(engine, game, moves, name)

            if len(moves) > 0:
                utils.save_game_to_pgn(game, out)
            done += 1


if __name__ == "__main__":
    main()
