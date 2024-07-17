import asyncio
from .tictactoe_repository import create_experiment_dir, create_cycle_dir, save_game_log, correct_game_log_file, generate_cycle_summary
from .tictactoe_game import play_game_async

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
                                            strategy='closest_few_shot_example', starts_from_cycle=starts_from_cycle))

async def run_experiment_cycles_async(experiment_name, num_cycles, strategy='default', starts_from_cycle=0):
    create_experiment_dir(experiment_name, strategy=strategy)
    for cycle_number in range(starts_from_cycle, num_cycles):
        await run_experiment_cycle_async(experiment_name, cycle_number)

async def run_experiment_cycle_async(experiment_name, cycle_number):
    create_cycle_dir(experiment_name, cycle_number)
    tasks = []
    for opponent in ['random_player', 'minimal_gpt4_player', 'cot_player_without_few_shot', 'minimax_player']:
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

# ----------------

def correct_all_game_logs(experiment_name, num_cycles):
    for cycle_number in range(num_cycles):
        for opponent in ['random_player', 'minimal_gpt4_player', 'cot_player_without_few_shot', 'minimax_player']:
            correct_game_log_file(experiment_name, cycle_number, opponent, 'X')
            correct_game_log_file(experiment_name, cycle_number, opponent, 'O')

