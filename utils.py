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


def compare_move_against_best_move(engine, fen, move, depth=18):

    board = chess.Board(fen)

    info = engine.analyse(board, chess.engine.Limit(depth=depth))

    best_evaluation = info["score"].relative

    # Analyze the position after the candidate move has been played
    board.push(move)
    move_info = engine.analyse(board, chess.engine.Limit(depth=depth))
    move_evaluation = move_info["score"].relative
    board.pop()

    # Check for mate situations
    if not (move_info["score"].relative.is_mate() or info["score"].relative.is_mate()):
        return best_evaluation, best_evaluation.score() - (move_evaluation.score() * -1)
    elif best_evaluation.mate() and move_evaluation.mate():
        if(best_evaluation.mate()<=move_evaluation.mate()):
            #did NOT chose the fastest way to the mate, shame
            return best_evaluation, -10 #TODO: DECIDE HOW MUCH TO PENALIZE IT
        return best_evaluation, 0 #nice
    elif best_evaluation.mate():
        return best_evaluation, -999999  # move missed mate in n. shame
    return best_evaluation, -9999999 #sacc'd da King , shame on you dawg


def is_move_winning(engine, fen, move):
    if move.uci() == "g1g7":
        a = 42069
    print("checking move: "+str(move))
    best_eval, diff = compare_move_against_best_move(engine, fen, move)
    if best_eval.is_mate():
        return diff == 0
    elif 25 > diff > -25 and best_eval.score() >= -20:
        return True
    return False


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

    minimum_recap_piece = (999999, 0) #piece val/move tuple

    for recap in possible_recaps:
        recap_val = get_piece_value(board, recap.from_square)
        if recap_val<minimum_recap_piece[0]:
            minimum_recap_piece = (recap_val, recap)


        if recap_val < get_piece_value(board, square):
            can_recap_with_lower_valued_piece = True

    if can_recap_with_lower_valued_piece:
        return True

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

    answ = False

    #TODO: make it take with the lowest valued piece possible.
    for recap in possible_recaps:
        boardtwo = chess.Board(board.fen())
        boardtwo.push(recap)
        answ = is_piece_hanging(boardtwo, square, color)
    if answ:
        return True

    return False
    # TODO: ITS A SAC!!
    return True


# IS_PIECE_HANGING_SAFE: ALSO CHECKS IF THEY CAN ACTUALLY TAKE WITHOUT LOSING MATERIAL IMMEDIATELY, FIXES PAWN PUSHES
# THAT ARE "SACRIFICES" THAT ARE REALLY DISCOVERED ATTACKS ON HIGHER VALUED PIECES AND STUFF
# TODO: HANDLE POSSIBLE PROMOTIONS IF TAKES, RESULTING IN IMMEDIATE MAT GAIN.
def is_piece_hanging_s(board, square, color):
    turn = board.fen()

    if turn == "rnbqk2r/1p1pnpbp/2p1p1p1/p2P4/2B1P3/2N5/PPP1NPPP/R1BQK2R b KQkq - 0 7":
        a = 0
    if is_piece_hanging(board, square, color):

        if not turn == board.fen():
            print("did NOT pass the vibe check huzz")

        # TODO: CHECK IF TAKING THE PIECE LOSES MATERIAL

        # SIMULATE TAKING
        captures = get_legal_captures(board, square)
        sacced_p_value = get_piece_value(board, square)

        if sacced_p_value < 2:
            return False  # pawn lives do NOT matter

        is_there_good_capture = False or len(captures) == 0

        for capture in captures:
            board.push(capture)
            is_cap_poisonous = False

            # TODO: CHECK IF TAKING THE "SACCED" PIECE HANGS MATE

            legal_moves = board.legal_moves

            for move in legal_moves:

                board.push(move)
                if board.is_checkmate():
                    if len(captures)>1: #IF TAKING IS FORCED ITS BRILLIANT
                        is_cap_poisonous = True
                elif board.promoted and not is_piece_hanging(board, move.to_square, color):
                    is_cap_poisonous = True
                board.pop()

            opponents_pieces = get_pieces(board, not color)
            for piece in opponents_pieces:
                # TODO: MAKE IT ALSO CHECK WHETHER IT WAS NOT HANGING BEFORE THE MOVE WAS PLAYED..
                if is_piece_hanging(board, piece, not color) and get_piece_value(board, piece) >= sacced_p_value:
                    is_cap_poisonous = True
                else:
                    continue
            if not is_cap_poisonous:
                is_there_good_capture = True

            board.pop()
        if not turn == board.fen():
            print("did NOT pass the vibe check huzz")
        if not is_there_good_capture:
            return False
        return True
    return False


