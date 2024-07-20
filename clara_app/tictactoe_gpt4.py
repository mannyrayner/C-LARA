from .tictactoe_engine import get_opponent, algebraic_to_index, index_to_algebraic, get_available_moves
from .clara_chatgpt4 import get_api_chatgpt4_response, interpret_chat_gpt4_response_as_json
from .clara_utils import post_task_update, post_task_update_async
from .clara_classes import ChatGPTError

import asyncio
from collections import defaultdict
import traceback

max_number_of_gpt4_tries = 5

async def request_minimal_gpt4_move_async(board, player, callback=None):
    formatted_request = format_minimal_gpt4_request(board, player)
    available_moves = [index_to_algebraic(move) for move in get_available_moves(board)]
    return await call_gpt4_with_retry_async(formatted_request, available_moves, callback=callback)

async def request_cot_analysis_and_move_async(board, player, cot_template_name, few_shot_examples, callback=None):
    formatted_request = format_cot_request(board, player, cot_template_name, few_shot_examples)
    available_moves = [index_to_algebraic(move) for move in get_available_moves(board)]
    return await call_gpt4_with_retry_async(formatted_request, available_moves, callback=callback)

async def request_cot_analysis_and_move_with_voting_async(board, player, cot_template_name, few_shot_examples, callback=None):
    formatted_request = format_cot_request(board, player, cot_template_name, few_shot_examples)
    available_moves = [index_to_algebraic(move) for move in get_available_moves(board)]

    move_counts = defaultdict(int)
    cot_records = {}
    api_calls = []

    # Run the first two invocations in parallel
    tasks = [asyncio.create_task(call_gpt4_with_retry_async(formatted_request, available_moves, callback=callback)) for _ in range(2)]
    results = await asyncio.gather(*tasks)

    for response in results:
        move = response['selected_move']
        move_counts[move] += 1
        cot_records[move] = response['cot_record']
        api_calls.extend(response['api_calls'])

        if move_counts[move] == 2:
            return {'selected_move': move, 'cot_record': cot_records[move], 'prompt': formatted_request, 'api_calls': api_calls}

    # Continue submitting requests until we get two responses selecting the same move
    while True:
        response = await call_gpt4_with_retry_async(formatted_request, available_moves, callback=callback)
        move = response['selected_move']
        move_counts[move] += 1
        cot_records[move] = response['cot_record']
        api_calls.extend(response['api_calls'])

        if move_counts[move] == 2:
            return {'selected_move': move, 'cot_record': cot_records[move], 'prompt': formatted_request, 'api_calls': api_calls}

async def call_gpt4_with_retry_async(formatted_request, available_moves, gpt_model='gpt-4o', callback=None):
    api_calls = []
    n_attempts = 0
    limit = max_number_of_gpt4_tries
    while True:
        if n_attempts >= limit:
            await post_task_update_async(callback, f'*** Giving up, have tried sending this to GPT-4o {limit} times')
            return {'cot_record': None, 'prompt': formatted_request, 'selected_move': None, 'api_calls': api_calls}
        n_attempts += 1
        await post_task_update_async(callback, f'--- Calling {gpt_model} (attempt #{n_attempts})')
        try:
            api_call = await get_api_chatgpt4_response(formatted_request, config_info={'gpt_model': gpt_model}, callback=callback)
            api_calls.append(api_call)
            response_string = api_call.response
            move_info = interpret_chat_gpt4_response_as_json(api_call.response, object_type='dict')
            selected_move = move_info.get('selected_move')
            if not selected_move in available_moves:
                raise ValueError(f'Illegal move: {selected_move}')
            return {'cot_record': response_string, 'prompt': formatted_request, 'selected_move': selected_move, 'api_calls': api_calls}
        except ChatGPTError as e:
            await post_task_update_async(callback, f"Error parsing GPT-4o response: {e}")
        except Exception as e:
            await post_task_update_async(callback, f'*** Warning: error when sending request to GPT-4o')
            await post_task_update_async(callback, f'"{str(e)}"\n{traceback.format_exc()}')

async def call_gpt4_with_retry_for_cot_evaluation_async(formatted_request, gpt_model='gpt-4o', callback=None):
    api_calls = []
    n_attempts = 0
    limit = max_number_of_gpt4_tries
    while True:
        if n_attempts >= limit:
            await post_task_update_async(callback, f'*** Giving up, have tried sending this to GPT-4o {limit} times')
            return {'evaluation': None, 'api_calls': api_calls}
        n_attempts += 1
        await post_task_update_async(callback, f'--- Calling {gpt_model} (attempt #{n_attempts})')
        try:
            api_call = await get_api_chatgpt4_response(formatted_request, config_info={'gpt_model': gpt_model}, callback=callback)
            api_calls.append(api_call)
            response_string = api_call.response
            evaluation = interpret_chat_gpt4_response_as_json(api_call.response, object_type='dict')
            if not 'logically_consistent' in evaluation or not 'correct_threats_and_opportunities' in evaluation:
                raise ValueError(f'Evaluation not in requested format: {evaluation}')
            return {'evaluation': evaluation, 'api_calls': api_calls}
        except ChatGPTError as e:
            await post_task_update_async(callback, f"Error parsing GPT-4o response: {e}")
        except Exception as e:
            await post_task_update_async(callback, f'*** Warning: error when sending request to GPT-4o')
            await post_task_update_async(callback, f'"{str(e)}"\n{traceback.format_exc()}')

