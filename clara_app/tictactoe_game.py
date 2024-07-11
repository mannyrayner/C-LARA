
from .tictactoe_engine import minimax, get_board_from_positions, draw_board, get_available_moves, check_win, check_draw
from .tictactoe_engine import index_to_algebraic, algebraic_to_index
from .tictactoe_gpt4 import request_minimal_gpt4_move, request_cot_analysis_and_move
from .tictactoe_repository import get_best_few_shot_examples

from .clara_utils import post_task_update

import random
import json
import traceback

known_players = ( 'random_player', 'human_player', 'minimax_player', 'minimal_gpt4_player',
                  'cot_player_without_few_shot', 'cot_player_with_few_shot' )

def random_player(board, player, callback=None):
    moves = get_available_moves(board)
    return random.choice(moves), None

def human_player(board, player, callback=None):
    draw_board(board)
    move = input(f"Player {player}, enter your move (e.g., a1, b2): ")
    return algebraic_to_index(move), None

def minimax_player(board, player, callback=None):
    _, best_move = minimax(board, player, 0)
    return best_move, None

def minimal_gpt4_player(board, player, callback=None):
    response = request_minimal_gpt4_move(board, player, callback=callback)
    return algebraic_to_index(response['selected_move']), None

def cot_player_without_few_shot(board, player, callback=None):
    few_shot_examples = []
    response = request_cot_analysis_and_move(board, player, few_shot_examples, callback=callback)
    return algebraic_to_index(response['selected_move']), response['cot_record']

def cot_player_with_few_shot(board, player, experiment_name, cycle_number, callback=None):
    few_shot_examples = get_best_few_shot_examples(experiment_name, cycle_number)
    response = request_cot_analysis_and_move(board, player, few_shot_examples, callback=callback)
    return algebraic_to_index(response['selected_move']), response['cot_record']

def invoke_player(player_name, board, x_or_o, experiment_name, cycle_number, callback=None):
    complain_if_unknown_player(player_name, callback=callback)
    complain_if_unknown_x_or_o(x_or_o, callback=callback)
    
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
    elif player_name == 'cot_player_with_few_shot':
        return cot_player_with_few_shot(board, x_or_o, experiment_name, cycle_number, callback=callback)

def complain_if_unknown_player(player_name, callback=None):
    if not player_name in known_players:
        error_message = f'Unknown player name: {player_name}'
        post_task_update(callback, error_message)
        raise ValueError(error_message)

def complain_if_unknown_x_or_o(x_or_o, callback=None):
    if not x_or_o in ( 'X', 'O' ):
        error_message = f'Unknown side, must be X or O: {x_or_o}'
        post_task_update(callback, error_message)
        raise ValueError(error_message)

def play_game(player1, player2, experiment_name, cycle_number, callback=None):
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
        board_before_move = board.copy()
        move, cot_record = invoke_player(current_player, board, x_or_o, experiment_name, cycle_number, callback=callback)

        log.append({
            'turn': turn + 1,
            'player': x_or_o,
            'move': index_to_algebraic(move),
            'cot_record': cot_record,
            'board': board_before_move
        })

        board[move] = x_or_o
        draw_board(board)
        
        if check_win(board, x_or_o):
            post_task_update(callback, f"Player {x_or_o} wins!")
            if x_or_o == 'X':
                log.append({'game_over': True,
                            'score': { player1: 1, player2: 0 }})
            else:
                log.append({'game_over': True,
                            'score': { player1: 0, player2: 1 }})
            break
        elif check_draw(board):
            post_task_update(callback, "The game is a draw!")
            log.append({'game_over': True,
                        'score': { player1: 0.5, player2: 0.5 }})
            break

        turn += 1

    return log
