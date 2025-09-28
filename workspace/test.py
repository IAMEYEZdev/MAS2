import os
import json
import argparse
import datetime
import asyncio
import traceback
import tempfile
import importlib.util
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

import test_config as config
from ScoreFlow.benchmark.nq import NQBenchmark
from workflow_generator import WorkflowGenerator
from workflow_implementer import Implementer
from workflow_rectifier import WorkflowRectifier

try:
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
except ImportError:
    print("Warning: VLLM not available. Please install vllm for local model support.")
    LLM = None
    SamplingParams = None
    LoRARequest = None


class VLLMWorkflowTester:
    def __init__(self):
        self.benchmark = NQBenchmark(name="NQ", file_path="", log_path=config.OUTPUT_DIR)
        self.setup_directories()
        self.setup_models()
        
    def setup_directories(self):
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        os.makedirs("scoreflow_workspace/temp_gene_workflow_file", exist_ok=True)
        
    def setup_models(self):
        if LLM is None:
            raise ImportError("VLLM is required for local model testing")
            

        self.generator_llm = LLM(
            model=config.GENERATOR_MODEL_DIR,
            tensor_parallel_size=1,
            gpu_memory_utilization=0.7,
            max_model_len=4096,
        )
        

        self.implementer_llm = LLM(
            model=config.IMPLEMENTER_MODEL_DIR,
            tensor_parallel_size=1,
            gpu_memory_utilization=0.7,
            max_model_len=4096,
        )
        

        self.rectifier_llm = LLM(
            model=config.RECTIFIER_MODEL_DIR,
            tensor_parallel_size=1,
            gpu_memory_utilization=0.7,
            max_model_len=4096,
        )
        

        self.workflow_generator = WorkflowGenerator(
            llm=self.generator_llm,
            mode="local",
            local_model_dir=config.GENERATOR_MODEL_DIR,
            lora_dir=config.GENERATOR_LORA_DIR
        )
        
        self.workflow_implementer = Implementer(
            llm=self.implementer_llm,
            mode="local",
            local_model_dir=config.IMPLEMENTER_MODEL_DIR,
            lora_dir=config.IMPLEMENTER_LORA_DIR
        )
        
        self.workflow_rectifier = WorkflowRectifier(
            llm=self.rectifier_llm,
            mode="local",
            local_model_dir=config.RECTIFIER_MODEL_DIR,
            lora_dir=config.RECTIFIER_LORA_DIR
        )

    def load_nq_data(self, path: str, start: int, end: int) -> List[Dict[str, Any]]:
        problems: List[Dict[str, Any]] = []
        start = max(1, int(start))
        end = int(end)
        
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if idx < start:
                    continue
                if idx > end:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    item["task_id"] = idx
                    item["source_file"] = os.path.relpath(path)
                    problems.append(item)
                except Exception as e:
                    if config.VERBOSE:
                        print(f"Error loading line {idx}: {e}")
                    pass
        return problems

    def generate_workflow(self, problem: Dict[str, Any]) -> Optional[str]:

        lora_request = None
        if config.GENERATOR_LORA_DIR and os.path.exists(config.GENERATOR_LORA_DIR):
            try:
                lora_request = LoRARequest(
                    lora_name="generator_lora",
                    lora_int_id=1,
                    lora_local_path=config.GENERATOR_LORA_DIR
                )
            except Exception as e:
                if config.VERBOSE:
                    print(f"Failed to create LoRA request for generator: {e}")
        
        for attempt in range(config.MAX_WORKFLOW_GENERATION_ATTEMPTS):
            try:

                question_data = {
                    "problem": problem.get("question_text", "")
                }
                workflows = self.workflow_generator.generate(
                    question=question_data,
                    data_set="NQ",
                    graph_num=1,
                    lora_request=lora_request
                )
                if workflows and len(workflows) > 0:
                    return workflows[0]
            except Exception as e:
                if config.VERBOSE:
                    print(f"Workflow generation attempt {attempt + 1} failed: {e}")
                continue
        return None

    def implement_workflow(self, workflow: str) -> Optional[str]:

        lora_request = None
        if config.IMPLEMENTER_LORA_DIR and os.path.exists(config.IMPLEMENTER_LORA_DIR):
            try:
                lora_request = LoRARequest(
                    lora_name="implementer_lora",
                    lora_int_id=2,
                    lora_local_path=config.IMPLEMENTER_LORA_DIR
                )
            except Exception as e:
                if config.VERBOSE:
                    print(f"Failed to create LoRA request for implementer: {e}")
        
        try:
            implemented_workflows = self.workflow_implementer.implement(
                workflows=[workflow],
                replication_factor=1,
                lora_request=lora_request
            )
            if implemented_workflows and len(implemented_workflows) > 0:
                return implemented_workflows[0]["implemented_workflow"]
        except Exception as e:
            if config.VERBOSE:
                print(f"Workflow implementation failed: {e}")
        return None

    def execute_workflow(self, workflow: str, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:

            graph_match = re.search(r"<graph>(.*?)</graph>", workflow, re.DOTALL)
            if not graph_match:
                return {"error": "No valid workflow found in graph", "result": None}
            
            class_script = graph_match.group(1).strip()
            

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(f"""
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from ScoreFlow.scripts.NQ.operator import *
from metagpt.provider.llm_provider_registry import create_llm_instance as create

{class_script}

async def run_test(problem):
    workflow = Workflow(problem)
    try:
        result = await asyncio.wait_for(workflow.run_workflow(), timeout={config.TIMEOUT})
        return {{"success": True, "result": result}}
    except Exception as e:
        return {{"success": False, "error": str(e), "traceback": traceback.format_exc()}}

if __name__ == "__main__":
    import json
    problem = json.loads(sys.argv[1])
    result = asyncio.run(run_test(problem))
    print(json.dumps(result))
""")
                temp_file = f.name


            import subprocess
            result = subprocess.run([
                "python", temp_file, json.dumps(problem)
            ], capture_output=True, text=True, timeout=config.TIMEOUT)
            

            os.unlink(temp_file)
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON output", "result": result.stdout}
            else:
                return {
                    "error": f"Execution failed with return code {result.returncode}",
                    "stderr": result.stderr,
                    "stdout": result.stdout
                }
                
        except Exception as e:
            return {"error": f"Execution error: {str(e)}", "traceback": traceback.format_exc()}

    def rectify_workflow(self, broken_workflow: str, error_log: str) -> Optional[str]:

        lora_request = None
        if config.RECTIFIER_LORA_DIR and os.path.exists(config.RECTIFIER_LORA_DIR):
            try:
                lora_request = LoRARequest(
                    lora_name="rectifier_lora",
                    lora_int_id=3,
                    lora_local_path=config.RECTIFIER_LORA_DIR
                )
            except Exception as e:
                if config.VERBOSE:
                    print(f"Failed to create LoRA request for rectifier: {e}")
        
        for attempt in range(config.MAX_WORKFLOW_RECTIFICATION_ATTEMPTS):
            try:
                fixed_workflow = self.workflow_rectifier.rectify(broken_workflow, error_log, lora_request)
                if fixed_workflow and "<graph>" in fixed_workflow:
                    return fixed_workflow
            except Exception as e:
                if config.VERBOSE:
                    print(f"Workflow rectification attempt {attempt + 1} failed: {e}")
                continue
        return None

    def test_single_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "task_id": problem.get("task_id", "unknown"),
            "question": problem.get("question_text", ""),
            "gold_answers": problem.get("answers", []),
            "workflow_generation_success": False,
            "workflow_implementation_success": False,
            "workflow_execution_success": False,
            "final_answer": None,
            "f1_score": 0.0,
            "errors": [],
            "workflow_used": None
        }
        

        if config.VERBOSE:
            print(f"\n--- Testing Problem {result['task_id']} ---")
            print(f"Question: {result['question']}")
        
        workflow = self.generate_workflow(problem)
        if not workflow:
            result["errors"].append("Failed to generate workflow")
            return result
        
        result["workflow_generation_success"] = True
        result["workflow_used"] = workflow
        

        implemented_workflow = self.implement_workflow(workflow)
        if not implemented_workflow:
            result["errors"].append("Failed to implement workflow")
            return result
        
        result["workflow_implementation_success"] = True
        

        execution_attempts = 0
        max_execution_attempts = 3
        current_workflow = implemented_workflow
        
        while execution_attempts < max_execution_attempts:
            execution_result = self.execute_workflow(current_workflow, problem)
            
            if execution_result.get("success", False):
                result["workflow_execution_success"] = True
                result["final_answer"] = execution_result.get("result")
                break
            else:
                error_msg = execution_result.get("error", "Unknown execution error")
                result["errors"].append(f"Execution attempt {execution_attempts + 1}: {error_msg}")
                

                if execution_attempts < max_execution_attempts - 1:
                    rectified_workflow = self.rectify_workflow(current_workflow, error_msg)
                    if rectified_workflow:
                        current_workflow = rectified_workflow
                        result["workflow_used"] = current_workflow
                        if config.VERBOSE:
                            print(f"Workflow rectified, retrying execution...")
                    else:
                        result["errors"].append("Failed to rectify workflow")
                        break
                
                execution_attempts += 1
        

        if result["final_answer"]:
            try:
                f1_score, _ = self.benchmark.calculate_score(
                    result["gold_answers"], 
                    result["final_answer"]
                )
                result["f1_score"] = f1_score
            except Exception as e:
                result["errors"].append(f"F1 calculation error: {e}")
        
        if config.VERBOSE:
            print(f"Final Answer: {result['final_answer']}")
            print(f"F1 Score: {result['f1_score']}")
            if result["errors"]:
                print(f"Errors: {result['errors']}")
        
        return result

    def run_tests(self, start_line: int, end_line: int):
        print(f"Loading NQ data from {config.DATA_FILE} (lines {start_line}-{end_line})")
        problems = self.load_nq_data(config.DATA_FILE, start_line, end_line)
        print(f"Loaded {len(problems)} problems")
        
        if not problems:
            print("No problems loaded. Exiting.")
            return
        
        results = []
        successful_tests = 0
        total_f1 = 0.0
        
        for i, problem in enumerate(problems):
            print(f"\n{'='*50}")
            print(f"Processing problem {i+1}/{len(problems)}")
            
            result = self.test_single_problem(problem)
            results.append(result)
            
            if result["workflow_execution_success"]:
                successful_tests += 1
                total_f1 += result["f1_score"]
            

            if (i + 1) % 5 == 0:
                self.save_results(results, f"intermediate_results_{i+1}.json")
        

        avg_f1 = total_f1 / len(problems) if problems else 0.0
        success_rate = successful_tests / len(problems) if problems else 0.0
        
        print(f"\n{'='*50}")
        print(f"FINAL RESULTS:")
        print(f"Total problems: {len(problems)}")
        print(f"Successful executions: {successful_tests}")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Average F1 score: {avg_f1:.4f}")
        

        final_results = {
            "summary": {
                "total_problems": len(problems),
                "successful_executions": successful_tests,
                "success_rate": success_rate,
                "average_f1_score": avg_f1,
                "test_timestamp": datetime.datetime.now().isoformat()
            },
            "detailed_results": results
        }
        
        self.save_results(final_results, "final_results.json")
        print(f"Results saved to {config.OUTPUT_DIR}/")

    def save_results(self, results: Dict[str, Any], filename: str):
        output_path = os.path.join(config.OUTPUT_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Test NQ dataset with workflow pipeline")
    parser.add_argument("--start_line", type=int, default=config.START_LINE, 
                       help="Start line number in NQ.jsonl")
    parser.add_argument("--end_line", type=int, default=config.END_LINE,
                       help="End line number in NQ.jsonl")
    parser.add_argument("--data_file", type=str, default=config.DATA_FILE,
                       help="Path to NQ.jsonl file")
    
    args = parser.parse_args()
    

    config.DATA_FILE = args.data_file
    config.START_LINE = args.start_line
    config.END_LINE = args.end_line
    
    print("Initializing VLLM Workflow Tester...")
    print(f"Data file: {config.DATA_FILE}")
    print(f"Test range: lines {config.START_LINE}-{config.END_LINE}")
    print(f"Output directory: {config.OUTPUT_DIR}")
    print(f"Available LLMs: {config.AVAILABLE_LLMS}")
    
    try:
        tester = VLLMWorkflowTester()
        tester.run_tests(config.START_LINE, config.END_LINE)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
