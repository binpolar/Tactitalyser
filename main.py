from chess.svg import board
import utils as utils
import chess
import chess.engine

stockfish_path = "C:\\Users\\dario\\PycharmProjects\\Tactitalyzer\\stockfish\\stockfish-windows-x86-64-avx2.exe"


def main():
    games = utils.get_all_games()
    name = "name"

    out = "games/out.pgn"

    done = 0
    brilliances = 0

    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        engine.configure({"Threads": 16})
        for game, moves in games:
            print("####### GAME " + str(done) + " OUT OF " + str(len(games)) + " ########")

            utils.iterate_game(engine, game, moves, name)

            count = len(moves)
            print(str(count))

            if count > 0:
                head = game.headers
                utils.add_title_to_pgn(game, name)
                utils.save_game_to_pgn(game, out)
                brilliances += count

                print(game)
                print(moves)
            done += 1
    print("found " + str(brilliances) + " brilliant moves!!")


if __name__ == "__main__":
    main()
