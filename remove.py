import os
import json


def remove_empty_prefix_from_file(file_path):
    try:
        # Read the JSON file
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # If data is a list of dictionaries
        if isinstance(data, list):
            modified_data = [item for item in data if item.get("prefix", None) != ""]
        # If data is a single dictionary
        elif isinstance(data, dict):
            modified_data = {k: v for k, v in data.items() if v != "" or k != "prefix"}
        else:
            print(f"Unsupported JSON structure in file: {file_path}")
            return

        # Write the modified content back to the JSON file
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(modified_data, file, indent=4)

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")


def process_all_json_files_in_directory(directory):
    for subdir, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(subdir, file)
                remove_empty_prefix_from_file(file_path)


if __name__ == "__main__":
    data_directory = "data/"  # Path to your data directory
    process_all_json_files_in_directory(data_directory)
