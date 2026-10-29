import os 
import json

from sereleum.data.types import TItem

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


def save_items(output: str, items: list[TItem]) -> None:
    with open(output, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, ensure_ascii=False, indent=2)

def load_items(path: str, item_cls: type[TItem]):
    with open(path) as f:
        return [item_cls(**item) for item in json.load(f)]
    