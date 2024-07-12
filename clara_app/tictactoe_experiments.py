from .tictactoe_repository import create_experiment_dir, create_cycle_dir, save_game_log, get_best_few_shot_examples, generate_cycle_summary
from .tictactoe_game import play_game

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
    few_shot_examples = get_best_few_shot_examples('experiment0', 1)

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

# Automate multiple cycles
def run_experiment_cycles(experiment_name, num_cycles):
    create_experiment_dir(experiment_name)
    for cycle_number in range(num_cycles):
        create_cycle_dir(experiment_name, cycle_number)
        few_shot_examples = get_best_few_shot_examples(experiment_name, cycle_number)
        #print(f"Cycle {cycle_number} few-shot examples: {few_shot_examples}")
        for opponent in ['random_player', 'minimal_gpt4_player', 'cot_player_without_few_shot', 'minimax_player']:
            play_game_and_log(experiment_name, cycle_number, opponent, 'X')
            play_game_and_log(experiment_name, cycle_number, opponent, 'O')
        summary = generate_cycle_summary(experiment_name, cycle_number)
        #print(summary)

def generate_cycle_summaries(experiment_name, num_cycles):
    for cycle_number in range(num_cycles):
        generate_cycle_summary(experiment_name, cycle_number)

def play_game_and_log(experiment_name, cycle_number, opponent_player, color):
    if color == 'X':
        game_log = play_game('cot_player_with_few_shot', opponent_player, experiment_name, cycle_number)
    else:
        game_log = play_game(opponent_player, 'cot_player_with_few_shot', experiment_name, cycle_number)
    save_game_log(experiment_name, cycle_number, opponent_player, color, game_log)
