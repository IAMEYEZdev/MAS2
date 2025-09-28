import concurrent
import sys
import traceback
from typing import List, Any
import io
import contextlib

from tenacity import retry, stop_after_attempt, wait_fixed

from ScoreFlow.scripts.MATH.operator_an import *
from ScoreFlow.scripts.MATH.op_prompt import *
from metagpt.actions.action_node import ActionNode
from metagpt.llm import LLM
import asyncio
import logging


import yaml
import types
from metagpt.provider.llm_provider_registry import (
    create_llm_instance as _create_llm,
    LLM_REGISTRY,
)


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

        prompt = REVIEW_PROMPT.replace("{problem}", str(self.problem)).replace(
            "{solution}", str(pre_solution)
        )
        response = await self._fill_node(ReviewOp, prompt, mode="xml_fill")
        answer = response.get("revised_solution", "")

        return answer


def run_code(code):
    try:

        global_namespace = {}

        disallowed_imports = [
            "os",
            "sys",
            "subprocess",
            "multiprocessing",
            "matplotlib",
            "seaborn",
            "plotly",
            "bokeh",
            "ggplot",
            "pylab",
            "tkinter",
            "PyQt5",
            "wx",
            "pyglet",
        ]


        for lib in disallowed_imports:
            if f"import {lib}" in code or f"from {lib}" in code:
                logger.info("Detected prohibited import: %s", lib)
                return "Error", f"Prohibited import: {lib} and graphing functionalities"


        stdout_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf):
            exec(code, global_namespace)

        if "solve" in global_namespace and callable(global_namespace["solve"]):
            result = global_namespace["solve"]()
            return "Success", str(result)
        return "Error", "Function 'solve' not found"
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_str = traceback.format_exception(exc_type, exc_value, exc_traceback)
        return "Error", f"Execution error: {str(e)}\n{''.join(tb_str)}"


class Programmer(Operator):
    def __init__(self, llm: Any, *args, **kwargs):
        super().__init__(llm)
        if "problem" in kwargs:
            self.problem = kwargs["problem"]
        elif args:
            self.problem = args[-1]
        else:
            self.problem = None

    async def exec_code(self, code, timeout=30):
        """
        Asynchronously execute code and return an error if timeout occurs.
        """
        loop = asyncio.get_running_loop()
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            try:

                future = loop.run_in_executor(executor, run_code, code)

                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:

                executor.shutdown(wait=False, cancel_futures=True)
                return "Error", "Code execution timed out"
            except Exception as e:
                return "Error", f"Unknown error: {str(e)}"

    async def code_generate(self, problem, analysis, feedback, mode):
        """
        Asynchronous method to generate code.
        """

        prompt = (
            PYTHON_CODE_VERIFIER_PROMPT.replace("{problem}", str(problem))
            .replace("{analysis}", str(analysis))
            .replace("{feedback}", str(feedback))
        )
        response = await self._fill_node(
            CodeGenerateOp, prompt, mode, function_name="solve"
        )
        return response

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def __call__(self, analysis: str = "None"):
        """
        Call method, generate code and execute, retry up to 3 times.
        """
        code = None
        output = None
        feedback = ""
        for i in range(3):
            code_response = await self.code_generate(
                self.problem, analysis, feedback, mode="code_fill"
            )
            code = code_response.get("code")
            if not code:
                return "No code generated"
            status, output = await self.exec_code(code)
            if status == "Success":
                return (
                    "After executing the following code written by llm agent.\n"
                    + code
                    + "\nWe have the following output: "
                    + output
                )
            else:
                print(f"Execution error on attempt {i + 1}, error message: {output}")
                feedback = (
                    f"\nThe result of the error from the code you wrote in the previous round:\n"
                    f"Code: {code}\n\nStatus: {status}, {output}"
                )
        return (
            "After executing the following code written by llm agent.\n"
            + code
            + "\nWe have the following output: "
            + output
        )


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


        prompt = SC_ENSEMBLE_PROMPT.replace("{problem}", str(self.problem)).replace(
            "{solutions}", solution_text
        )
        response = await self._fill_node(ScEnsembleOp, prompt, mode="xml_fill")
        answer = response.get("solution_letter", "")
        answer = answer.strip().upper()

        return solutions[answer_mapping[answer]]
