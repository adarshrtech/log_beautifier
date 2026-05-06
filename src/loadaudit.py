import json
import os

def load_audit_logs(file_path):
    """Opens the file and turns each line into a Python dictionary."""
    logs_list = []

    if os.path.exists(file_path) == False:
        return logs_list

    try:
        with open(file_path, "r") as my_file:
            for line in my_file:
                clean_line = line.strip()

                if clean_line != "":
                    try:
                        data = json.loads(clean_line)
                        logs_list.append(data)
                    except:
                        continue
    except:
        return []

    return logs_list
