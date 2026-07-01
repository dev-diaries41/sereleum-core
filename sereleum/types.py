from typing import Literal

# Long running jobs
FinishedStatus = Literal['complete', 'failed']
Status = Literal[
    FinishedStatus,
    "active",
    "delayed",
    "queued",
]