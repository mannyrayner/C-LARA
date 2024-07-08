from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json
from .tictactoe_engine import algebraic_to_index, index_to_algebraic

def request_cot_analysis_and_move(board, player, few_shot_examples):

    formatted_request = format_cot_request(board, player, few_shot_examples)
    response = call_chat_gpt4(formatted_request, config_info={gpt_model: 'gpt-4o'})
    
    # Parse the response to extract the CoT analysis and the selected move
    try:
        move_info = interpret_chat_gpt4_response_as_json(response, object_type='dict')
        selected_move = move_info.get('selected_move')
    except ChatGPTError as e:
        print(f"Error parsing GPT-4o response: {e}")
        selected_move = None
    
    return response, selected_move

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
c1, b2, c3

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
