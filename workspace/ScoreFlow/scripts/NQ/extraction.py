from typing import Literal
import ScoreFlow.scripts.NQ.operator as operator
from metagpt.provider.llm_provider_registry import create_llm_instance

class Workflow:
    def __init__(
        self,
        llm_config,
    ) -> None:
        self.llm = create_llm_instance(llm_config)


    async def __call__(self, question: str, model_answer: str):
        """
        Simple extractor: directly return model answer (can be trimmed as needed).
        """
        return model_answer

