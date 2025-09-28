import ast
import random
import sys
import traceback
from collections import Counter
from typing import Dict, List, Tuple

from ScoreFlow.scripts.HumanEval.operator_an import *
from ScoreFlow.scripts.HumanEval.op_prompt import *
from metagpt.actions.action_node import ActionNode
from metagpt.llm import LLM
from metagpt.logs import logger
from ScoreFlow.benchmark.humaneval import HumanEvalBenchmark
import yaml
import types
from metagpt.provider.llm_provider_registry import (
    create_llm_instance as _create_llm,
    LLM_REGISTRY,
)
import re
from enum import Enum
import json

class CodeDataset(Enum):
    HUMAN_EVAL = "HumanEval"
    MBPP = "MBPP"

def extract_test_cases_from_jsonl(entry_point: str, dataset: CodeDataset = CodeDataset.HUMAN_EVAL):
    """
    For HumanEval, prefer reading tests from the canonical CSV file and return the full
    test code block (string). For MBPP, keep legacy jsonl behavior if needed.
    """
    if dataset == CodeDataset.HUMAN_EVAL.value:
        # Read from HumanEval.csv
        try:
            import csv  # local import to avoid global dependency
            with open("data/HumanEval.csv", "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("entry_point") == entry_point:
                        return row.get("test")
        except Exception:
            return None
    elif dataset == CodeDataset.MBPP.value:
        file_path = "data/mbpp_public_test.jsonl"
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    data = json.loads(line)
                    if data.get("entry_point") == entry_point:
                        return data.get("test")
        except FileNotFoundError:
            return None

    return None



def test_case_2_test_function(solution: str, test_case: str, entry_point: str):
    tester_function = f"""
{solution}


def check(candidate):
    {test_case}

def test_check():
    check({entry_point})

test_check()
"""
    return tester_function



def _to_cfg_namespace(d: dict) -> types.SimpleNamespace:
    cfg = types.SimpleNamespace(**(d or {}))
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
        setattr(cfg, "max_token", 8192)
    if not hasattr(cfg, "max_tokens"):
        setattr(cfg, "max_tokens", 8192)
    if not hasattr(cfg, "calc_usage"):
        setattr(cfg, "calc_usage", False)
    return cfg


def get_llm_by_name(model_name: str):
    try:
        with open("config/config2.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}

    models_map = data.get("models", {}) or {}
    if model_name in models_map:
        raw_cfg = dict(models_map[model_name])
        raw_cfg["model"] = model_name
    else:
        raw_cfg = dict(data.get("llm", {}) or {})
        raw_cfg["model"] = model_name

    cfg = _to_cfg_namespace(raw_cfg)
    return _create_llm(cfg)


class Operator:
    def __init__(self, llm: LLM):
        # Accept either an LLM instance or a model name string filled by implementer
        if isinstance(llm, str):
            # Build a fully-configured MetaGPT LLM via config (respects max_tokens/timeout/stream)
            try:
                self.llm = get_llm_by_name(llm)
            except Exception:
                # Fallback wrapper if config creation fails
                self.llm = LLM()
                self.llm.model = llm
            self.model = llm
        else:
            self.llm = llm
            self.model = getattr(llm, "model", "unknown")

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    async def _fill_node(self, op_class, prompt, mode=None, **extra_kwargs):
        # Ensure llm is a valid MetaGPT LLM instance (not a string)
        llm_obj = self.llm
        if isinstance(llm_obj, str):
            # try to build from config when a plain string slipped through
            try:
                llm_obj = get_llm_by_name(llm_obj)
            except Exception:
                tmp = LLM()
                tmp.model = llm_obj
                llm_obj = tmp
        fill_kwargs = {"context": prompt, "llm": llm_obj}
        if mode:
            fill_kwargs["mode"] = mode
        fill_kwargs.update(extra_kwargs)
        node = await ActionNode.from_pydantic(op_class).fill(**fill_kwargs)
        return node.instruct_content.model_dump()


class Custom(Operator):
    def __init__(self, llm: LLM, problem: str = None):
        super().__init__(llm)
        self.problem = "You have the following task: " + problem["prompt"]

    async def __call__(self, instruction):
        
        prompt = instruction + self.problem
        response = await self._fill_node(GenerateOp, prompt, mode="single_fill")
        
        return response["response"]
    
class CustomCodeGenerate(Operator):
    def __init__(self, llm: LLM, problem: str = None):
        super().__init__(llm)
        self.problem = "You have the following task: " + problem["prompt"]
        # Keep original dict for downstream use (e.g., Test operator)
        self.problem_dict = problem
        self.entry_point = problem["entry_point"]

    async def __call__(self, instruction):
        prompt = instruction + self.problem + CustomCodeGenerate_PROMPT
        response = await self._fill_node(GenerateOp, prompt, mode="code_fill", function_name=self.entry_point)
        return response['response']

class Review(Operator):
    def __init__(self, llm: LLM, problem: str = None):
        super().__init__(llm)
        self.problem = problem["prompt"]
        self.problem_dict = problem
        self.entry_point = problem["entry_point"]

    async def __call__(self, pre_solution):
        
        prompt = REVIEW_PROMPT.format(problem=self.problem, entry_point=self.entry_point, solution=pre_solution)
        response = await self._fill_node(ReviewOp, prompt, mode="xml_fill")
        answer = response.get("final_code", "")
        
        return answer

class ScEnsemble(Operator):

    def __init__(self, llm: LLM, problem: str = None):
        super().__init__(llm)
        self.problem = "You have the following task: " + problem["prompt"]
        self.problem_dict = problem

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

class Test(Operator):
    # Use the public test set to test the code, then revise the code based on the test result. Once reach the max iteration while still not pass, try generate again.
    def __init__(self, llm: LLM, problem: str = None):
        super().__init__(llm)
        self.code_generate = CustomCodeGenerate(llm, problem)
        self.problem = "You have the following task: " + problem["prompt"]
        self.problem_dict = problem
        self.entry_point = problem["entry_point"]

    def exec_code(self, solution):
        # Prioritize using the test field that comes with the problem (from HumanEval CSV), avoid external file dependencies
        problem_dict = self.problem_dict if isinstance(getattr(self, "problem_dict", None), dict) else {}
        test_code_block = problem_dict.get("test") if problem_dict else None
        if test_code_block:
            try:
                bench = HumanEvalBenchmark(name="HumanEval", file_path="", log_path="logs")
                ret = bench.check_solution(solution, test_code_block, self.entry_point)
                return "no error" if ret[0] == bench.PASS else [{"test_fail_case": {"error_type": "AssertionError", "error_message": ret[1]}}]
            except Exception as e:
                return {"exec_fail_case": str(e)}

        # Fallback solution: extract assertions from public test set and wrap execution
        test_cases = extract_test_cases_from_jsonl(self.entry_point, dataset="HumanEval")
        if not test_cases:
            return {"exec_fail_case": "No test cases available for entry_point."}

        fail_cases = []
        for test_case in test_cases:
            test_code = test_case_2_test_function(solution, test_case, self.entry_point)
            print("test_code:\n\n", test_code)
            try:
                exec(test_code, globals())
            except AssertionError as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb_str = traceback.format_exception(exc_type, exc_value, exc_traceback)
                with open("tester.txt", "a") as f:
                    f.write("test_error of " + self.entry_point + "\n")
                error_infomation = {
                    "test_fail_case": {
                        "test_case": test_case,
                        "error_type": "AssertionError",
                        "error_message": str(e),
                        "traceback": tb_str,
                    }
                }
                fail_cases.append(error_infomation)
            except Exception as e:
                with open("tester.txt", "a") as f:
                    f.write(self.entry_point + " " + str(e) + "\n")
                return {"exec_fail_case": str(e)}
        if fail_cases != []:
            return fail_cases
        else:
            return "no error"
    
    async def __call__(
        self, solution, test_loop: int = 10
    ):
        
        for _ in range(test_loop):
            result = self.exec_code(solution)
            if result == "no error":
                print("NO ERROR\n\n")
                return solution
            elif "exec_fail_case" in result:
                print("fail1:\n", result)
                result = result["exec_fail_case"]
                prompt = REFLECTION_ON_PUBLIC_TEST_PROMPT.format(
                    problem=self.problem,
                    solution=solution,
                    exec_pass=f"executed unsuccessfully, error: \n {result}",
                    test_fail="executed unsucessfully",
                    entry_point=self.entry_point
                )
                response = await self._fill_node(ReflectionTestOp, prompt, mode="code_fill")
                solution = response["reflection_and_solution"]
            else:
                print("fail2:\n", result)
                prompt = REFLECTION_ON_PUBLIC_TEST_PROMPT.format(
                    problem=self.problem,
                    solution=solution,
                    exec_pass="executed successfully",
                    test_fail=result,
                    entry_point=self.entry_point
                )
                response = await self._fill_node(ReflectionTestOp, prompt, mode="code_fill")
                solution = response["reflection_and_solution"]
        
        result = self.exec_code(solution)
        if result == "no error":
            return solution
        else:
            solution = await self.code_generate(instruction="Can you analyze this problem step by step and generate the code?")
            return solution



