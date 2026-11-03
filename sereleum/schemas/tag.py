from pydantic import BaseModel

class Tag(BaseModel):
    id: str
    name: str

class TagCrossRef(BaseModel):
    item_id: str
    tag_id: int