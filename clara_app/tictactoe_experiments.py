
from .tictactoe_repository import create_experiment_dir, get_experiment_dir, create_cycle_dir
from .tictactoe_repository import save_game_log, correct_game_log_file, generate_cycle_summary
from .tictactoe_engine import immediate_threats_and_opportunities
from .tictactoe_game import play_game_async

import asyncio
from collections import defaultdict
import os
import json
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ttest_ind

def create_experiment0():
    create_experiment_dir('experiment0')

def create_experiment0_cycle0():
    create_cycle_dir('experiment0', 0)

def create_experiment0_cycle0_games():
    play_game_and_log('experiment0', 0, 'random_player', 'X')
    play_game_and_log('experiment0', 0, 'random_player', 'O')
    play_game_and_log('experiment0', 0, 'minimal_gpt4_player', 'X')
    play_game_and_log('experiment0', 0, 'minimal_gpt4_player', 'O')
    play_game_and_log('experiment0', 0, 'cot_player_without_few_shot', 'X')
    play_game_and_log('experiment0', 0, 'cot_player_without_few_shot', 'O')
    play_game_and_log('experiment0', 0, 'minimax_player', 'X')
    play_game_and_log('experiment0', 0, 'minimax_player', 'O')

def create_experiment0_cycle1():
    create_cycle_dir('experiment0', 1)

def create_experiment0_cycle1_games():
    play_game_and_log('experiment0', 1, 'random_player', 'X')
    play_game_and_log('experiment0', 1, 'random_player', 'O')
    play_game_and_log('experiment0', 1, 'minimal_gpt4_player', 'X')
    play_game_and_log('experiment0', 1, 'minimal_gpt4_player', 'O')
    play_game_and_log('experiment0', 1, 'cot_player_without_few_shot', 'X')
    play_game_and_log('experiment0', 1, 'cot_player_without_few_shot', 'O')
    play_game_and_log('experiment0', 1, 'minimax_player', 'X')
    play_game_and_log('experiment0', 1, 'minimax_player', 'O')

    generate_cycle_summary('experiment0', 1)

def create_experiment_close():
    create_experiment_dir('experiment_close', strategy='closest_few_shot_example')

def create_experiment_close_cycle0():
    run_experiment_cycle('experiment_close', 0)

def create_experiment_close_cycle1():
    run_experiment_cycle('experiment_close', 1)

def create_experiment_close_cycle0_games():
    play_game_and_log('experiment0', 0, 'random_player', 'X')
    play_game_and_log('experiment0', 0, 'random_player', 'O')
    play_game_and_log('experiment0', 0, 'minimal_gpt4_player', 'X')
    play_game_and_log('experiment0', 0, 'minimal_gpt4_player', 'O')
    play_game_and_log('experiment0', 1, 'cot_player_without_few_shot', 'X')
    play_game_and_log('experiment0', 1, 'cot_player_without_few_shot', 'O')
    play_game_and_log('experiment0', 1, 'minimax_player', 'X')
    play_game_and_log('experiment0', 1, 'minimax_player', 'O')

    generate_cycle_summary('experiment0', 1)

# Test async functionality
def create_experiment_test_async():
    create_experiment_dir('experiment_test_async', strategy='closest_few_shot_example')

async def create_test_async_cycle(cycle_number):
    experiment_name = 'experiment_test_async'
    opponent = 'random_player'
    create_cycle_dir(experiment_name, cycle_number)
    
    tasks = []
    tasks.append(asyncio.create_task(play_game_and_log_async(experiment_name, cycle_number, opponent, 'X')))
    tasks.append(asyncio.create_task(play_game_and_log_async(experiment_name, cycle_number, opponent, 'O')))

    await asyncio.gather(*tasks)
    generate_cycle_summary(experiment_name, cycle_number)

def run_test_async_cycle(cycle_number):
    experiment_name = 'experiment_test_async'
    asyncio.run(create_test_async_cycle(cycle_number))
# End test async functionality

def run_experiment_async(num_cycles, starts_from_cycle=0):
    asyncio.run(run_experiment_cycles_async(f'experiment_async_{num_cycles}', num_cycles,
                                            strategy='closest_few_shot_example',
                                            starts_from_cycle=starts_from_cycle))

def run_experiment_explicit_async(num_cycles, starts_from_cycle=0):
    asyncio.run(run_experiment_cycles_async(f'experiment_async_explicit_{num_cycles}', num_cycles,
                                            strategy='closest_few_shot_example_explicit',
                                            starts_from_cycle=starts_from_cycle))

def run_experiment_explicit_with_voting_async(num_cycles, starts_from_cycle=0):
    asyncio.run(run_experiment_cycles_async(f'experiment_async_explicit_with_voting_{num_cycles}', num_cycles,
                                            strategy='closest_few_shot_example_explicit_with_voting',
                                            starts_from_cycle=starts_from_cycle))

