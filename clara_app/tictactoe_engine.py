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

def check_draw(board):
    return all(s != ' ' for s in board)

def get_available_moves(board):
    return [i for i, s in enumerate(board) if s == ' ']

def minimax(board, player, depth):
    opponent = 'O' if player == 'X' else 'X'
    
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

def get_board_from_positions(x_positions, o_positions):
    board = [' ' for _ in range(9)]
    for pos in x_positions:
        board[pos] = 'X'
    for pos in o_positions:
        board[pos] = 'O'
    return board

def algebraic_to_index(algebraic):
    conversion = {
        'a1': 0, 'a2': 3, 'a3': 6,
        'b1': 1, 'b2': 4, 'b3': 7,
        'c1': 2, 'c2': 5, 'c3': 8
    }
    return conversion[algebraic]

def index_to_algebraic(index):
    conversion = {
        0: 'a1', 3: 'a2', 6: 'a3',
        1: 'b1', 4: 'b2', 7: 'b3',
        2: 'c1', 5: 'c2', 8: 'c3'
    }
    return conversion[index]

def minimax_tic_tac_toe(x_positions_algebraic, o_positions_algebraic, player_to_move):
    x_positions = [algebraic_to_index(pos) for pos in x_positions_algebraic]
    o_positions = [algebraic_to_index(pos) for pos in o_positions_algebraic]
    
    board = get_board_from_positions(x_positions, o_positions)
    draw_board(board)
    
    evaluation, best_move = minimax(board, player_to_move, 0)
    
    result = 'win' if evaluation == 1 else 'loss' if evaluation == -1 else 'draw'
    best_move_algebraic = index_to_algebraic(best_move) if best_move is not None else None
    
    return result, best_move_algebraic

def draw_board(board):
    print("  a b c")
    for row in range(2, -1, -1):
        print(row + 1, ' '.join(board[row * 3: (row + 1) * 3]))

# Example usage:
##x_positions_algebraic = ['a1', 'b2']
##o_positions_algebraic = ['b1', 'b3']
##player_to_move = 'X'
##result, best_move = minimax_tic_tac_toe(x_positions_algebraic, o_positions_algebraic, player_to_move)
##print(f"Result: {result}, Best Move: {best_move}")
