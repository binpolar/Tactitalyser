import glob
import os

import chess
import chess.pgn


def get_games(pgn):
    games = []
    pgn_file = open(pgn)
    while True:
        game = chess.pgn.read_game(pgn_file)
        # print(str(game))
        if game is None:
            break
        games.append((game, []))  # append game/candidate moves-fen pair,, pair? ( empty at first )

    return games


def get_all_games():
    all_games = []
    os.chdir("games/")
    for file in glob.glob("*.pgn"):
        print(file)

        all_games.extend(get_games(file))
    return all_games


# Define the material values for each piece
piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 99999,
}


# Function to count material for a specific side
def count_material(board, color):
    material = 0

    for piece_type in piece_values:
        material += len(board.pieces(piece_type, color)) * piece_values[piece_type]

    return material


def get_legal_captures(board, square):
    legal_captures = []
    for move in board.legal_moves:
        if move.to_square == square and board.is_capture(move):
            legal_captures.append(move)
    return legal_captures


def get_legal_threats(board, square):
    legal_threats = []
    for move in board.legal_moves:
        if move.from_square == square and board.is_capture(move):
            legal_threats.append(move)
    return legal_threats


def get_piece_value(board, square):
    return piece_values[board.piece_type_at(square)]


def compare_move_against_best_move(engine, fen, move, depth=14):
    board = chess.Board(fen)

    info = engine.analyse(board, chess.engine.Limit(depth=depth))

    best_evaluation = info["score"].relative.score()

    # Analyze the position after the candidate move has been played
    board.push(move)
    move_info = engine.analyse(board, chess.engine.Limit(depth=depth))
    move_evaluation = move_info["score"].relative.score()
    board.pop()

    # Check for mate situations
    if not (move_info["score"].relative.is_mate() or info["score"].relative.is_mate()):
        return best_evaluation - (move_evaluation * -1)
    else:
        return 0  # TODO: see if best move leads to mate faster, can't be bothered right now


def is_piece_hanging(board, square, color):
    opponent_color = chess.BLACK if color == chess.WHITE else chess.WHITE

    # Get the list of attackers and defenders for the destination square
    attackers = board.attackers(opponent_color, square)
    defenders = board.attackers(color, square)

    # TODO: DISCARD ATTACKERS THAT ARE PINNED TO THE KING
    recaps = get_legal_captures(board, square)
    actual_attackers = []
    for recap in recaps:
        if recap.to_square == square:
            actual_attackers.append(recap.from_square)
    for attacker in attackers:
        if not (attacker in actual_attackers):
            attackers.remove(attacker)

    # DEST SQUARE WAS UNPROTECTED, CARRY ON
    if len(attackers) < 1:
        return False

    # TODO: OK SO WE HAVE CAPTURED A PIECE OF LESSER VALUE, OR WE HA PLACED A PIECE WHERE IT CAN BE CAPTURED. CHECK
    #  IF THEY CAN RECAPTURE WITH A LOWER VALUE PIECE OR THEY HAVE AT LEAST ONE MORE ATTACKER THAN WE HAVE DEFENDERS.

    possible_recaps = get_legal_captures(board, square)
    can_recap_with_lower_valued_piece = False

    for recap in possible_recaps:
        if get_piece_value(board, recap.from_square) < get_piece_value(board, square):
            can_recap_with_lower_valued_piece = True

    if can_recap_with_lower_valued_piece:
        return True

    if len(attackers) <= len(defenders):
        return False

    # TODO: CHECK IF WE HAVE MORE THAN ONE DEFENDER, IF WE DONT HAVE ANY ITS CERTAINLY A SAC. IF NOT THEN CONTINUE

    if not len(defenders):
        return True

    # TODO: CHECK IF THEY CAN ONLY RECAPTURE WITH A PIECE WHOSE VALUE IS HIGHER THAN YOUR LOWEST VALUED DEFENDER IF
    #  SO THEN ITS NOT A SAC

    possible_recaps = get_legal_captures(board, square)
    can_only_recap_with_higher_valued_piece = True

    for recap in possible_recaps:
        if get_piece_value(board, recap.from_square) <= get_piece_value(board, square):
            can_only_recap_with_higher_valued_piece = False

    if can_only_recap_with_higher_valued_piece:
        return False

    # TODO: ITS A SAC!!
    return True


# IS_PIECE_HANGING_SAFE: ALSO CHECKS IF THEY CAN ACTUALLY TAKE WITHOUT LOSING MATERIAL IMMEDIATELY, FIXES PAWN PUSHES
# THAT ARE "SACRIFICES" THAT ARE REALLY DISCOVERED ATTACKS ON HIGHER VALUED PIECES AND STUFF
def is_piece_hanging_s(board, square, color):
    if is_piece_hanging(board, square, color):
        # TODO: CHECK IF TAKING THE PIECE LOSES MATERIAL

        # SIMULATE TAKING
        captures = get_legal_captures(board, square)
        sacced_p_value = get_piece_value(board, square)

        is_there_good_capture = False or len(captures) == 0

        for capture in captures:
            board.push(capture)
            is_cap_poisonous = False

            # TODO: CHECK IF TAKING THE "SACCED" PIECE HANGS MATE

            legal_moves = board.legal_moves

            for move in legal_moves:

                board.push(move)
                if board.is_checkmate():
                    is_cap_poisonous = True
                board.pop()

            opponents_pieces = get_pieces(board, not color)
            for piece in opponents_pieces:
                # TODO: MAKE IT ALSO CHECK WHETHER IT WAS NOT HANGING BEFORE THE MOVE WAS PLAYED..
                if is_piece_hanging(board, piece, not color) and get_piece_value(board, piece) > sacced_p_value:
                    is_cap_poisonous = True
                else:
                    continue
            if not is_cap_poisonous:
                is_there_good_capture = True

            board.pop()

        if not is_there_good_capture:
            return False
        return True
    return False


