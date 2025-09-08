from __future__ import annotations

from typing import Dict
from pydantic import BaseModel
from .config import settings


class RuntimeConfigState(BaseModel):
    category_to_workshop: Dict[str, str] = {
        "精简摘要": "summary-01",
        "深度思考": "snapshot-insight",
    }


class RuntimeConfig:
    def __init__(self) -> None:
        self._state = RuntimeConfigState()

    def get_category_map(self) -> Dict[str, str]:
        return dict(self._state.category_to_workshop)

    def set_category_map(self, mapping: Dict[str, str]) -> None:
        # Replace entirely to make behavior explicit and predictable
        self._state.category_to_workshop = dict(mapping)


runtime_config = RuntimeConfig()


