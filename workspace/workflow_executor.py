import importlib.util
import traceback
import os
import re
import uuid

workflow_text = '''
<graph>
class Workflow:
    def __init__(self, problem) -> None:
        self.problem = problem["problem"] if isinstance(problem, dict) else str(problem)
        self.agent = create(config)
        self.custom = operator.Custom(self.agent, gid=None, problem=self.problem)
        self.programmer = operator.Programmer(self.agent, gid=None, problem=self.problem)
        self.sc_ensemble = operator.ScEnsemble(self.agent, gid=None, problem=self.problem)

    async def run_workflow(self):
        """
        This is a workflow graph.
        """
        analysis = await self.custom(instruction="Can you solve this problem by breaking it down into detailed steps and explaining the reasoning behind each step?")
        program_result = await self.programmer(analysis=analysis)
        return {"solution": program_result}
</graph>
'''


class WorkflowExecutor:
    def __init__(self, temp_dir="scoreflow_workspace/tmp_executor"):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_class_code(self, workflow_text: str) -> str:
        if workflow_text.strip().startswith("```"):
            workflow_text = re.sub(r"^\s*```[a-zA-Z]*\s*", "", workflow_text.strip())
            workflow_text = re.sub(r"\s*```\s*$", "", workflow_text)
            workflow_text = workflow_text.strip()

        match = re.search(r"<graph>([\s\S]*?)</graph>", workflow_text, re.DOTALL)
        if match:
            return match.group(1).strip()

     
        if "class Workflow:" in workflow_text:
            return workflow_text

        raise ValueError("No <graph>...</graph> or 'class Workflow:' block found.")

    def execute_from_text(self, workflow_text: str, data_set: str, problem) -> dict:
        """
        Extract Workflow class -> write to py file -> execute run_workflow()

        Args:
            workflow_text (str): Complete workflow code containing <graph>
            problem (str): Problem description

        Returns:
            dict: Contains execution status, result or error
        """
        try:
            prompt_module = importlib.import_module(
                f"ScoreFlow.scripts.{data_set}.conditions"
            )
            TIME_LIMIT = prompt_module.TIME_LIMIT
            PYTHON_END = prompt_module.PYTHON_END
            PYTHON_START = prompt_module.PYTHON_START
            if "create_llm_instance as create" in PYTHON_START:
                PYTHON_START = (
                    PYTHON_START + "\nimport types, yaml\n"
                    "from metagpt.provider.llm_provider_registry import create_llm_instance as _create, LLM_REGISTRY\n"
                    'with open("config/config2.yaml", "r", encoding="utf-8") as f:\n'
                    "    _cfg = yaml.safe_load(f)\n"
                    "class _Cfg(types.SimpleNamespace):\n"
                    "    def __getattr__(self, name):\n"
                    "        return None\n"
                    'config = _Cfg(**_cfg.get("llm", {}))\n'
                    "def create(cfg):\n"
                    '    api = getattr(cfg, "api_type", None)\n'
                    "    if isinstance(api, str):\n"
                    "        api_lower = api.lower()\n"
                    "        for key in list(LLM_REGISTRY.providers.keys()):\n"
                    '            key_name = getattr(key, "name", str(key))\n'
                    "            if str(key).lower() == api_lower or key_name.lower() == api_lower:\n"
                    "                cfg.api_type = key\n"
                    "                break\n"
                    "        else:\n"
                    "            for key in list(LLM_REGISTRY.providers.keys()):\n"
                    '                key_name = getattr(key, "name", str(key)).lower()\n'
                    '                if "openai" in api_lower and "openai" in key_name:\n'
                    "                    cfg.api_type = key\n"
                    "                    break\n"
                    "
                    '    if not hasattr(cfg, "pricing_plan"):\n'
                    '        setattr(cfg, "pricing_plan", getattr(cfg, "model", None))\n'
                    '    if not hasattr(cfg, "temperature"):\n'
                    '        setattr(cfg, "temperature", 0)\n'
                    '    if not hasattr(cfg, "proxy"):\n'
                    '        setattr(cfg, "proxy", None)\n'
                    '    if not hasattr(cfg, "use_system_prompt"):\n'
                    '        setattr(cfg, "use_system_prompt", True)\n'
                    '    if not hasattr(cfg, "stream"):\n'
                    '        setattr(cfg, "stream", False)\n'
                    "    return _create(cfg)\n"
                )
        
            class_code = self.extract_class_code(workflow_text)
            class_code = PYTHON_START + class_code + PYTHON_END.format(time=TIME_LIMIT)

            uid = str(uuid.uuid4()).replace("-", "_")
            temp_file_path = os.path.join(self.temp_dir, f"{uid}_workflow.py")
            with open(temp_file_path, "w") as f:
                f.write(class_code)

   
            spec = importlib.util.spec_from_file_location(
                "workflow_module", temp_file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            WorkflowClass = getattr(module, "Workflow")
            try:
                instance = WorkflowClass(problem)
            except TypeError:
                instance = WorkflowClass(module.__dict__.get("config", {}), problem)

            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(instance())
            if isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {
                    "solution": str(result),
                    "token_usage": {"total_cost": 0},
                }
            token_usage = result_dict.get("token_usage", {"total_cost": 0})

            os.remove(temp_file_path)

            return {
                "success": True,
                "result": result_dict.get("solution", ""),
                "error": None,
                "token_cost": token_usage.get("total_cost", 0),
            }

        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": traceback.format_exc(),
                "token_cost": 0,
            }


def main():
    question = {
        "question_text": "What is the capital of France?",
        "answers": ["Paris"],
        "document_text": "France is a country in Western Europe. Its capital and largest city is Paris, which is located in the north-central part of the country.",
        "example_id": "test_example_001"
    }
    executor = WorkflowExecutor()

    result = executor.execute_from_text(
        workflow_text=workflow_text, data_set="NQ", problem=question
    )
    if result["success"]:
        print("✅ Execution successful:", result["result"])
        print("cost:", result["token_cost"] * 400)
    else:
        print("❌ Execution failed:", result["error"])


if __name__ == "__main__":
    main()