def run_experiment_async_incremental(num_cycles, starts_from_cycle=0):
    asyncio.run(run_experiment_cycles_async(f'experiment_async_incremental_{num_cycles}', num_cycles,
                                            strategy='closest_few_shot_example_incremental', 
                                            starts_from_cycle=starts_from_cycle))

async def run_experiment_cycles_async(experiment_name, num_cycles,
                                      strategy='n_maximally_different',
                                      starts_from_cycle=0):
    create_experiment_dir(experiment_name, strategy=strategy)
    for cycle_number in range(starts_from_cycle, num_cycles):
        await run_experiment_cycle_async(experiment_name, cycle_number)

async def run_experiment_cycle_async(experiment_name, cycle_number):
    create_cycle_dir(experiment_name, cycle_number)
    tasks = []
    for opponent in ['random_player', 'minimal_gpt4_player', 'cot_player_without_few_shot',
                     'cot_player_without_few_shot_explicit', 'minimax_player']:
        tasks.append(asyncio.create_task(play_game_and_log_async(experiment_name, cycle_number, opponent, 'X')))
        tasks.append(asyncio.create_task(play_game_and_log_async(experiment_name, cycle_number, opponent, 'O')))
    await asyncio.gather(*tasks)
    summary = generate_cycle_summary(experiment_name, cycle_number)

async def play_game_and_log_async(experiment_name, cycle_number, opponent_player, color):
    if color == 'X':
        game_log = await play_game_async('cot_player_with_few_shot', opponent_player, experiment_name, cycle_number)
    else:
        game_log = await play_game_async(opponent_player, 'cot_player_with_few_shot', experiment_name, cycle_number)
    save_game_log(experiment_name, cycle_number, opponent_player, color, game_log)

def generate_cycle_summaries(experiment_name, num_cycles):
    for cycle_number in range(num_cycles):
        generate_cycle_summary(experiment_name, cycle_number)

def analyze_experiment_results(experiment_name, num_cycles):
    experiment_dir = get_experiment_dir(experiment_name)
        
    error_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'correct': 0, 'incorrect': 0})))
    summary_scores = defaultdict(lambda: defaultdict(lambda: {'X': 0, 'O': 0, 'total': 0}))
    experiment_cost = 0.0

    for cycle_number in range(num_cycles):
        cycle_dir = os.path.join(experiment_dir, f'cycle_{cycle_number}')
        log_files = [os.path.join(cycle_dir, f) for f in os.listdir(cycle_dir) if f.startswith('game_log') and f.endswith('.json')]
        for log_file in log_files:
            with open(log_file, 'r') as f:
                game_log = json.load(f)
                metadata = game_log[0]
                player_x = metadata['X']
                player_o = metadata['O']

                if 'score' in game_log[-1]:
                    for player, score in game_log[-1]['score'].items():
                        if game_log[0]['X'] == player:
                            summary_scores[cycle_number][player]['X'] += score
                        if game_log[0]['O'] == player:
                            summary_scores[cycle_number][player]['O'] += score
                        summary_scores[cycle_number][player]['total'] += score
                    experiment_cost += game_log[-1]['total_cost']
                
                for entry in game_log[1:]:
                    if 'board' in entry and 'move' in entry and 'player' in entry and 'correct_moves' in entry:
                        board = entry['board']
                        move = entry['move']
                        correct_moves = entry['correct_moves']
                        player = entry['player']
                        current_player = player_x if player == 'X' else player_o
                        threats_and_opportunities = immediate_threats_and_opportunities(board, player)

                        if move in correct_moves:
                            # If one of the conditions below are fulfilled, and we made a generally correct move,
                            # count it as a success even if it wasn't specifically one of the moved given for the condition.
                            # E.g. we could have an own_winning_move but play a threat before taking the win.
                            error_counts[cycle_number][current_player]['overall_correctness']['correct'] += 1
                            if threats_and_opportunities['winning_moves']:
                                error_counts[cycle_number][current_player]['own_winning_move']['correct'] += 1
                            # If there is more than one opponent threat we have a lost position, so there are no correct moves.
                            if len(threats_and_opportunities['opponent_threats']) == 1:
                                error_counts[cycle_number][current_player]['opponent_threat']['correct'] += 1
                            if threats_and_opportunities['double_threat']:
                                error_counts[cycle_number][current_player]['double_threat']['correct'] += 1
                            if threats_and_opportunities['double_threat_follow_up_to_single_threat']:
                                error_counts[cycle_number][current_player]['double_threat_follow_up']['correct'] += 1
                        else:
                            error_counts[cycle_number][current_player]['overall_correctness']['incorrect'] += 1
                            if threats_and_opportunities['winning_moves']:
                                error_counts[cycle_number][current_player]['own_winning_move']['incorrect'] += 1
                            # If there is more than one opponent threat we have a lost position, so there are no correct moves.
                            if len(threats_and_opportunities['opponent_threats']) == 1:
                                error_counts[cycle_number][current_player]['opponent_threat']['incorrect'] += 1
                            if threats_and_opportunities['double_threat']:
                                error_counts[cycle_number][current_player]['double_threat']['incorrect'] += 1
                            if threats_and_opportunities['double_threat_follow_up_to_single_threat']:
                                error_counts[cycle_number][current_player]['double_threat_follow_up']['incorrect'] += 1

    return error_counts, summary_scores, experiment_cost

