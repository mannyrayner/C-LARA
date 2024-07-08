from .tictactoe_engine import algebraic_to_index, index_to_algebraic

from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json
from .clara_utils import post_task_update
from .clara_classes import ChatGPTError

import traceback

max_number_of_gpt4_tries = 5

def request_cot_analysis_and_move(board, player, few_shot_examples, callback=None):
    formatted_request = format_cot_request(board, player, few_shot_examples)
    gpt_model = 'gpt-4o'
    api_calls = []
    n_attempts = 0
    limit = max_number_of_gpt4_tries
    while True:
        if n_attempts >= limit:
            post_task_update(callback, f'*** Giving up, have tried sending this to GPT-4o {limit} times')
            { 'cot_record': None, 'selected_move': None, 'api_calls': api_calls }
        n_attempts += 1
        post_task_update(callback, f'--- Calling {gpt_model} (attempt #{n_attempts}) to perform CoT analysis')
        try:
            api_call = call_chat_gpt4(formatted_request, config_info={'gpt_model': gpt_model})
            api_calls.append(api_call)
            response_string = api_call.response
            # Parse the response to extract the CoT analysis and the selected move
            move_info = interpret_chat_gpt4_response_as_json(api_call.response, object_type='dict')
            selected_move = move_info.get('selected_move')
            return { 'cot_record': response_string, 'selected_move': selected_move, 'api_calls': api_calls }
        except ChatGPTError as e:
            post_task_update(callback, f"Error parsing GPT-4o response: {e}")
        except Exception as e:
            post_task_update(callback, f'*** Warning: error when sending request to GPT-4o')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
    

cot_template = """
Given the current Tic-Tac-Toe board state, provide a detailed Chain of Thought analysis to determine the best move for the player {player}.
Consider in particular possible winning moves for {player}, possible winning moves that {opponent} may be threatening to make, 
and possible moves that {player} can make which will threaten to win.

Here is the board state, where the squares occupied by X and O, and the unoccupied squares, are given using chess algebraic notation:

{board}

A player wins if they can occupy all three squares on one of the following eight lines:

{possible_lines}

{cot_examples}

Provide your analysis and the best move. At the end, return the selected move in JSON format as follows:
```json
{{
    "selected_move": "<move>"
}}
```
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

def format_cot_request(board, player, few_shot_examples):
    opponent = 'O' if player == 'X' else 'X'
    board_str = format_board_for_cot(board)
    cot_str = format_examples_for_cot(few_shot_examples)
    return cot_template.format(player=player, opponent=opponent, board=board_str, possible_lines=possible_lines, cot_examples=cot_str)

def format_board_for_cot(board):
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

{few_shot_examples[0]}""" + separator
    else:
        
        return f"""Here are examples of CoT analyses:

{separator.join(few_shot_examples)}""" + separator
