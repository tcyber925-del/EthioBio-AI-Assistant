import json
from dataclasses import dataclass


@dataclass
class TokenChunk:
    delta: str
    node: str = ""
    done: bool = False
    error: str | None = None
    status: bool = False

    def model_dump_json(self) -> str:
        return json.dumps({
            "delta": self.delta,
            "node": self.node,
            "done": self.done,
            "error": self.error,
            "status": self.status,
        })
