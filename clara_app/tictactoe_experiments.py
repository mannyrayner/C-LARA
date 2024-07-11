from .tictactoe_repository import create_experiment_dir, create_cycle_dir, save_game_log, get_best_few_shot_examples
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
    print(few_shot_examples)  # for debugging

def play_game_and_log(experiment_name, cycle_number, opponent_player, color):
    game_log = play_game('cot_player_with_few_shot', opponent_player, experiment_name, cycle_number)
    save_game_log(experiment_name, cycle_number, opponent_player, color, game_log)
