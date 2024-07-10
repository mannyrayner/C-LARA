from .tictactoe_repository import create_experiment_dir, create_cycle_dir, save_game_log
from .tictactoe_game import play_game

def create_experiment0():
    create_experiment_dir('experiment0')

def create_experiment0_cycle0():
    create_cycle_dir('experiment0', 0)

def create_experiment0_cycle0_games():
    play_game_and_log('experiment0', 0, 'random_player', 'X')

def play_game_and_log(experiment_name, cycle_number, opponent_player, color):
    game_log = play_game('cot_player_with_few_shot', opponent_player, experiment_name, cycle_number)
    save_game_log(experiment_name, cycle_number, opponent_player, color, game_log)
