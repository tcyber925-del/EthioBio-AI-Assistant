import random

from src.config import settings


class EvalSampler:
    def __init__(self):
        self._enabled = settings.eval_enabled
        self._rate = settings.eval_sampling_rate

    def should_evaluate(self, is_error: bool = False, token_count: int = 0) -> bool:
        if not self._enabled:
            return False
        if is_error:
            return True
        if token_count > 4000:
            return True
        return random.random() < self._rate