minimal_template = """
Given the current Tic-Tac-Toe board state, find the best move for the player {player}.

Here is the board state, where the squares occupied by X and O, and the unoccupied squares, are given using chess algebraic notation:

{board}

A player wins if they can occupy all three squares on one of the following eight lines:

{possible_lines}

Return the selected move in JSON format as follows, where <move> is given in chess algebraic notation:
```json
{{
    "selected_move": "<move>"
}}
```
"""

cot_template = """
Given the current Tic-Tac-Toe board state, provide a detailed Chain of Thought analysis to determine the best move for the player {player}.
Consider in particular possible winning moves for {player}, possible winning moves that {opponent} may be threatening to make, 
and possible moves that {player} can make which will threaten to win.

Here is the board state, where the squares occupied by X and O, and the unoccupied squares, are given using chess algebraic notation:

{board}

A player wins if they can occupy all three squares on one of the following eight lines:

{possible_lines}

Provide your analysis and the best move. At the end, return the selected move in JSON format as follows:
```json
{{
    "selected_move": "<move>"
}}
```

{cot_examples}
"""

cot_template_explicit = """
Given the current Tic-Tac-Toe board state, provide a detailed Chain of Thought analysis to determine the best move for the player {player}.

Here is the board state, where the squares occupied by X and O, and the unoccupied squares, are given using chess algebraic notation:

{board}

A player wins if they can occupy all three squares on one of the following eight lines:

{possible_lines}

Reason as follows:
1. If {player} can play on an empty square and make a line of three {player}s, play on that square and win now.

2. Otherwise, if {opponent} could play on an empty square and make a line of three {opponent}s, play on that square to stop them winning next move.

3. Otherwise, if {player} can play on an empty square and create a position where they have more than one immediate threat,
   i.e. more than one line containing two {player}s and an empty square, play the move which creates the multiple threats and win.

4. Otherwise, if {player} can play on an empty square and make an immediate threat,
   consider whether there is a strong followup after {opponent}'s forced reply.

Provide your analysis and the best move. At the end, return the selected move in JSON format as follows:
```json
{{
    "selected_move": "<move>"
}}
```

{cot_examples}
"""

possible_lines = """Vertical:
a1, a2, a3
b1, b2, b3
c1, c2, c3

Horizontal:
a1, b1, c1
a2, b2, c2
a3, b3, c3

Diagonal:
a1, b2, c3
a3, b2, c1"""

def format_minimal_gpt4_request(board, player):
    board_str = format_board_for_gpt4(board)
    return minimal_template.format(player=player, board=board_str, possible_lines=possible_lines)

def format_cot_request(board, player, cot_template_name, few_shot_examples):
    opponent = get_opponent(player)
    board_str = format_board_for_gpt4(board)
    cot_str = format_examples_for_cot(few_shot_examples)
    template = cot_template_explicit if cot_template_name == 'explicit' else cot_template
    return template.format(player=player, opponent=opponent, board=board_str, possible_lines=possible_lines, cot_examples=cot_str)

def format_board_for_gpt4(board):
    x_line_content = ', '.join([index_to_algebraic(i) for i, s in enumerate(board) if s == "X"])
    o_line_content = ', '.join([index_to_algebraic(i) for i, s in enumerate(board) if s == "O"])
    unoccupied_line_content = ', '.join([index_to_algebraic(i) for i, s in enumerate(board) if s == " "])
    return f"""Squares occupied by X: {x_line_content}
Squares occupied by O: {o_line_content}
Unoccupied squares: {unoccupied_line_content}"""

def format_examples_for_cot(few_shot_examples):
    separator = "\n-------------"
    if len(few_shot_examples) == 0:
        return ''
    elif len(few_shot_examples) == 1:
        return f"""Here is an example of a CoT analysis:

{format_cot_example(few_shot_examples[0])}""" + separator
    else:
        
        return f"""Here are examples of CoT analyses:

{separator.join([format_cot_example(example) for example in few_shot_examples])}""" + separator

def format_cot_example(example):
    board = example['board']
    player = example['player']
    cot_record = example['cot_record']

    return f"""Example with {player} to play:

{format_board_for_gpt4(board)}

Output:

{cot_record}"""