def sacrifices_material(fen, move, color):
    if move.uci() == "f1d3":
        a = 0

    board = chess.Board(fen)

    if board.is_en_passant(move):
        return False  # EN PASSANT IS SIMPLY FORCED

    if board.is_capture(move):
        # TODO: BEFORE PUSHING THE MOVE CHECK IF IT CAPTURES A PIECE OF HIGHER OR EQUAL VALUE, IF SO ITS NOT A SAC AT
        #  ALL..
        if get_piece_value(board, move.from_square) <= get_piece_value(board, move.to_square):
            return False

        # TODO: CHECK IF PUSHING THE MOVE MAKES A DISCOVERY ATTACK ON AN HIGHER VALUED PIECE THAN THE ONE WERE MOVING OR IF OPPONENT CANT TAKE BECAUSE IF TAKES THEN AN HIGHER VALUED PIECE OF THE ONE WE MOVED IS HANGING

    # Make the move
    board.push(move)

    return is_piece_hanging_s(board, move.to_square, color)


# Function to get all color pieces on the board
def get_pieces(board, color):
    squares = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == color:
            squares.append(square)
    return squares


def ignores_threats(fen, move, color):
    # TODO: OK SO WE'RE HERE CUZ CURRENT MOVE IS NOT A SAC SO WE CAN OPERATE UNDER THIS ASSUMPTION: NOT REALLY A TODO
    #  BUT I LIKE THE WAY TOD0 TEXT IS HIGHLIGHTED TOD0: LOOP THROUGH ALL OUR PIECES TO SEE IF ANY OF THEM ARE
    #  HANGING AND CHECK IF MOVE DOESNT GET THEM OUT OF TROUBLE: AN ACTUAL TOD0
    if move.uci() == "g4g3":
        a = 42069
    board = chess.Board(fen)
    m_pieces = get_pieces(board, color)
    hanging_pieces = []

    board.push(chess.Move.null())  # makes it the opponent's turn, possibly forfeits the opportunity to play en passant,

    for square in m_pieces:
        if is_piece_hanging_s(board, square, color):
            hanging_pieces.append(square)
    board.pop()  # REGAIN OUR EN PASSANT PRIVILEGES

    if len(hanging_pieces) == 0:
        return False

    is_capture = board.is_capture(move)

    board.push(move)

    _m_pieces = get_pieces(board, color)
    _hanging_pieces = []

    for square in _m_pieces:
        if is_piece_hanging_s(board, square, color):
            _hanging_pieces.append(square)

    for piece in hanging_pieces:
        if not (piece in _hanging_pieces):
            hanging_pieces.remove(piece)

    if len(hanging_pieces)==0:
        return False

    did_ignore_treat = True
    for piece in hanging_pieces:
        if not (piece in _hanging_pieces):
            did_ignore_treat = False


    # TODO: CHECK IF MOVE IGNORES THREAT TO ATTACK A PIECE OF HIGHER VALUE:

    board.push(chess.Move.null())  # make it our turn
    threats = get_legal_threats(board, move.to_square)

    max_hanging_piece_value = 0
    for piece in _hanging_pieces:
        val = get_piece_value(board, piece)
        if val > max_hanging_piece_value:
            max_hanging_piece_value = val

    for capture in threats:
        if get_piece_value(board, capture.to_square) > max_hanging_piece_value:
            return False  # cuz of danger levels

    board.pop()

    if did_ignore_treat:

        # TODO: THIS SHOULD MEAN THAT WE IGNORED THE TREAT ON AN HANGING PIECE OF OURS. CHECK IF THE VALUE OF THE
        #  HIGHEST PIECE THREATENED IS LESS THAN THE VALUE OF THE CAPTURE IF THE MOVE IS A CAPTURE

        if is_capture and get_piece_value(board, move.to_square) >= max_hanging_piece_value:
            return False
        elif is_capture and get_piece_value(board, move.to_square) < max_hanging_piece_value:
            # TODO: check if move also threatens other pieces resulting in eventual mat gain, if so them its not
            #  brilliant at all
            mat_gain = get_piece_value(board, move.to_square)

            for possible_cap in threats:
                if (get_piece_value(board, possible_cap.to_square) + mat_gain >= max_hanging_piece_value) and (
                        is_piece_hanging(board, possible_cap.to_square)):
                    return False

        elif not is_capture:
            return True

    return False


def check_move(engine, board, move, color):
    # TODO: ADD OTHER CRITERIA LIKE DOES IT IGNORE A FREE CAPTURE TO PLAY SOMETHING BETTER

    if sacrifices_material(board.fen(), move, color) or ignores_threats(board.fen(), move, color):

        # TODO: CHECK IF TAKING

        diff = compare_move_against_best_move(engine, board.fen(), move)
        if 20 > diff > 0:
            return True
    return False


def do_turn(engine, board, move, color, moves):
    if check_move(engine, board, move, color):
        print("brilliant move " + str(move))
        moves.append(move)


def iterate_game(engine, game, moves, player, treshold=0.07):
    board = game.board()
    white = game.headers["White"]
    color = chess.BLACK

    is_white = player == white
    if is_white:
        color = chess.WHITE

    for move in game.mainline_moves():
        turn = board.turn
        board.push(move)

        if board.is_checkmate():
            break
        board.pop()

        if (turn and is_white) or (not turn and not is_white):
            do_turn(engine, board, move, color, moves)

        board.push(move)


def save_game_to_pgn(game, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "a") as pgn_file:
        exporter = chess.pgn.FileExporter(pgn_file)
        game.accept(exporter)
