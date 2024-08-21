"""
Code for the perfect minimax Tic-Tac-Toe engine, and using it to detect key tactical motifs.

A Tic-Tac-Toe position is represented as a list of 9 elements giving the state of each square on the board:

0 1 2
3 4 5
6 7 8

The value must be ' ', 'X' or 'O'

Squares are represented either as indices (number from 0 to 8) or in chess-style algebraic notation
(a1 to c3). The internal representation is the index, but for external use, i.e. humans and AIs, it's
more convenient to use the algebraic notation.
"""

import pprint

# Convert an algebraic square location to an index.
def algebraic_to_index(algebraic):
    conversion = {
        'a1': 0, 'a2': 3, 'a3': 6,
        'b1': 1, 'b2': 4, 'b3': 7,
        'c1': 2, 'c2': 5, 'c3': 8
    }
    return conversion[algebraic]

# Convert an index square location to algebraic.
def index_to_algebraic(index):
    conversion = {
        0: 'a1', 3: 'a2', 6: 'a3',
        1: 'b1', 4: 'b2', 7: 'b3',
        2: 'c1', 5: 'c2', 8: 'c3'
    }
    return conversion[index]

# Get the name of the opposing player.
def get_opponent(player):
    return 'O' if player == 'X' else 'X'

# Get the value of the critical central square.
def get_center_square_value(board):
    return board[algebraic_to_index('b2')]

# Get the turn number by seeing how many empty squares there are and subtracting.
def get_turn_value(board):
    return 1 + 9 - len(get_available_moves(board))

# Check whether a given player has won.
def check_win(board, player):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # horizontal
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # vertical
        [0, 4, 8], [2, 4, 6]  # diagonal
    ]
    for condition in win_conditions:
        if all(board[i] == player for i in condition):
            return True
    return False

# Check whether the board is full
def check_draw(board):
    return all(s != ' ' for s in board)

# Return the empty squares.
def get_available_moves(board):
    return [i for i, s in enumerate(board) if s == ' ']

# Return the board state resulting from making a move
def apply_move(board, move, player):
    new_board = board.copy()
    new_board[move] = player
    return new_board

# Perfect player.
# board is the board position
# player is the player to move
# depth is the depth searched (for the initial call this should be 0)
#
# Returns a pair ( value, best_move ) where
# value is the result with correct play ( 1 = X wins, 0 = draw, -1 = O wins)
# best_move is a move which will produce the best result with continued best play on each side
def minimax(board, player, depth):
    opponent = get_opponent(player)
    
    if check_win(board, 'X'):
        return 1, None
    if check_win(board, 'O'):
        return -1, None
    if check_draw(board):
        return 0, None
    
    best_move = None
    if player == 'X':
        best_value = -float('inf')
        for move in get_available_moves(board):
            board[move] = player
            value, _ = minimax(board, opponent, depth + 1)
            board[move] = ' '
            if value > best_value:
                best_value = value
                best_move = move
    else:
        best_value = float('inf')
        for move in get_available_moves(board):
            board[move] = player
            value, _ = minimax(board, opponent, depth + 1)
            board[move] = ' '
            if value < best_value:
                best_value = value
                best_move = move
    
    return best_value, best_move

# Create a board state from a list of positions for X and O.
def get_board_from_positions(x_positions, o_positions):
    board = [' ' for _ in range(9)]
    for pos in x_positions:
        board[pos] = 'X'
    for pos in o_positions:
        board[pos] = 'O'
    return board

# Use the perfect player to get the position evaluation
def minimax_tic_tac_toe(x_positions_algebraic, o_positions_algebraic, player_to_move):
    x_positions = [algebraic_to_index(pos) for pos in x_positions_algebraic]
    o_positions = [algebraic_to_index(pos) for pos in o_positions_algebraic]
    
    board = get_board_from_positions(x_positions, o_positions)
    draw_board(board)
    
    evaluation, best_move = minimax(board, player_to_move, 0)
    
    result = 'win' if evaluation == 1 else 'loss' if evaluation == -1 else 'draw'
    best_move_algebraic = index_to_algebraic(best_move) if best_move is not None else None
    
    return result, best_move_algebraic

# Print the board position in a graphical human-friendly way
def draw_board(board):
    print(drawn_board_str(board))

# String with graphical human-friendly board position
def drawn_board_str(board):
    out_str = "  a b c\n"
    for row in range(2, -1, -1):
        out_str += f"{row + 1} {' '.join(board[row * 3: (row + 1) * 3])}\n"
    return out_str

