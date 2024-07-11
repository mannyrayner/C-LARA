from .tictactoe_engine import minimax, get_available_moves, apply_move, get_opponent
from .tictactoe_engine import index_to_algebraic, algebraic_to_index, drawn_board_str
from .clara_utils import absolute_file_name, file_exists, directory_exists

import os
import json
from datetime import datetime
import random
from collections import defaultdict

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

def get_best_few_shot_examples(experiment_name, cycle_number, N=5):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    cache_path = os.path.join(cycle_dir, 'few_shot_examples.json')
    
    if file_exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)

    if cycle_number == 0:
        return []

    previous_cycle_number = cycle_number - 1
    previous_cycle_dir = get_cycle_dir(experiment_name, previous_cycle_number)
    log_files = [f for f in os.listdir(previous_cycle_dir) if f.startswith('game_log') and f.endswith('.json')]

    candidates = []
    for log_file in log_files:
        with open(os.path.join(previous_cycle_dir, log_file), 'r') as f:
            game_log = json.load(f)
            candidates.extend(select_usable_cot_protocol_entries_from_log(game_log))

    print(f'Found {len(candidates)} candidate CoT records to use. Selecting a diverse set')

    selected_entries = select_diverse_entries(candidates, N)
    cache_few_shot_examples(experiment_name, cycle_number, selected_entries)
    
    return selected_entries

def select_usable_cot_protocol_entries_from_log(annotated_log):
    usable_entries = []
    for entry in annotated_log:
        if ('cot_record' in entry and 
            entry['cot_record'] is not None and                            # There is a CoT record
            entry['player_relative_evaluation'] >= 0 and                   # Player is not already lost
            len(entry['correct_moves']) < len(entry['legal_moves']) and    # There are both correct and incorrect moves
            entry['move'] in entry['correct_moves']):                      # Player chose a correct move
            usable_entries.append(entry)
    return usable_entries

def select_diverse_entries(candidates, N):
    if not candidates:
        return []

    selected = [random.choice(candidates)]
    while len(selected) < N:
        remaining_candidates = [entry for entry in candidates if entry not in selected]
        if not remaining_candidates:
            break
        best_candidate = max(remaining_candidates, key=lambda entry: combined_difference_score(entry, selected))
        selected.append(best_candidate)

    return selected

def combined_difference_score(entry, selected):
    return sum(difference_metric(entry, sel) for sel in selected)

def difference_metric(entry1, entry2):
    turn_diff = abs(entry1['turn'] - entry2['turn'])
    player_diff = 0 if entry1['player'] == entry2['player'] else 1
    evaluation_diff = abs(entry1['player_relative_evaluation'] - entry2['player_relative_evaluation'])
    correct_move_proportion_diff = abs(
        (len(entry1['correct_moves']) / len(entry1['legal_moves'])) - 
        (len(entry2['correct_moves']) / len(entry2['legal_moves']))
    )
    return turn_diff + player_diff + evaluation_diff + correct_move_proportion_diff

def cache_few_shot_examples(experiment_name, cycle_number, entries):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    cache_path = os.path.join(cycle_dir, 'few_shot_examples.json')
    with open(cache_path, 'w') as f:
        json.dump(entries, f, indent=4)

##def generate_cycle_summary(experiment_name, cycle_number):
##    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
##    log_files = [f for f in os.listdir(cycle_dir) if f.startswith('game_log') and f.endswith('.json')]
##    
##    summary_scores = defaultdict(float)
##    
##    for log_file in log_files:
##        with open(os.path.join(cycle_dir, log_file), 'r') as f:
##            game_log = json.load(f)
##            if 'score' in game_log[-1]:
##                for player, score in game_log[-1]['score'].items():
##                    summary_scores[player] += score
##    
##    summary = {player: score for player, score in summary_scores.items()}
##    print(f"Cycle {cycle_number} Summary for {experiment_name}:")
##    for player, score in summary.items():
##        print(f"{player}: {score}")
##    
##    return summary

def generate_cycle_summary(experiment_name, cycle_number):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    log_files = [f for f in os.listdir(cycle_dir) if f.startswith('game_log') and f.endswith('.json')]
    
    summary_scores = defaultdict(lambda: {'X': 0.0, 'O': 0.0, 'total': 0.0})
    
    for log_file in log_files:
        with open(os.path.join(cycle_dir, log_file), 'r') as f:
            game_log = json.load(f)
            if 'score' in game_log[-1]:
                for player, score in game_log[-1]['score'].items():
                    if game_log[0]['X'] == player:
                        summary_scores[player]['X'] += score
                    if game_log[0]['O'] == player:
                        summary_scores[player]['O'] += score
                    summary_scores[player]['total'] += score
    
    summary = {player: score for player, score in summary_scores.items()}
    print(f"Cycle {cycle_number} Summary for {experiment_name}:")
    for player, score in summary.items():
        print(f"{player}: X: {score['X']} | O: {score['O']} | Total: {score['total']}")
    
    return summary

