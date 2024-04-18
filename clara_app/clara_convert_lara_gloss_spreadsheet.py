def convert_wanakat_kaori():
    spreadsheet_path = 'C:/cygwin64/home//github/c-lara/tmp/LARA MARS Iaai 2024/token_iaai_french_final.csv'
    output_path = 'C:/cygwin64/home//github/c-lara/tmp/LARA MARS Iaai 2024/wanakat_kaori_glossed.txt'
    convert_glosses_to_clara_format(spreadsheet_path, output_path)

import csv

def convert_glosses_to_clara_format(input_tsv_path, output_txt_path):
    """
    Convert glosses from a TSV format to the C-LARA glossed text format.
    
    Args:
    input_tsv_path (str): The file path for the input TSV file.
    output_txt_path (str): The file path for the output text file.
    """
    
    # Open the input TSV file
    with open(input_tsv_path, mode='r', encoding='utf-8', newline='') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        
         # Initialize an empty list to hold the converted lines
        converted_lines = []

        # Initialize counters and placeholders
        line_counter = 0
        iaai_line = None
        gloss_line = None

        for row in reader:
            # Skip separator lines
            if line_counter % 4 == 0:
                pass
            elif line_counter % 4 == 1:  # Iaai text line
                iaai_line = [ word for word in row if word ]
            elif line_counter % 4 == 2:  # French gloss line
                gloss_line = [ word for word in row if word ]
                # Combine the Iaai text and French glosses
                combined_line = ' '.join([f"@{word}@#gloss#" if ' ' in word else f"{word}#{gloss}#"
                                          for word, gloss in zip(iaai_line, gloss_line)])
                converted_lines.append(f'{combined_line}||')
            # The fourth line (French translation) is ignored for conversion purposes

            line_counter += 1

    # Write the converted lines to the output file
    with open(output_txt_path, 'w', encoding='utf-8') as output_file:
        for line in converted_lines:
            output_file.write(line + '\n')

# Example usage
# Assuming the spreadsheet data is in a CSV format for this example. If it's in another format like Excel,
# additional steps will be needed to extract the data.
# spreadsheet_path = "path/to/iaai_glosses.csv"
# output_path = "path/to/c_lara_formatted_glosses.txt"
# convert_to_c_lara_gloss_format(spreadsheet_path, output_path)