def sacrifices_material(fen, move, color):
    if move.uci() == "f3d4":
        a = 42069
    board = chess.Board(fen)

    if board.is_en_passant(move):
        return False  # EN PASSANT IS SIMPLY FORCED nah TODO: HANDLE EN PASSANT

    if board.is_capture(move):
        # TODO: BEFORE PUSHING THE MOVE CHECK IF IT CAPTURES A PIECE OF HIGHER OR EQUAL VALUE, IF SO ITS NOT A SAC AT
        #  ALL..
        if get_piece_value(board, move.from_square) <= get_piece_value(board, move.to_square):
            return False

    # Make the move
    board.push(move)
    return is_piece_hanging_s(board, move.to_square, color) or ignores_threats_s(fen, move, color)


# Function to get all color pieces on the board
def get_pieces(board, color):
    squares = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == color:
            squares.append(square)
    return squares


def get_hanging_pieces(fen, color):
    board = chess.Board(fen)

    turn = board.turn
    if turn == color:
        board.push(
            chess.Move.null())  # makes it the opponent's turn, possibly forfeits the opportunity to play en passant

    m_pieces = get_pieces(board, color)
    hanging_pieces = []

    for square in m_pieces:
        if is_piece_hanging(board, square, color):
            hanging_pieces.append(square)
    return hanging_pieces


# IGNORES THREATS SAFE. CHECKS FOR SITUATIONS WHERE IT DOES IGNORE THREATS BUT THERE WAS NO OTHER CHOICE
def ignores_threats_s(fen, move, color):
    if ignores_threats(fen, move, color):
        board = chess.Board(fen)

        # TODO: ADD A CHECK TO SEE IF YOU CAN POSSIBLY RESOLVE THE THREATS IN ONE MOVE IF SO THEN CONTINUE.
        could_have_saved_them_all = False
        legal_moves = board.legal_moves

        for m in legal_moves:
            board.push(m)
            num_hangs = len(get_hanging_pieces(board.fen(), color))
            if num_hangs == 0:
                could_have_saved_them_all = True
            board.pop()

        if not could_have_saved_them_all:
            return False
        return True
    return False


