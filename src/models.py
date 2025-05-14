from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Antenna:
    antenna_id: str
    x: float
    y: float

@dataclass
class Tag:
    tag_id: str
    type: str  # 'ref' or 'tar'
    true_x: Optional[float] = None
    true_y: Optional[float] = None
    pred_x: Optional[float] = None
    pred_y: Optional[float] = None
    is_read: bool = False

    def __post_init__(self):
        if self.type not in ('ref', 'tar'):
            raise ValueError(f"Tag.type must be 'ref' or 'tar', got {self.type}")
        if self.type == 'ref' and (self.pred_x is not None or self.pred_y is not None):
            raise ValueError("Reference tags should not have pred_x or pred_y")

@dataclass
class Record:
    tag_id: str
    antenna_id: str
    rc: int
    rssi: float
    read_time: datetime = field(default_factory=datetime.now)
    record_id: Optional[int] = None
