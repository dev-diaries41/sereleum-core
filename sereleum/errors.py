

from enum import Enum
from typing import Dict, Optional, Union

class ErrorCode(Enum):
    INVALID_MODEL_PATH = "INVALID_MODEL_PATH"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    COLLECTION_NOT_FOUND = "COLLECTION_NOT_FOUND"
    ITEM_OR_COLLECTION_NOT_FOUND = "ITEM_OR_COLLECTION_NOT_FOUND"
    DUPLICATE_NAME = "DUPLICATE_NAME"
    MISSING_LABELLER = "MISSING_LABELLER"


class SereleumError(Exception):
    def __init__(self, message: str, code: Optional[ErrorCode] = None, details: Optional[Union[Dict, str, object]] = None):
        if details is None:
            details = {}
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)