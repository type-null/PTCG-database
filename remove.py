import os


def remove_empty_prefix_lines(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        with open(file_path, "w", encoding="utf-8") as file:
            for line in lines:
                if '"prefix": ""' not in line:
                    file.write(line)

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")


def process_all_json_files_in_directory(directory):
    for subdir, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(subdir, file)
                remove_empty_prefix_lines(file_path)


if __name__ == "__main__":
    data_directory = "data/"  # Path to your data directory
    process_all_json_files_in_directory(data_directory)
