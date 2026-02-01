from typing import Iterator, Callable, TypeVar

T = TypeVar("T")

def paginate_until_total(fetch_fn: Callable[[int, int], T], total: int, batch_size: int = 500, initial_offset: int = 0) -> Iterator[T]:
    offset = initial_offset
    while offset < total:
        yield fetch_fn(offset, batch_size)
        offset += batch_size

def paginate_until(fetch_fn: Callable[[int, int], T], break_fn: Callable[[T], bool], batch_size: int = 500, initial_offset: int = 0) -> Iterator[T]:
    offset = initial_offset
    while True:
        batch = fetch_fn(offset, batch_size)
        if break_fn(batch):
            break
        yield batch
        offset += batch_size