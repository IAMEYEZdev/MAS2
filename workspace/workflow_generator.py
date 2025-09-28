from typing import List
import importlib
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
import asyncio
from difflib import SequenceMatcher


try:
    from vllm import LLM as VLLM, SamplingParams  
except Exception: 
    VLLM = None 

    class SamplingParams:  
        def __init__(self, *args, **kwargs) -> None:
            pass




import tempfile
import shutil
import asyncio
from importlib import __import__
import importlib.util


try:
    from vllm.lora.request import LoRARequest  
except Exception:  
    class LoRARequest: 
        def __init__(self, *args, **kwargs) -> None:
            pass


def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def similarity_ratio(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()



def test_if_runable(
    graph_text,
    TEMP_AVOID,
    PYTHON_START,
    PYTHON_END,
    NO_EXCEPTION_LIST,
    TEST_PROMPT,
    sim_threshold,
):
    temp_dir = None
    try:
        graph_content = re.search(r"<graph>(.*?)</graph>", graph_text, re.DOTALL)
        if graph_content is None:
            return False
        class_script = graph_content.group(1).strip()

        extract_graph_script = re.search(
            r"async def run_workflow\(self\)(.*?)return", class_script, re.DOTALL
        )
        if extract_graph_script is None:
            return False
        extract_graph_script = extract_graph_script.group(1).strip()


        extract_TEMP_AVOID = re.search(
            r"async def run_workflow\(self\)(.*?)return", TEMP_AVOID, re.DOTALL
        )
        if extract_TEMP_AVOID is None:
            return False 
        extract_TEMP_AVOID = extract_TEMP_AVOID.group(1).strip()
        similar_score = similarity_ratio(extract_graph_script, extract_TEMP_AVOID)
        if similar_score >= sim_threshold:
            return False

        
        safe_python_start = PYTHON_START
        marker = "from metagpt.provider.llm_provider_registry import create_llm_instance as create"
        if marker in safe_python_start:
            safe_python_start = safe_python_start.replace(
                marker,
                "class _Dummy:\n    pass\n\n# stub create to avoid real LLM init during static runability test\ndef create(config):\n    return _Dummy()",
            )
        python_script = safe_python_start + class_script + PYTHON_END

       
        temp_dir = tempfile.mkdtemp()
        graph_file_path = os.path.join(temp_dir, "graph_test.py")

        with open(graph_file_path, "w", encoding="utf-8") as graph_file:
            graph_file.write(python_script)


        for no_exception in NO_EXCEPTION_LIST:
            if no_exception in extract_graph_script:
                return False

        spec = importlib.util.spec_from_file_location("graph_test", graph_file_path)
        graph_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph_module)


        try:
            setattr(graph_module, "create", lambda cfg: object())
        except Exception:
            pass


        graph_class = getattr(graph_module, "Workflow", None)
        if graph_class is None:
            return False

        return True

        print("====graph_text====")
        print(graph_text)
        return True

    except Exception as e:
        print(f"Test setup failed: {str(e)}")
        return False
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


class WorkflowGenerator:
    def __init__(self, llm, mode: str, local_model_dir=None, lora_dir=None, **kwargs):
        self.llm = llm
        self.mode = mode
        self.local_model_dir = local_model_dir
        self.lora_dir = lora_dir
        self.local_llm = llm  


    def generate(self, question, data_set, graph_num, lora_request=None):
        
        prompt_module = importlib.import_module(
            f"ScoreFlow.scripts.{data_set}.conditions"
        )
        TIME_LIMIT_TEST = prompt_module.TIME_LIMIT_TEST
        PYTHON_END = prompt_module.PYTHON_END
        sim_threshold = prompt_module.sim_threshold
        PYTHON_START = prompt_module.PYTHON_START
        TEMP_AVOID = prompt_module.TEMP_AVOID
        TEST_PROMPT = prompt_module.TEST_PROMPT
        NO_EXCEPTION_LIST = prompt_module.NO_EXCEPTION_LIST
        START_PORMPT = prompt_module.START_PORMPT
        END_PROMPT = prompt_module.END_PROMPT

        temple_file_path = "scoreflow_workspace/temp_gene_workflow_file"
        ensure_directory_exists(temple_file_path)

        attempt_limit = 10 

        
        sampling_params = SamplingParams(
            temperature=0.6, top_p=0.95, max_tokens=1000, stop=["</graph>"]
        )

        for i in range(graph_num):
            attempts = 0
            success = False
            print(f"graph:{i}/{graph_num}\n")
            while attempts < attempt_limit and not success:
                prompt = START_PORMPT + question["problem"] + END_PROMPT
                if self.mode == "local":
                    outputs = self.local_llm.generate(
                        [prompt], sampling_params, lora_request=lora_request
                    )
                    response = outputs[0].outputs[0].text
                    print(f"response:{response}")
                elif self.mode == "remote":
                    response = self.get_remote_response([prompt])[0]

                output_text = response + "</graph>"
                try:
                    if test_if_runable(
                        output_text,
                        TEMP_AVOID,
                        PYTHON_START,
                        PYTHON_END,
                        NO_EXCEPTION_LIST,
                        TEST_PROMPT,
                        sim_threshold,
                    ):
                        if (
                            data_set
                            and str(data_set).upper() == "MATH"
                            and '"llm_symbol"' not in output_text
                        ):
                            output_text = (
                                output_text.replace(
                                    "operator.Custom(", 'operator.Custom("llm_symbol", '
                                )
                                .replace(
                                    "operator.ScEnsemble(",
                                    'operator.ScEnsemble("llm_symbol", ',
                                )
                                .replace(
                                    "operator.Programmer(",
                                    'operator.Programmer("llm_symbol", ',
                                )
                                .replace(
                                    "operator.Review(", 'operator.Review("llm_symbol", '
                                )
                            )
                        elif (
                            data_set
                            and str(data_set).upper() == "NQ"
                            and '"llm_symbol"' not in output_text
                        ):
                            output_text = (
                                output_text.replace(
                                    "operator.Custom(", 'operator.Custom("llm_symbol", '
                                )
                                .replace(
                                    "operator.ScEnsemble(",
                                    'operator.ScEnsemble("llm_symbol", ',
                                )
                                .replace(
                                    "operator.AnswerGenerate(",
                                    'operator.AnswerGenerate("llm_symbol", ',
                                )
                                .replace(
                                    "operator.Review(", 'operator.Review("llm_symbol", '
                                )
                            )
                        return [output_text]
                    else:
                        attempts += 1
                except Exception as e:
                    print(f"Generation attempt {attempts} failed: {str(e)}")
                    attempts += 1
            if not success:
                print(f"Warning: The {i+1}th workflow still failed after {attempts} attempts.")
        return []

    def get_remote_response(self, prompts):
        self.client = OpenAI(
            api_key="<API_KEY>",
            base_url="https://openrouter.ai/api/v1",
        )
        response_list = []
        for prompt in prompts:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.5,
                top_p=0.95,
                stop=["</graph>"],
            )
            response_list.append(response.choices[0].message.content)
        return response_list


if __name__ == "__main__":
    llm = "gpt-4o-mini"
    workflow_generator = WorkflowGenerator(llm, "remote")
    problem = {
        "question_text": "What is the capital of France?",
        "answers": ["Paris"],
        "document_text": "France is a country in Western Europe. Its capital and largest city is Paris, which is located in the north-central part of the country along the Seine River.",
        "example_id": "test_example_001"
    }
    workflows = workflow_generator.generate(problem, "NQ", 1)
    print("Generated workflows:")
    for wf in workflows:
        print(wf)
