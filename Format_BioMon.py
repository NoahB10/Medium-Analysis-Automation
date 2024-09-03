import pandas as pd
import os

# Define file paths
example_format_path = r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Equipment\JOBST\example_format.txt'
buffer_sol_path = r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Equipment\JOBST\Buffer_Sol.txt'
output_file_path = r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Equipment\JOBST\Formatted_Buffer_Sol.txt'

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

# Read the example format template
with open(example_format_path, 'r') as file:
    template_lines = file.readlines()

# Read the Buffer_Sol data, handling possible encoding issues
try:
    buffer_df = pd.read_csv(buffer_sol_path, sep='\t', header=None, encoding='ISO-8859-1', skiprows=1)
except UnicodeDecodeError:
    buffer_df = pd.read_csv(buffer_sol_path, sep='\t', header=None, encoding='cp1252', skiprows=1)

# Example: The expected number of columns in the output is 83 (based on your description)
expected_columns = 83

# Ensure Buffer_Sol data has the correct number of columns
if buffer_df.shape[1] < expected_columns:
    # Add missing columns with zero or appropriate placeholder values
    for i in range(buffer_df.shape[1], expected_columns):
        buffer_df[i] = 0  # Filling missing columns with zeros
elif buffer_df.shape[1] > expected_columns:
    buffer_df = buffer_df.iloc[:, :expected_columns]  # Trim excess columns if needed

# Convert Buffer_Sol data to a list of strings formatted for the output
output_lines = template_lines[:3]  # Assuming the first three lines are metadata and headers

for index, row in enumerate(buffer_df.itertuples(index=False, name=None), start=1):  # Start numbering from 1
    # Format each element properly, depending on whether it's a float or not
    formatted_row = [f"{x:.4f}" if isinstance(x, (int, float)) else str(x) for x in row]
    # Prepend the sample number (index) before the time column
    formatted_line = f"{index}\t" + "\t".join(formatted_row) + "\n"
    output_lines.append(formatted_line)

# Write the combined data to a new file
with open(output_file_path, 'w') as file:
    file.writelines(output_lines)

print(f"The file has been formatted and saved as {output_file_path}.")