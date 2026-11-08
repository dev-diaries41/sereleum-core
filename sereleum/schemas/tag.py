from pydantic import BaseModel

class Tag(BaseModel):
    id: int
    name: str

class TagCrossRef(BaseModel):
    item_id: str
    tag_id: int