def plot_cycle_summaries(cycle_summaries, player_name, metric='overall_correctness', window_size=10):
    if not metric in ( 'overall_correctness', 'own_winning_move', 'opponent_threat', 'double_threat', 'double_threat_follow_up'):
        raise ValueError(f'Unknown metric {metric}')
    
    cycles = []
    overall_correct = []
    overall_incorrect = []
    
    for cycle_number, summary in cycle_summaries.items():
        if player_name in summary:
            cycles.append(cycle_number)
            overall_correct.append(summary[player_name][metric]['correct'] if metric in summary[player_name] else 0)
            overall_incorrect.append(summary[player_name][metric]['incorrect'] if metric in summary[player_name] else 0)
        else:
            overall_correct.append(0)
            overall_incorrect.append(0)
    
    total_moves = [c + i for c, i in zip(overall_correct, overall_incorrect)]
    accuracy = [c / t if t > 0 else 0 for c, t in zip(overall_correct, total_moves)]
    
    # Compute moving average
    accuracy_smoothed = np.convolve(accuracy, np.ones(window_size)/window_size, mode='valid')
    cycles_smoothed = cycles[:len(accuracy_smoothed)]
    
    plt.plot(cycles_smoothed, accuracy_smoothed, label=f"{metric} accuracy (smoothed)")
    plt.xlabel('Cycle Number')
    plt.ylabel('Accuracy')
    plt.title(f'Accuracy for {metric} over cycles (smoothed)')
    plt.legend()
    plt.show()

def compare_performance(cycle_summaries, player_name, start1, end1, start2, end2, metric='overall_correctness'):
    if not metric in ( 'overall_correctness', 'own_winning_move', 'opponent_threat', 'double_threat', 'double_threat_follow_up'):
        raise ValueError(f'Unknown metric {metric}')
    
    scores1 = [summary[player_name][metric]['correct'] / (summary[player_name][metric]['correct'] + summary[player_name][metric]['incorrect'])
               for cycle_number, summary in cycle_summaries.items() if start1 <= cycle_number <= end1]
    scores2 = [summary[player_name][metric]['correct'] / (summary[player_name][metric]['correct'] + summary[player_name][metric]['incorrect'])
               for cycle_number, summary in cycle_summaries.items() if start2 <= cycle_number <= end2]
    
    t_stat, p_value = ttest_ind(scores1, scores2)
    return t_stat, p_value

def plot_cycle_summaries_for_scores(summary_scores, player_name, window_size=10):
    cycles = []
    overall_correct = []
    overall_incorrect = []
    
    for cycle_number, summary in summary_scores.items():
        if player_name in summary:
            cycles.append(cycle_number)
            overall_correct.append(summary[player_name]['total'])
        else:
            overall_correct.append(0)
    
    total_scores = overall_correct
    accuracy = [score for score in total_scores]
    
    # Compute moving average
    accuracy_smoothed = np.convolve(accuracy, np.ones(window_size)/window_size, mode='valid')
    cycles_smoothed = cycles[:len(accuracy_smoothed)]
    
    plt.plot(cycles_smoothed, accuracy_smoothed, label=f"{player_name} Cycle Score (Smoothed)")
    plt.xlabel('Cycle Number')
    plt.ylabel('Total Score')
    plt.title(f'Total Score for {player_name} Over Cycles (Smoothed)')
    plt.legend()
    plt.show()

def compare_performance_for_scores(summary_scores, player_name, start1, end1, start2, end2):
    scores1 = [summary[player_name]['total']
               for cycle_number, summary in summary_scores.items() if start1 <= cycle_number <= end1]
    scores2 = [summary[player_name]['total']
               for cycle_number, summary in summary_scores.items() if start2 <= cycle_number <= end2]
    
    t_stat, p_value = ttest_ind(scores1, scores2)
    return t_stat, p_value


# ----------------

def correct_all_game_logs(experiment_name, num_cycles):
    for cycle_number in range(num_cycles):
        for opponent in ['random_player', 'minimal_gpt4_player', 'cot_player_without_few_shot',
                         'cot_player_without_few_shot_explicit', 'minimax_player']:
            correct_game_log_file(experiment_name, cycle_number, opponent, 'X')
            correct_game_log_file(experiment_name, cycle_number, opponent, 'O')

