
from .tictactoe_engine import minimax, get_board_from_positions, draw_board, get_available_moves, check_win, check_draw
from .tictactoe_engine import index_to_algebraic, algebraic_to_index
from .tictactoe_gpt4 import request_minimal_gpt4_move, request_cot_analysis_and_move

from .clara_utils import post_task_update

import random
import json
import traceback

known_players = ( 'random_player', 'human_player', 'minimax_player', 'minimal_gpt4_player', 'cot_player_without_few_shot' )

def random_player(board, player, callback=None):
    moves = get_available_moves(board)
    return random.choice(moves)

def human_player(board, player, callback=None):
    draw_board(board)
    move = input(f"Player {player}, enter your move (e.g., a1, b2): ")
    return algebraic_to_index(move)

def minimax_player(board, player, callback=None):
    _, best_move = minimax(board, player, 0)
    return best_move

def minimal_gpt4_player(board, player, callback=None):
    response = request_minimal_gpt4_move(board, player, callback=callback)
    return algebraic_to_index(response['selected_move'])

def cot_player_without_few_shot(board, player, callback=None):
    few_shot_examples = []
    response = request_cot_analysis_and_move(board, player, few_shot_examples, callback=callback)
    return algebraic_to_index(response['selected_move'])

def invoke_player(player_name, board, x_or_o, callback=None):
    complain_if_unknown_player(player_name, callback=callback)
    
    if player_name == 'random_player':
        return random_player(board, x_or_o, callback=callback)
    elif player_name == 'human_player':
        return human_player(board, x_or_o, callback=callback)
    elif player_name == 'minimax_player':
        return minimax_player(board, x_or_o, callback=callback)
    elif player_name == 'minimal_gpt4_player':
        return minimal_gpt4_player(board, x_or_o, callback=callback)
    elif player_name == 'cot_player_without_few_shot':
        return cot_player_without_few_shot(board, x_or_o, callback=callback)

def complain_if_unknown_player(player_name, callback=None):
    if not player_name in known_players:
        error_message = f'Unknown player name: {player_name}'
        post_task_update(callback, error_message)
        raise ValueError(error_message)

def play_game(player1, player2, callback=None):
    complain_if_unknown_player(player1, callback=callback)
    complain_if_unknown_player(player2, callback=callback)
    
    board = [' '] * 9
    players = [player1, player2]
    player_symbols = ['X', 'O']
    turn = 0

    log = []

    while True:
        current_player = players[turn % 2]
        x_or_o = player_symbols[turn % 2]
        move = invoke_player(current_player, board, x_or_o, callback=callback)
        board[move] = x_or_o

        log.append({
            'turn': turn + 1,
            'player': x_or_o,
            'move': index_to_algebraic(move),
            'board': board.copy()
        })

        draw_board(board)
        
        if check_win(board, x_or_o):
            post_task_update(callback, f"Player {x_or_o} wins!")
            log.append({'result': f"Player {x_or_o} wins"})
            break
        elif check_draw(board):
            post_task_update(callback, "The game is a draw!")
            log.append({'result': "Draw"})
            break

        turn += 1

    return log
