import re

log_data = """
2024-05-05 00:53:33,793 | ERROR | Card | Card 7008 has unseen rule box!
2024-05-05 00:53:34,048 | ERROR | Card | Card 7009 has unseen rule box!
2024-05-05 00:53:34,315 | ERROR | Card | Card 7013 has unseen rule box!
2024-05-05 00:53:52,051 | ERROR | Card | Card 32295 has unseen rule box!
2024-05-05 00:53:52,320 | ERROR | Card | Card 32318 has unseen rule box!
2024-05-05 00:53:53,186 | ERROR | Card | Card 36704 has unseen rule box!
2024-05-05 00:53:53,478 | ERROR | Card | Card 36903 has unseen rule box!
2024-05-05 00:53:56,219 | ERROR | Card | Card 37194 has unseen rule box!
2024-05-05 00:53:57,050 | ERROR | Card | Card 37371 has unseen rule box!
2024-05-05 00:53:57,320 | ERROR | Card | Card 37396 has unseen rule box!
"""

# Regular expression pattern to match the ID numbers
pattern = r"Card (\d+) has unseen rule box!"

# List to store the extracted numbers
id_numbers = []

# Loop through each line in the log data
for line in log_data.split("\n"):
    # Check if the line contains the specified phrase
    if "unseen rule box!" in line:
        # print(line)
        # Use regular expression to find the ID number and append it to the list
        match = re.search(pattern, line)
        if match:
            # print(match.group(1))
            id_numbers.append(int(match.group(1)))

print(id_numbers)
