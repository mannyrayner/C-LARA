from .tictactoe_engine import get_opponent, algebraic_to_index, index_to_algebraic, drawn_board_str, immediate_threats_and_opportunities
from .tictactoe_gpt4 import call_gpt4_with_retry_for_cot_evaluation_async, format_board_for_gpt4

cot_evaluation_template = """I am going to give you a position in a Tic-Tac-Toe game, a reliable ground-truth evaluation of the position,
and a second analysis. Your task is to determine whether the second analysis is consistent with the ground-truth evaluation.

Here is the board state with {player} to move, where the squares occupied by X and O, and the unoccupied squares, are given using chess algebraic notation:

{algebraic_board}

Here is a formatted image of the board.

{formatted_board}

Here is the reliable ground-truth evaluation of the position:

{position_summary}

Here is the second analysis:

{cot_record}

Here are the criteria to use when evaluating the second analysis:

1. Is the second analysis logically consistent with the ground truth evaluation?
2. Does the second analysis correctly identify the threats and opportunities?

Provide your evaluation in JSON format as follows:
```json
{{
    "logically_consistent": <true/false>,
    "correct_threats_and_opportunities": <true/false>,
    "comments": "<detailed comments>"
}}
```
Only provide the JSON, since the reply will be read by a Python script.
"""

async def evaluate_cot_record_async(record):
    try:
        board = record['board']
        player = record['player']
        cot_record = record['cot_record']
        algebraic_board = format_board_for_gpt4(board)
        formatted_board = drawn_board_str(board)
        threats_and_opportunities = immediate_threats_and_opportunities(board, player)
        position_summary = threats_and_opportunities_to_english(threats_and_opportunities, player)
        formatted_request = cot_evaluation_template.format(player=player, algebraic_board=algebraic_board, formatted_board=formatted_board,
                                                           position_summary=position_summary, cot_record=cot_record)
        evaluation = await call_gpt4_with_retry_for_cot_evaluation_async(formatted_request)
        record.update(evaluation['evaluation'])
    except Exception as e:
        #raise e
        record.update({
            'logically_consistent': False,
            'correct_threats_and_opportunities': False,
            'comments': f'Exception in call_gpt4_with_retry_for_cot_evaluation_async: {str(e)}'
        })
    return evaluation
        
def threats_and_opportunities_to_english(threats_and_opportunities, player):
    opponent = get_opponent(player)
    descriptions = []
    if threats_and_opportunities['winning_moves']:
        descriptions.append(f"Winning move for {player}: {' or '.join(threats_and_opportunities['winning_moves'])}")
    else:
        descriptions.append(f"{player} does not have an immediately winning move")
        
    if threats_and_opportunities['opponent_threats']:
        descriptions.append(f"{opponent} is threatening an immediate win with {' or '.join(threats_and_opportunities['opponent_threats'])}")
    else:
        descriptions.append(f"{opponent} does not have any threat to make a line on the next move")
        
    if threats_and_opportunities['double_threat']:
        descriptions.append(f"{player} can threaten to make two lines with {' or '.join(threats_and_opportunities['double_threat'])}")
    else:
        descriptions.append(f"{player} has no way to make an immediate double threat")
        
    if threats_and_opportunities['single_threat']:
        descriptions.append(f"{player} can threaten to make a line with {' or '.join(threats_and_opportunities['single_threat'])}")
    else:
        descriptions.append(f"{player} has no way to make an immediate threat")
        
    if threats_and_opportunities['double_threat_follow_up_to_single_threat']:
        descriptions.append(f"""If {player} plays {threats_and_opportunities['double_threat_follow_up_to_single_threat']},
after the forced reply they can make a winning double threat""")
        
    return "\n".join(descriptions)
