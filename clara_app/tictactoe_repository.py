from .tictactoe_evaluate_cot import evaluate_cot_record_async
from .tictactoe_engine import minimax, get_available_moves, apply_move, get_opponent, get_turn_value, get_center_square_value
from .tictactoe_engine import index_to_algebraic, algebraic_to_index, drawn_board_str, check_win, check_draw
from .clara_utils import absolute_file_name, file_exists, directory_exists

import os
import json
from datetime import datetime
import random
from collections import defaultdict
import asyncio

supported_strategies = ( 'n_maximally_different', 'closest_few_shot_example',
                         'closest_few_shot_example_explicit', 'closest_few_shot_example_explicit_with_voting',
                         'closest_few_shot_example_incremental' )

def create_experiment_dir(experiment_name, strategy='n_maximally_different', base_dir='$CLARA/tictactoe_experiments'):
    if not strategy in supported_strategies:
        raise ValueError(f'Unknown strategy {strategy}. Needs to be one of: {supported_strategies}')
    experiment_dir = get_experiment_dir(experiment_name, base_dir=base_dir)
    os.makedirs(experiment_dir, exist_ok=True)
    metadata = {
        'experiment_name': experiment_name,
        'start_date': datetime.now().isoformat(),
        'strategy': strategy,
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

def get_experiment_strategy(experiment_name):
    experiment_dir = get_experiment_dir(experiment_name)
    experiment_metadata_path = os.path.join(experiment_dir, 'metadata.json')
    with open(experiment_metadata_path, 'r') as f:
        experiment_metadata = json.load(f)
    return experiment_metadata['strategy'] if 'strategy' in experiment_metadata else 'n_maximally_different'

def cot_template_name_for_experiment_name(experiment_name):
    strategy = get_experiment_strategy(experiment_name)
    return 'explicit' if strategy in ( 'closest_few_shot_example_explicit', 'closest_few_shot_example_explicit_with_voting' ) else 'minimal'

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

def correct_game_log_file(experiment_name, cycle_number, opponent_player, color):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    log_path = os.path.join(cycle_dir, f'game_log_{opponent_player}_{color}.json')
    
    if not os.path.exists(log_path):
        raise ValueError(f"Log file {log_path} does not exist")
    
    with open(log_path, 'r') as f:
        game_log = json.load(f)

    correct_game_log(game_log)
    
    with open(log_path, 'w') as f:
        json.dump(game_log, f, indent=4)
    
    human_readable_log = game_log_to_human_readable_str(game_log)
    human_readable_log_path = os.path.join(cycle_dir, f'game_log_{opponent_player}_{color}.txt')
    with open(human_readable_log_path, 'w', encoding='utf-8') as f:
        f.write(human_readable_log)

def correct_game_log(game_log):
    # Get the initial metadata entry and game moves
    metadata_entry = game_log[0]
    player1 = metadata_entry['X']
    player2 = metadata_entry['O']
        
    last_move_record = game_log[-2]
    move = algebraic_to_index(last_move_record['move'])
    player = last_move_record['player']
    board = last_move_record['board']
    final_board = board.copy()
    final_board[move] = player

    total_cost = sum([ record['cost'] for record in game_log if 'cost' in record ])
    
    # Check the final state of the game
    if check_win(final_board, 'X'):
        final_record = {'game_over': True, 'score': { player1: 1, player2: 0 }, 'total_cost': total_cost}
    elif check_win(final_board, 'O'):
        final_record = {'game_over': True, 'score': { player1: 0, player2: 1 }, 'total_cost': total_cost}
    elif check_draw(final_board):
        final_record = {'game_over': True, 'score': { player1: 0.5, player2: 0.5 }, 'total_cost': total_cost}
    else:
        raise ValueError(f"Unexpected state at end of game log {log_path}")
    
    # Replace the final record with the corrected one
    game_log[-1] = final_record
                                                        
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

async def get_best_few_shot_examples_async(experiment_name, cycle_number, board, player, N=5):
    strategy = get_experiment_strategy(experiment_name)
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    cache_path = os.path.join(cycle_dir, 'few_shot_examples.json')
    consistent_cot_records = None
    total_evaluation_cost = 0

    if cycle_number == 0:
        # We have nothing to extract few-shot example from
        return [], 0

    if file_exists(cache_path):
        # We have examples cached
        with open(cache_path, 'r') as f:
            selected_entries = json.load(f)
    else:
        previous_cycle_number = cycle_number - 1
        previous_cycle_dir = get_cycle_dir(experiment_name, previous_cycle_number)
        previous_cache_path = os.path.join(previous_cycle_dir, 'few_shot_examples.json')
        log_files = [f for f in os.listdir(previous_cycle_dir) if f.startswith('game_log') and f.endswith('.json')]

        candidates = []
        for log_file in log_files:
            with open(os.path.join(previous_cycle_dir, log_file), 'r') as f:
                game_log = json.load(f)
                candidates.extend(select_usable_cot_protocol_entries_from_log(game_log))

        print(f'Found {len(candidates)} candidate CoT records to use.')

        evaluation_results = await asyncio.gather(*(evaluate_cot_record_async(candidate) for candidate in candidates))
        total_evaluation_cost = sum(result['api_calls'][0].cost for result in evaluation_results)

        consistent_cot_records = [ candidate for candidate in candidates
                                   if not ( 'logically_consistent' in candidate and not candidate['logically_consistent'] ) and
                                   not ( 'correct_threats_and_opportunities' in candidate and not candidate['correct_threats_and_opportunities'] ) ]

        inconsistent_cot_records = [ candidate for candidate in candidates if not candidate in consistent_cot_records ]

        print(f'Evaluated {len(consistent_cot_records)} candidate CoT records as consistent with ground truth from minimax engine.')
        
        if strategy == 'n_maximally_different':
            selected_entries = select_diverse_entries(consistent_cot_records, N)
        elif strategy in ( 'closest_few_shot_example', 'closest_few_shot_example_explicit', 'closest_few_shot_example_explicit_with_voting' ):
            selected_entries = consistent_cot_records
        elif strategy == 'closest_few_shot_example_incremental':
            if file_exists(previous_cache_path):
                with open(previous_cache_path, 'r') as f:
                    previous_entries = json.load(f)
            else:
                previous_entries = []
            selected_entries = previous_entries + consistent_cot_records
        else:
            raise ValueError(f"Unknown strategy {strategy} in get_best_few_shot_examples_async. Must be one of {supported_strategies}")
        cache_few_shot_examples(experiment_name, cycle_number, selected_entries)
        cache_inconsistent_few_shot_examples(experiment_name, cycle_number, inconsistent_cot_records)
    
    if strategy == 'n_maximally_different':
        return selected_entries, total_evaluation_cost
    elif strategy in ( 'closest_few_shot_example', 'closest_few_shot_example_explicit', 'closest_few_shot_example_incremental', 'closest_few_shot_example_explicit_with_voting' ):
        return most_relevant_cot_entries_for_position(selected_entries, board, player), total_evaluation_cost

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
        best_candidate = max(remaining_candidates, key=lambda entry: combined_difference_score_for_diverse(entry, selected))
        selected.append(best_candidate)

    return selected

def most_relevant_cot_entries_for_position(cot_records, board, player):
    if not cot_records:
        return []
    else:
        best_candidate = min(cot_records, key=lambda entry: relevance_score(entry, board, player))
        return [ best_candidate ]

def combined_difference_score_for_diverse(entry, selected):
    return sum(difference_metric_for_diverse(entry, sel) for sel in selected)

def difference_metric_for_diverse(entry1, entry2):
    turn_diff = abs(entry1['turn'] - entry2['turn'])
    player_diff = 0 if entry1['player'] == entry2['player'] else 1
    evaluation_diff = abs(entry1['player_relative_evaluation'] - entry2['player_relative_evaluation'])
    correct_move_proportion_diff = abs(
        (len(entry1['correct_moves']) / len(entry1['legal_moves'])) - 
        (len(entry2['correct_moves']) / len(entry2['legal_moves']))
    )
    return turn_diff + player_diff + evaluation_diff + correct_move_proportion_diff

def relevance_score(entry, board, player):
    player_diff = 0 if entry['player'] == player else 1
    turn_diff = abs(get_turn_value(entry['board']) - get_turn_value(board))
    center_square_value_diff = 0 if get_center_square_value(entry['board']) == get_center_square_value(board) else 1

    return player_diff + turn_diff + center_square_value_diff

def cache_few_shot_examples(experiment_name, cycle_number, entries):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    cache_path = os.path.join(cycle_dir, 'few_shot_examples.json')
    with open(cache_path, 'w') as f:
        json.dump(entries, f, indent=4)

def cache_inconsistent_few_shot_examples(experiment_name, cycle_number, entries):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    cache_path = os.path.join(cycle_dir, 'inconsistent_few_shot_examples.json')
    with open(cache_path, 'w') as f:
        json.dump(entries, f, indent=4)

def generate_cycle_summary(experiment_name, cycle_number):
    cycle_dir = get_cycle_dir(experiment_name, cycle_number)
    log_files = [f for f in os.listdir(cycle_dir) if f.startswith('game_log') and f.endswith('.json')]
    
    summary_scores = defaultdict(lambda: {'X': 0.0, 'O': 0.0, 'total': 0.0})
    total_cycle_cost = 0

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
                total_cycle_cost += game_log[-1]['total_cost']

    summary = {player: score for player, score in summary_scores.items()}
    print(f"Cycle {cycle_number} Summary for {experiment_name}:")
    for player, score in summary.items():
        print(f"{player}: X: {score['X']} | O: {score['O']} | Total: {score['total']}")
    print(f"Total cost for cycle {cycle_number}: ${total_cycle_cost:.2f}")
    
    return summary, total_cycle_cost


