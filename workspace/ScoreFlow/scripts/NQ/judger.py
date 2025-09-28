from typing import Literal
import ScoreFlow.scripts.NQ.operator as operator
from metagpt.provider.llm_provider_registry import create_llm_instance


def _normalize(s: str) -> str:
    import re, string
    s = s or ""
    s = s.strip().lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\s+", " ", s)
    return s


class Workflow:
    def __init__(
        self,
        llm_config,
    ) -> None:
        self.llm = create_llm_instance(llm_config)

    async def __call__(self, question: str, model_answer: str, right_answer: str):
        """
        Simple judgment: After normalization, if there's exact match or containment match, score 1, otherwise 0.
        """
        p = _normalize(model_answer)
        g = _normalize(right_answer)
        if not g:
            return 0
        return 1 if (p == g or g in p) else 0


