
from .tictactoe_engine import minimax, get_board_from_positions, draw_board, get_available_moves, check_win, check_draw
from .tictactoe_engine import index_to_algebraic, algebraic_to_index
from .tictactoe_gpt4 import request_minimal_gpt4_move_async, request_cot_analysis_and_move_async, request_cot_analysis_and_move_with_voting_async
from .tictactoe_repository import get_best_few_shot_examples_async, cot_template_name_for_experiment_name, get_experiment_strategy

from .clara_utils import post_task_update

import random
import json
import traceback

known_players = ( 'random_player', 'human_player', 'minimax_player', 'minimal_gpt4_player',
                  'cot_player_without_few_shot', 'cot_player_without_few_shot_explicit',
                  'cot_player_with_few_shot' )

def random_player(board, player, callback=None):
    moves = get_available_moves(board)
    return random.choice(moves), None, None, 0

def human_player(board, player, callback=None):
    draw_board(board)
    move = input(f"Player {player}, enter your move (e.g., a1, b2): ")
    return algebraic_to_index(move), None, None, 0

def minimax_player(board, player, callback=None):
    _, best_move = minimax(board, player, 0)
    return best_move, None, None, 0

async def minimal_gpt4_player_async(board, player):
    response = await request_minimal_gpt4_move_async(board, player)
    total_cost = sum(call.cost for call in response['api_calls'])
    return algebraic_to_index(response['selected_move']), None, response['prompt'], total_cost

async def cot_player_without_few_shot_async(board, player):
    few_shot_examples = []
    cot_template_name = 'minimal'
    response = await request_cot_analysis_and_move_async(board, player, cot_template_name, few_shot_examples)
    total_cost = sum(call.cost for call in response['api_calls'])
    return algebraic_to_index(response['selected_move']), response['cot_record'], response['prompt'], total_cost

async def cot_player_without_few_shot_explicit_async(board, player):
    few_shot_examples = []
    cot_template_name = 'explicit'
    response = await request_cot_analysis_and_move_async(board, player, cot_template_name, few_shot_examples)
    total_cost = sum(call.cost for call in response['api_calls'])
    return algebraic_to_index(response['selected_move']), response['cot_record'], response['prompt'], total_cost

async def cot_player_with_few_shot_async(board, player, experiment_name, cycle_number):
    few_shot_examples, evaluation_cost = await get_best_few_shot_examples_async(experiment_name, cycle_number, board, player)
    cot_template_name = cot_template_name_for_experiment_name(experiment_name)
    strategy = get_experiment_strategy(experiment_name)
    if strategy == 'closest_few_shot_example_explicit_with_voting':
        response = await request_cot_analysis_and_move_with_voting_async(board, player, cot_template_name, few_shot_examples)
    else:
        response = await request_cot_analysis_and_move_async(board, player, cot_template_name, few_shot_examples)
    total_cost = sum(call.cost for call in response['api_calls']) + evaluation_cost
    return algebraic_to_index(response['selected_move']), response['cot_record'], response['prompt'], total_cost

async def invoke_player_async(player_name, board, x_or_o, experiment_name, cycle_number):
    complain_if_unknown_player(player_name)
    complain_if_unknown_x_or_o(x_or_o)
    
    try:
        if player_name == 'random_player':
            return random_player(board, x_or_o)
        elif player_name == 'human_player':
            return human_player(board, x_or_o)
        elif player_name == 'minimax_player':
            return minimax_player(board, x_or_o)
        elif player_name == 'minimal_gpt4_player':
            return await minimal_gpt4_player_async(board, x_or_o)
        elif player_name == 'cot_player_without_few_shot':
            return await cot_player_without_few_shot_async(board, x_or_o)
        elif player_name == 'cot_player_without_few_shot_explicit':
            return await cot_player_without_few_shot_explicit_async(board, x_or_o)
        elif player_name == 'cot_player_with_few_shot':
            return await cot_player_with_few_shot_async(board, x_or_o, experiment_name, cycle_number)
    except Exception as e:
        # Fall back to random player if there's an exception
        #raise e
        return random_player(board, x_or_o)

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

async def play_game_async(player1, player2, experiment_name, cycle_number):
    complain_if_unknown_player(player1)
    complain_if_unknown_player(player2)
    
    board = [' '] * 9
    players = [player1, player2]
    player_symbols = ['X', 'O']
    turn = 0

    log = []
    total_cost = 0

    while True:
        current_player = players[turn % 2]
        x_or_o = player_symbols[turn % 2]
        board_before_move = board.copy()
        move, cot_record, prompt, cost = await invoke_player_async(current_player, board, x_or_o, experiment_name, cycle_number)
        total_cost += cost

        log.append({
            'turn': turn + 1,
            'player': x_or_o,
            'board': board_before_move,
            'prompt': prompt,
            'move': index_to_algebraic(move),
            'cot_record': cot_record,
            'cost': cost
        })

        board[move] = x_or_o
        draw_board(board)
        
        if check_win(board, 'X'):
            log.append({'game_over': True,
                        'score': { player1: 1, player2: 0 },
                        'total_cost': total_cost})
            break
        elif check_win(board, 'O'):
            log.append({'game_over': True,
                        'score': { player1: 0, player2: 1 },
                        'total_cost': total_cost})
            break
        elif check_draw(board):
            log.append({'game_over': True,
                        'score': { player1: 0.5, player2: 0.5 },
                        'total_cost': total_cost})
            break

        turn += 1

    return log
