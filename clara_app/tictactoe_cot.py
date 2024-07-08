from .tictactoe_engine import get_opponent, minimax, get_board_from_positions, algebraic_to_index, index_to_algebraic

def validate_cot_analysis(board, player, cot_record, selected_move):
    opponent = get_opponent(player)
    # Use minimax to evaluate the current board state and get the optimal evaluation
    optimal_evaluation, _ = minimax(board, player, 0)
    
    # Apply the move suggested by GPT-4o
    selected_move_index = algebraic_to_index(selected_move)
    board[selected_move_index] = player
    
    # Evaluate the new board state after making the selected move
    selected_move_evaluation, _ = minimax(board, opponent, 0)

    board[selected_move_index] = ' '
    
    # Check if the evaluation of the selected move matches the optimal evaluation
    is_correct = (selected_move_evaluation == optimal_evaluation)
    
    return {
        'board': board,
        'player': player,
        'cot_record': cot_record,
        'selected_move': selected_move,
        'optimal_evaluation': optimal_evaluation,
        'selected_move_evaluation': selected_move_evaluation,
        'is_correct': is_correct
    }