# -----------------------------------------

# Returns current status of game as one of the following:
# ( 'win', 'X') Game is over and X won
# ( 'win', 'O' ) Game is over and O wom
# ( 'draw', None ) Game is over and it was a draw
# ('ongoing', None ) Game is still in progress
def is_game_over(board):
    if check_win(board, 'X'):
        return 'win', 'X'
    elif check_win(board, 'O'):
        return 'win', 'O'
    elif check_draw(board):
        return 'draw', None
    else:
        return 'ongoing', None

# board is a position and player is to play.
# Return the moves, in index form, which would let player win on the next move.
def get_threatened_moves(board, player):
    threatened_moves = []
    available_moves = get_available_moves(board)
    for move in available_moves:
        board[move] = player
        if check_win(board, player):
            threatened_moves.append(move)
        board[move] = ' '
    return threatened_moves

# board is a position and player is to play.
# Return the moves, in index form, which would let player threaten to win on the next move.
def get_threat_moves(board, player):
    threat_moves = []
    available_moves = get_available_moves(board)
    for move in available_moves:
        board[move] = player
        if len(get_threatened_moves(board, player)) > 0:
            threat_moves.append(move)
        board[move] = ' '
    return threat_moves

# board is a position and player is to play.
# Return the moves, in index form, which would let player threaten to win on the next move in two or more ways
def get_double_threat_moves(board, player):
    double_threat_moves = []
    available_moves = get_available_moves(board)
    for move in available_moves:
        board[move] = player
        if len(get_threatened_moves(board, player)) > 1:
            double_threat_moves.append(move)
        board[move] = ' '
    return double_threat_moves

# board is a position and player is to play.
# Return the moves, in algebraic form, for the common tactical motifs
def immediate_threats_and_opportunities(board, player):
    opponent = get_opponent(player)
    move_summaries = {
        'winning_moves': [],        # Immediate wins by player
        'opponent_threats': [],     # Moves that would let the opponent make a line if they were to move
        'double_threat': [],        # Moves that let player make a double threat to win
        'single_threat': [],        # Moves that let player make a single threat to win
        'double_threat_follow_up_to_single_threat': None      # A threat that can be followed up by a winning double threat
    }
    
    available_moves = get_available_moves(board)
    for move in available_moves:
        board[move] = player
        if check_win(board, player):
            move_summaries['winning_moves'].append(index_to_algebraic(move))
        board[move] = ' '
        
        board[move] = opponent
        if check_win(board, opponent):
            move_summaries['opponent_threats'].append(index_to_algebraic(move))
        board[move] = ' '
    
    # Check for double threats and single threats
    for move in available_moves:
        board[move] = player
        threatened_moves = get_threatened_moves(board, player)
        board[move] = ' '
        if len(threatened_moves) > 1:
            move_summaries['double_threat'].append(index_to_algebraic(move))
        elif len(threatened_moves) == 1:
            move_summaries['single_threat'].append(index_to_algebraic(move))

    # Check for follow-up double threat
    for threat_move in move_summaries['single_threat']:
        move_index = algebraic_to_index(threat_move)
        board[move_index] = player
        opponent_threat_moves = get_threatened_moves(board, player)
        if opponent_threat_moves:
            forced_move = opponent_threat_moves[0]  # Opponent's forced move
            board[forced_move] = opponent
            if not get_threatened_moves(board, opponent):  # Check that forced move is not itself a threat
                follow_up_double_threat_moves = get_double_threat_moves(board, player)
                if len(follow_up_double_threat_moves) > 0:
                    move_summaries['double_threat_follow_up_to_single_threat'] = threat_move
            board[forced_move] = ' '
        board[move_index] = ' '

    return move_summaries

# Return the result of immediate_threats_and_opportunities + the game status
def generate_position_summary(board, player):
    game_status, winner = is_game_over(board)
    summary = {
        'game_status': game_status,
        'winner': winner
    }
    if game_status == 'ongoing':
        threats_opportunities = immediate_threats_and_opportunities(board, player)
        summary.update(threats_opportunities)
    
    return summary

# Test above function
def test_generate_position_summary(x_positions_algebraic, o_positions_algebraic, player_to_move):
    x_positions = [algebraic_to_index(pos) for pos in x_positions_algebraic]
    o_positions = [algebraic_to_index(pos) for pos in o_positions_algebraic]
    
    board = get_board_from_positions(x_positions, o_positions)
    draw_board(board)

    summary = generate_position_summary(board, player_to_move)
    pprint.pprint(summary)
    
 
