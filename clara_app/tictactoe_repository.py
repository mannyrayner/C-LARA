from .tictactoe_engine import minimax, get_available_moves, apply_move, get_opponent
from .tictactoe_engine import index_to_algebraic, algebraic_to_index, drawn_board_str
from .clara_utils import absolute_file_name, file_exists, directory_exists

import os
import json
from datetime import datetime

def create_experiment_dir(experiment_name, base_dir='$CLARA/tictactoe_experiments'):
    experiment_dir = get_experiment_dir(experiment_name, base_dir=base_dir)
    os.makedirs(experiment_dir, exist_ok=True)
    metadata = {
        'experiment_name': experiment_name,
        'start_date': datetime.now().isoformat(),
        'cycles': []
    }
    with open(os.path.join(experiment_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=4)
    
def get_experiment_dir(experiment_name, base_dir='$CLARA/tictactoe_experiments'):
    abs_base_dir = absolute_file_name(base_dir)
    if not directory_exists(abs_base_dir):
        raise ValueError(f'Base dir {abs_base_dir} not found')
    experiment_dir = os.path.join(abs_base_dir, experiment_name)
    return experiment_dir

def create_cycle_dir(experiment_name, cycle_number):
    experiment_dir = get_experiment_dir(experiment_name)
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    os.makedirs(cycle_dir, exist_ok=True)
                                        
    experiment_metadata_path = os.path.join(experiment_dir, 'metadata.json')
    with open(experiment_metadata_path, 'r') as f:
        experiment_metadata = json.load(f)
    experiment_metadata['cycles'].append(cycle_number)
    with open(experiment_metadata_path, 'w') as f:
        json.dump(experiment_metadata, f, indent=4)

    cycle_metadata_path = os.path.join(cycle_dir, 'metadata.json')                             
    cycle_metadata = {
        'cycle_number': cycle_number,
        'start_date': datetime.now().isoformat()
    }
    with open(cycle_metadata_path, 'w') as f:
        json.dump(cycle_metadata, f, indent=4)

def get_cycle_dir(experiment_name, cycle_number):
    experiment_dir = get_experiment_dir(experiment_name)
    if not directory_exists(experiment_dir):
        raise ValueError(f'Experiment dir {experiment_dir} not found')
    cycle_dir = os.path.join(experiment_dir, f'cycle_{cycle_number}')
    return cycle_dir

def save_game_log(experiment_name, cycle_number, opponent_player, color, game_log):
    metadata_entry = { 'experiment': experiment_name,
                       'cycle_number': cycle_number,
                       'X': 'cot_player_with_few_shot' if color == 'X' else opponent_player,
                       'O': 'cot_player_with_few_shot' if color == 'O' else opponent_player }
    game_log = [ metadata_entry ] + game_log
        
    annotate_game_log(game_log)
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    log_path = os.path.join(cycle_dir, f'game_log_{opponent_player}_{color}.json')
    
    with open(log_path, 'w') as f:
        json.dump(game_log, f, indent=4)

    human_readable_log = game_log_to_human_readable_str(game_log)
    human_readable_log_path = os.path.join(cycle_dir, f'game_log_{opponent_player}_{color}.txt')
    with open(human_readable_log_path, 'w', encoding='utf-8') as f:
        f.write(human_readable_log)
                                                        
def annotate_game_log(game_log):
    annotated_log = []
    for entry in game_log:
        if 'board' in entry and 'player' in entry:
            board = entry['board']
            player = entry['player']
            evaluation, _ = minimax(board, player, 0)
            relative_evaluation = evaluation if player == 'X' else -evaluation
            legal_moves = [index_to_algebraic(move) for move in get_available_moves(board)]
            if relative_evaluation == -1:
                # In a lost position, there are no "correct" moves
                correct_moves = []
            else:
                correct_moves = [index_to_algebraic(move) for move in get_available_moves(board)
                                 if minimax(apply_move(board, move, player), get_opponent(player), 0)[0] == evaluation]
            entry.update({
                'evaluation': evaluation,
                'player_relative_evaluation': relative_evaluation,
                'legal_moves': legal_moves,
                'correct_moves': correct_moves
            })
        annotated_log.append(entry)
    return annotated_log

def game_log_to_human_readable_str(game_log):
    out_str = ''
    for entry in game_log:
        out_str += '-----------------------------------\n'
        if 'board' in entry:
            out_str += 'Position before move:\n' 
            out_str += drawn_board_str(entry['board'])
            out_str += '\n'
        for key in entry:
            value = entry[key]
            if not key in ( 'board', 'cot_record' ):
                out_str += f'{key}: {value}'
                out_str += '\n\n'
        if 'cot_record' in entry and entry['cot_record']:
            out_str += f"cot_record: {entry['cot_record']}"
            out_str += '\n'
    return out_str

def get_best_few_shot_examples(experiment_name, cycle_number):
    if cycle_number == 0:
        return []
    # Add code to extract cot protocols from previous cycle dir

def select_usable_cot_protocols_from_log(annotated_log):
    usable_protocols = []
    for entry in annotated_log:
        if (entry['cot_record'] is not None and                            # There is a CoT record
            entry['player_relative_evaluation'] >= 0 and                   # Player is not already lost
            len(entry['correct_moves']) < len(entry['legal_moves']) and    # There are both correct and incorrect moves
            entry['move'] in entry['correct_moves']):                      # Player chose a correct move
            best_protocols.append(entry['cot_record'])
    return usable_protocols