def ignores_threats(fen, move, color):
    # TODO: OK SO WE'RE HERE CUZ CURRENT MOVE IS NOT A SAC SO WE CAN OPERATE UNDER THIS ASSUMPTION: NOT REALLY A TODO
    #  BUT I LIKE THE WAY TOD0 TEXT IS HIGHLIGHTED TOD0: LOOP THROUGH ALL OUR PIECES TO SEE IF ANY OF THEM ARE
    #  HANGING AND CHECK IF MOVE DOESNT GET THEM OUT OF TROUBLE: AN ACTUAL TOD0

    # IT DOES NOT IGNORE THREATS A MOVE THAT DOES WHATEVER IT TAKES TO MINIMIZE MATERIAL LOSS

    if move.uci() == "h8h3":
        a = 42069
    board = chess.Board(fen)
    # TODO: CHECK IF MOVE SAVED THE HIGHEST AMOUNT OF MAT POSSIBLE

    fen = board.fen()
    hanging_pieces = get_hanging_pieces(board.fen(), color)

    max_hanging_piece_value_before = 0
    for piece in hanging_pieces:
        val = get_piece_value(board, piece)
        if val > max_hanging_piece_value_before:
            max_hanging_piece_value_before = val

    if not board.fen() == fen:
        print("did NOT pass the vibe check huzz")
    if len(hanging_pieces) == 0:
        return False

    is_capture = board.is_capture(move)

    board.push(move)

    _hanging_pieces = get_hanging_pieces(board.fen(), color)

    saved_pieces = []

    for piece in hanging_pieces:
        if not (piece in _hanging_pieces):
            hanging_pieces.remove(piece)
            saved_pieces.append((piece, get_piece_value(chess.Board(fen), piece)))

    if len(hanging_pieces) == 0:
        return False

    did_ignore_treat = True
    for piece in hanging_pieces:
        if not (piece in _hanging_pieces):
            did_ignore_treat = False

    # TODO: CHECK IF MOVE IGNORES THREAT TO ATTACK A PIECE OF HIGHER VALUE:

    board.push(chess.Move.null())  # make it our turn
    threats = get_legal_threats(board, move.to_square)
    board.pop()

    max_hanging_piece_value = 0
    for piece in _hanging_pieces:
        val = get_piece_value(board, piece)
        if val > max_hanging_piece_value:
            max_hanging_piece_value = val

    #TODO: MAKE IT SO THAT IT SAYS YOU PUSSIED OUT WHEN THE SUM OF THE PIECE VALUES YOU SAVED IS GREATER OR EQUAL TO THE MAX VALUED HANGING PIECE AFTER
    pussied_out = False
    for s_piece, s_p_val in saved_pieces:
        if s_p_val==max_hanging_piece_value_before:
            pussied_out = True
    if pussied_out:
        return False

    for capture in threats:
        if get_piece_value(board, capture.to_square) > max_hanging_piece_value:
            return False  # danger levels
        elif get_piece_value(board, capture.to_square) <= max_hanging_piece_value and is_piece_hanging(board,
                                                                                                       capture.to_square,
                                                                                                       color):
            captures = get_legal_captures(board, capture.to_square)
            for cap in captures:
                board.push(cap)
                if board.is_check():
                    return False
                board.pop()

    if did_ignore_treat:

        if max_hanging_piece_value < 2:
            return False  # pawns lives matter

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
                        is_piece_hanging_s(board, possible_cap.to_square, color)):
                    return False

            return True

        elif not is_capture:
            max_piece_hanging_after_adv = 0
            # TODO: CHECK IF NO MATTER WHAT PIECE GETS FREELY TAKEN A PIECE OF EQUAL OR GREATER VALUE IS HANGING AND WHAT WE'RE STILL HANGING HAS A LOWER VALUE THAN THE THINK WE TOOK MINUS THE ONE HE JUST TOOK:
            for piece in _hanging_pieces:
                caps = get_legal_captures(board, piece)

                for cap in caps:
                    pieces = get_pieces(board, not color)
                    board.push(cap)

                    is_cap_poisonous = False

                    # TODO: CHECK IF TAKING THE "SACCED" PIECE HANGS MATE

                    legal_moves = board.legal_moves

                    for move in legal_moves:

                        board.push(move)
                        if board.is_checkmate():
                            is_cap_poisonous = True
                        elif board.promoted and not is_piece_hanging(board, move.to_square, color):
                            is_cap_poisonous = True
                        board.pop()
                    if is_cap_poisonous:
                        return False

                    for a_piece in pieces:
                        val = get_piece_value(board, piece)
                        if is_piece_hanging(board, a_piece, not color) and val > max_piece_hanging_after_adv:
                            max_piece_hanging_after_adv = val
                    board.pop()
            if max_piece_hanging_after_adv > max_hanging_piece_value:
                return False
            return True

    return False


def check_move(engine, board, move, color):
    # TODO: ADD OTHER CRITERIA LIKE DOES IT IGNORE A FREE CAPTURE TO PLAY SOMETHING BETTER, ALSO LOOK FOR DESPERADOES
    answ = sacrifices_material(board.fen(), move, color)
    if move.uci() == "g1g7":
        a = 42069
    if answ:
        print(move.uci())
        if is_move_winning(engine, board.fen(), move):
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


import chess.pgn


# Function to modify PGN headers
def add_title_to_pgn(game, player_name):
    # Modify the player's title to GM if they are the white player
    if game.headers["White"] == player_name:
        game.headers["WhiteTitle"] = "GM"
        game.headers["WhiteElo"] = "9999"
        game.headers["BlackTitle"] = "NOOB"
        game.headers["BlackElo"] = "0"

    elif game.headers["Black"] == player_name:
        game.headers["BlackTitle"] = "GM"
        game.headers["BlackElo"] = "9999"
        game.headers["WhiteTitle"] = "NOOB"
        game.headers["WhiteElo"] = "0"


def save_game_to_pgn(game, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "a") as pgn_file:
        exporter = chess.pgn.FileExporter(pgn_file)
        game.accept(exporter)
