from collections import defaultdict

from tqdm import tqdm

from logging import Logger

from sereleum.label.item_labeller import ItemLabeller
from sereleum.schemas.item import DocItem
from sereleum.data.stores.item_store import ItemStore
from sereleum.data.stores.tags.tag_store import TagStore

async def label_items(
        items: list[DocItem], 
        item_store: ItemStore[DocItem], 
        tag_store: TagStore, 
        labeller: ItemLabeller,
        logger: Logger,
        batch_size: int = 32
    ):
    offset = 0
    total_items = await item_store.count()

    processed = 0
    tagged = 0

    with tqdm(
        total=max(0, total_items - offset),
        desc="Labelling items",
        unit="items",
        dynamic_ncols=True
    ) as progress:
        while offset < total_items:
            batch_limit = min(batch_size, total_items - offset)
            items = await item_store.get(
                limit=batch_limit,
                offset=offset
            )

            if not items:
                break

            result = await labeller.label_items(items)

            grouped: dict[str, list[str]] = defaultdict(list)
            for item_id, label in result.items():
                grouped[label].append(item_id)

            for tag, item_ids in grouped.items():
                await tag_store.tag(tag, item_ids=item_ids)
                tagged += len(item_ids)

            processed += len(items)
            offset += len(items)

            progress.update(len(items))
            progress.set_postfix(
                batch=f"{processed // batch_size + 1}",
                labels=len(result),
                tags=len(grouped),
                tagged=tagged
            )

            logger.info(
                "Processed %d/%d items | Labels: %d | Tags: %d",
                processed,
                total_items,
                len(result),
                len(grouped)
            )

    logger.info(
        "Labelling complete. Processed: %d, Tagged: %d",
        processed,
        tagged
    )
