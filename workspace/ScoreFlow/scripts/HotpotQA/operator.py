import ast
import random
import sys
import traceback
from collections import Counter
from typing import Dict, List, Tuple, Any

from tenacity import retry, stop_after_attempt, wait_fixed

from ScoreFlow.scripts.HotpotQA.operator_an import *
from ScoreFlow.scripts.HotpotQA.op_prompt import *
from metagpt.actions.action_node import ActionNode
from metagpt.llm import LLM
import yaml
import types
from metagpt.provider.llm_provider_registry import (
    create_llm_instance as _create_llm,
    LLM_REGISTRY,
)
from metagpt.logs import logger
import re


def _to_cfg_namespace(d: dict) -> types.SimpleNamespace:
    cfg = types.SimpleNamespace(**d)
    api = getattr(cfg, "api_type", None)
    if isinstance(api, str):
        api_lower = api.lower()
        for key in list(LLM_REGISTRY.providers.keys()):
            key_name = getattr(key, "name", str(key))
            if str(key).lower() == api_lower or key_name.lower() == api_lower:
                cfg.api_type = key
                break
    if not hasattr(cfg, "pricing_plan"):
        setattr(cfg, "pricing_plan", getattr(cfg, "model", None))
    if not hasattr(cfg, "temperature"):
        setattr(cfg, "temperature", 0)
    if not hasattr(cfg, "proxy"):
        setattr(cfg, "proxy", None)
    if not hasattr(cfg, "use_system_prompt"):
        setattr(cfg, "use_system_prompt", True)
    if not hasattr(cfg, "stream"):
        setattr(cfg, "stream", False)
    if not hasattr(cfg, "timeout"):
        setattr(cfg, "timeout", None)
    if not hasattr(cfg, "max_token"):
        setattr(cfg, "max_token", 4096)
    if not hasattr(cfg, "max_tokens"):
        setattr(cfg, "max_tokens", 4096)
    if not hasattr(cfg, "calc_usage"):
        setattr(cfg, "calc_usage", False)
    return cfg


def get_llm_by_name(model_name: str):
    if model_name == "llm_symbol":
        return object()
    try:
        with open("config/config2.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    models_map = data.get("models", {}) or {}
    default_llm = data.get("llm", {}) or {}
    if model_name in models_map:
        raw_cfg = dict(models_map[model_name])
        raw_cfg.setdefault("model", model_name)
    else:
        raw_cfg = dict(default_llm)
        raw_cfg["model"] = model_name
    cfg = _to_cfg_namespace(raw_cfg)
    return _create_llm(cfg)


class Operator:
    def __init__(self, llm: Any):
        # Allow passing model name string or already constructed LLM instance
        if isinstance(llm, str):
            self.llm = get_llm_by_name(llm)
        else:
            self.llm = llm

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    async def _fill_node(self, op_class, prompt, mode=None, **extra_kwargs):
        fill_kwargs = {"context": prompt, "llm": self.llm}
        if mode:
            fill_kwargs["mode"] = mode
        fill_kwargs.update(extra_kwargs)
        node = await ActionNode.from_pydantic(op_class).fill(**fill_kwargs)
        return node.instruct_content.model_dump()


class Custom(Operator):
    def __init__(self, llm: Any, *args, **kwargs):
        super().__init__(llm)
        if "problem" in kwargs:
            self.problem = kwargs["problem"]
        elif args:
            self.problem = args[-1]
        else:
            self.problem = None

    async def __call__(self, instruction):
        
        prompt = instruction + self.problem
        response = await self._fill_node(GenerateOp, prompt, mode="single_fill")
        
        return response["response"]
    
class AnswerGenerate(Operator):
    def __init__(self, llm: Any, *args, **kwargs):
        super().__init__(llm)
        if "problem" in kwargs:
            self.problem = kwargs["problem"]
        elif args:
            self.problem = args[-1]
        else:
            self.problem = None

    async def __call__(self) -> Tuple[str, str]:
        prompt = ANSWER_GENERATION_PROMPT.format(input=self.problem)
        response = await self._fill_node(AnswerGenerateOp, prompt, mode="xml_fill")
        answer = response.get("answer", "")
        thought = response.get("thought", "")
        final_response = thought + "\n So we have the final results: " +  answer  
        
        return final_response

class Review(Operator):
    def __init__(self, llm: Any, *args, **kwargs):
        super().__init__(llm)
        if "problem" in kwargs:
            self.problem = kwargs["problem"]
        elif args:
            self.problem = args[-1]
        else:
            self.problem = None

    async def __call__(self, pre_solution):
        
        prompt = REVIEW_PROMPT.format(problem=self.problem, solution=pre_solution)
        response = await self._fill_node(ReviewOp, prompt, mode="xml_fill")
        answer = response.get("revised_solution", "")

        return answer


class ScEnsemble(Operator):

    def __init__(self, llm: Any, *args, **kwargs):
        super().__init__(llm)
        if "problem" in kwargs:
            self.problem = kwargs["problem"]
        elif args:
            self.problem = args[-1]
        else:
            self.problem = None

    async def __call__(self, solutions: List[str]):
        answer_mapping = {}
        solution_text = ""
        for index, solution in enumerate(solutions):
            answer_mapping[chr(65 + index)] = index
            solution_text += f"{chr(65 + index)}: \n{str(solution)}\n\n\n"

        prompt = SC_ENSEMBLE_PROMPT.format(problem=self.problem, solutions=solution_text)
        response = await self._fill_node(ScEnsembleOp, prompt, mode="xml_fill")
        answer = response.get("solution_letter", "")
        answer = answer.strip().upper()
        
        return solutions[answer_mapping[answer]]