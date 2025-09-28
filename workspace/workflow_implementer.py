from openai import OpenAI
from typing import List

import re
import yaml
import json

try:
    from vllm import SamplingParams
except ImportError:
    SamplingParams = None


def load_models_from_config() -> List[str]:
    try:
        with open("config/config2.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    models_map = data.get("models", {}) or {}
    if models_map:
        return list(models_map.keys())

    return ["gpt-4o-mini", "gpt-4o"]


LLM_NAMES = load_models_from_config()

LLM_POOL = [
    {
        "Name": "gpt-4o-mini",
        "Description": """GPT-4o Mini is a smaller, faster variant of OpenAI’s GPT-4o multimodal model (released May 2024). 
It is optimized for lower latency. Best suited for lightweight tasks or as a fallback model 
when speed is prioritized over absolute peak performance.""",
    },
    {
        "Name": "gpt-4o",
        "Description": """GPT-4o is OpenAI’s flagship multimodal model released in May 2024, 
offering exceptional performance in complex reasoning, including mathematical proofs, symbolic manipulation, and multi-step derivations. 
Its long-context capabilities and strong instruction-following make it ideal for high-precision MATH dataset evaluations.""",
    },
    {
        "Name": "qwen/qwen-2.5-72b-instruct",
        "Description": """Qwen2.5-72B Instruct is a 72-billion-parameter instruction-tuned model from the Qwen 2.5 series. 
It excels in advanced mathematical reasoning, theorem verification, and long-form derivations, 
while also supporting multimodal understanding and extended context windows. 
Currently one of the most powerful open-source models for high-stakes reasoning tasks.""",
    },
    {
        "Name": "qwen/qwq-32b",
        "Description": """QwQ-32B is a medium-sized reasoning-optimized model from Qwen, strong at step-by-step multi-hop reasoning and QA""",
    },
]


def get_allowed_model_names() -> List[str]:
    catalog_names = [item["Name"] for item in LLM_POOL]
    allowed = [name for name in catalog_names if name in LLM_NAMES]
    return allowed or LLM_NAMES or ["gpt-4o-mini"]


OPERATOR_DESCRIPTION = [
    {
        "name": "Custom",
        "description": "Generate detailed step-by-step analysis and reasoning for factual questions, potentially using provided context.",
    },
    {
        "name": "AnswerGenerate",
        "description": "Directly generate concise final answers for factual QA tasks based on evidence and reasoning.",
    },
    {
        "name": "ScEnsemble",
        "description": "Evaluate multiple answer candidates and select the most accurate one for factual questions.",
    },
    {
        "name": "Review",
        "description": "Critique and refine solutions for factual questions, ensuring accuracy and completeness.",
    },
]


class Implementer:
    def __init__(self, llm, mode: str, local_model_dir=None, lora_dir=None):
        self.llm = llm
        self.mode = mode
        self.local_model_dir = local_model_dir
        self.lora_dir = lora_dir
        self.local_llm = llm  
        self.llm_remote_client = OpenAI(
            api_key="<API_KEY>",
            base_url="https://openrouter.ai/api/v1",
        )

    def implement(self, workflows, replication_factor: int = 1, lora_request=None):
        """
        Implements workflows with LLMs.

        Args:
            workflows (List[str]): A list of workflows to be processed.
            replication_factor (int): The number of times each workflow should be replicated with LLM filling.

        Returns:
            List[dict]: A list of dicts, each containing the implemented workflow, its parent workflow, and replication index.
        """
        implemented_workflow_infos = []
        for workflow in workflows:
            for i in range(replication_factor):
                prompt = self.generate_prompt(workflow_text=workflow)
                fix_workflow_text = None
                if self.mode == "remote":
                    response = self.get_response(prompt)
                else:

                    response = self.get_response(prompt)

                match = re.search(r"<graph>[\s\S]*?</graph>", response, re.DOTALL)
                fix_workflow_text = match.group(0) if match else response
                fix_workflow_text = re.sub(
                    r",\s*llm\s*=\s*\"[^\"]*\"", "", fix_workflow_text
                )
                fix_workflow_text = re.sub(
                    r",\s*model\s*=\s*\"[^\"]*\"", "", fix_workflow_text
                )

                fix_workflow_text = self.enforce_allowed_models(fix_workflow_text)

                if '"llm_symbol"' in fix_workflow_text:
                    model_map = self.build_default_model_map()
                    fix_workflow_text = self.fallback_fill_placeholders(
                        fix_workflow_text, model_map
                    )
                implemented_workflow_infos.append(
                    {
                        "implemented_workflow": fix_workflow_text,
                        "parent_workflow": workflow,
                        "replication_index": i,
                    }
                )
        return implemented_workflow_infos

    def generate_prompt(self, workflow_text):
        workflow_text = workflow_text + "</graph>"
        pattern = re.compile(r"<graph>(.*?)</graph>", re.DOTALL)
        match = pattern.search(workflow_text)
        Workflow_text = (
            "\n<graph>\n"
            + (match.group(1).strip() if match else workflow_text)
            + "\n</graph>"
        )

        allowed_names = get_allowed_model_names()
        llm_list = (
            "\n".join([f"- **{name}**" for name in allowed_names])
            or "- (none configured)"
        )

        llm_catalog = "\n".join(
            [f"- **{item['Name']}**: {item['Description']}" for item in LLM_POOL]
        )
        op_desc = "\n".join(
            [f"- **{d['name']}**: {d['description']}" for d in OPERATOR_DESCRIPTION]
        )

        prompt = f"""
        You are a model selector for AI workflows.

        Goal:
        Replace every string placeholder "llm_symbol" in operator constructors with the most suitable model name for that operator.
        DO NOT modify any function signatures or add any extra keyword arguments like llm= or model= to method calls.
        ONLY change the first argument of operator constructors (e.g., operator.Custom("llm_symbol", ...) → operator.Custom("gpt-4o-mini", ...)).

        Available LLMs (intersection with config/models):
        {llm_list}

        Reference LLM Catalog (with brief descriptions):
        {llm_catalog}

        Operator descriptions:
        {op_desc}

        CRITICAL INSTRUCTIONS:
        - ONLY replace "llm_symbol" strings, do NOT change "operator." paths
        - Keep the exact same operator paths as in the input code
        - Do NOT add any import statements or module prefixes
        - Output must be valid Python code that can be executed

        Final output MUST be only code, starting with <graph> and ending with </graph>.

        Workflow Code to Modify:
        {Workflow_text}
        """
        return prompt

    def build_default_model_map(self) -> dict:
        allowed = get_allowed_model_names()
        pick = lambda name: (
            name if name in allowed else (allowed[0] if allowed else "gpt-4o-mini")
        )
        return {
            "Custom": pick("gpt-4o"),
            "AnswerGenerate": pick("gpt-4o"),
            "Programmer": pick("gpt-4o"),
            "ScEnsemble": pick("gpt-4o"),
            "Review": pick("gpt-4o"),
        }

    def fallback_fill_placeholders(self, graph_text: str, model_map: dict) -> str:
        def repl(op_name: str, model: str, text: str) -> str:
            pattern = rf"operator\.{op_name}\(\s*\"llm_symbol\"\s*,"
            replacement = f'operator.{op_name}("{model}",'
            return re.sub(pattern, replacement, text)

        out = graph_text
        for op, model in model_map.items():
            out = repl(op, model, out)
        return out

    def enforce_allowed_models(self, graph_text: str) -> str:
        """Trim model names in constructors to allowed set to prevent selecting unconfigured models."""
        allowed = set(get_allowed_model_names())
        model_map = self.build_default_model_map()

        def sub_for_op(op: str, text: str) -> str:
            pat = re.compile(rf"(operator\.{op}\(\s*\")(.*?)(\"\s*,)")

            def repl(m):
                prefix, name, suffix = m.group(1), m.group(2), m.group(3)
                fixed = (
                    name if name in allowed else model_map.get(op, next(iter(allowed)))
                )
                return f"{prefix}{fixed}{suffix}"

            return pat.sub(repl, text)

        out = graph_text
        for op in ("Custom", "AnswerGenerate", "Programmer", "ScEnsemble", "Review"):
            out = sub_for_op(op, out)
        return out

    def get_response(self, prompt):
        if self.mode == "local":
            sampling_params = SamplingParams(
                temperature=0.7,
                top_p=0.95,
                max_tokens=1500,
            )
            outputs = self.local_llm.generate([prompt], sampling_params)
            return outputs[0].outputs[0].text
        else:
            response = self.llm_remote_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7,
            )
            return response.choices[0].message.content


if __name__ == "__main__":
    implementer = Implementer(llm=None, mode="remote")
    workflow_text = '''
    <graph>
    class Workflow:
        def __init__(self, problem) -> None:
            self.problem = problem
            self.custom = operator.Custom("llm_symbol", self.problem)
            self.sc_ensemble = operator.ScEnsemble("llm_symbol", self.problem)

        async def run_workflow(self):
            """
            This is a workflow graph for NQ dataset.
            """
            # Analyze the question with context
            analysis = await self.custom(instruction="Can you analyze this question and provide relevant information from the context?")
            # Ensemble multiple reasoning approaches
            final_answer = await self.sc_ensemble(solutions=[analysis])

            return {"solution": final_answer}
    </graph>
    '''
    workflow_list = [
        workflow_text,
    ]  
    replication_factor = 1  
    workflows = implementer.implement(
        workflow_list, replication_factor=replication_factor
    )
    print("Implemented workflows:")
    for wf in workflows:
        print(wf)
