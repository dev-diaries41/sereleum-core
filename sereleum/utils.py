import tracemalloc
import time
import os 
import tiktoken

from typing import Iterator, Callable, TypeVar
from openai.types import ResponsesModel


T = TypeVar("T")

def paginated_read(fetch_fn: Callable[[int, int], T], total: int, batch_size: int = 500, initial_offset: int = 0) -> Iterator[T]:
    offset = initial_offset
    while offset < total:
        yield fetch_fn(offset, batch_size)
        offset += batch_size

def paginated_read_until_empty(fetch_fn: Callable[[int, int], T], break_fn: Callable[[T], bool], batch_size: int = 500, initial_offset: int = 0) -> Iterator[T]:
    offset = initial_offset
    while True:
        batch = fetch_fn(offset, batch_size)
        if break_fn(batch):
            break
        yield batch
        offset += batch_size

def with_mem_profile(func):
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        print(f"Current memory usage: {current / 1024**2:.2f} MB | Peak memory usage: {peak / 1024**2:.2f} MB")
        return result
    return wrapper


def with_time(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        time_elapsed = time.perf_counter() - start
        print(f" Time elapsed: {time_elapsed:.6f} s")
        return result, time_elapsed
    return wrapper


def get_new_dirname(dir_path: str, prefix: str):
    os.makedirs(dir_path, exist_ok=True)
    highest = -1
    dirs = os.listdir(dir_path)
    if len(dirs) == 0:
        return os.path.join(dir_path, prefix + "0")
    for d in dirs:
        if not d.startswith(prefix):
            continue
        n = int(d.strip(prefix))
        highest = n if n > highest else highest
    return os.path.join(dir_path, prefix + str(highest + 1))


def get_new_filename(dir_path: str, prefix: str, ext):
    os.makedirs(dir_path, exist_ok=True)
    highest = -1
    files = os.listdir(dir_path)
    if len(files) == 0:
        return os.path.join(dir_path,  prefix + "0" + ext)
    for f in files:
        if not f.startswith(prefix):
            continue
        n = int(os.path.splitext(f)[0].strip(prefix))
        highest = n if n > highest else highest
    return os.path.join(dir_path, prefix + str(highest + 1) + ext)



def count_tokens_embedding(text: str, model: ResponsesModel) -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

