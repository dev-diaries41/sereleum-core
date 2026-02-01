import os 

def get_new_dirname(dir_path: str, prefix: str):
    os.makedirs(dir_path, exist_ok=True)
    highest = -1

    for d in os.listdir(dir_path):
        if not d.startswith(prefix):
            continue

        num_part = d[len(prefix):]
        if not num_part.isdigit():
            continue

        n = int(num_part)
        if n > highest:
            highest = n

    return os.path.join(dir_path, f"{prefix}{highest + 1}")

def get_new_filename(dir_path: str, prefix: str, ext):
    os.makedirs(dir_path, exist_ok=True)
    highest = -1

    for f in os.listdir(dir_path):
        if not f.startswith(prefix) or not f.endswith(ext):
            continue

        name = os.path.splitext(f)[0]
        num_part = name[len(prefix):]

        if not num_part.isdigit():
            continue

        n = int(num_part)
        if n > highest:
            highest = n

    return os.path.join(dir_path, f"{prefix}{highest + 1}{ext}")
