from typing import Any
from pydantic import BaseModel, ConfigDict

class Payload(BaseModel):
    model_config = ConfigDict(extra="allow")

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
