import tracemalloc
import time


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


## temp solution in prod use user selected labels
def get_true_labels(item_ids: list[str]):
        true_labels: dict[str, str] = {}
        for id in  item_ids:
            label = id.split("_")[0]
            if not label: 
                print(f"[WARNING] {id} is not a valid labelled item.")
                continue
            true_labels[id] = label
        return true_labels
