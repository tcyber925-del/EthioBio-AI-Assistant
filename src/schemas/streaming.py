from dataclasses import dataclass


@dataclass
class TokenChunk:
    delta: str
    node: str = ""
    done: bool = False
    error: str | None = None
    status: bool = False
    metadata: dict | None = None

    def model_dump_json(self) -> str:
        import json
        d: dict = {
            "delta": self.delta,
            "node": self.node,
            "done": self.done,
            "error": self.error,
            "status": self.status,
        }
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return json.dumps(d)
