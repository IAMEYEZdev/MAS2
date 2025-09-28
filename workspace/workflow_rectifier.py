from openai import OpenAI
from vllm import LLM, SamplingParams
from typing import List
workflow_template = '''
<graph>
class Workflow:
    def __init__(
        self,
        problem
    ) -> None:
        self.problem = problem
        self.code_generate = operator.CustomCodeGenerate("llm_symbol", self.problem)
        self.sc_ensemble = operator.ScEnsemble("llm_symbol", self.problem)
        self.test = operator.Test("llm_symbol", self.problem)

    async def run_workflow(self):
        """
        This is a workflow graph.
        """
        solution = await self.code_generate(instruction="Can you analyze this problem step by step and generate the code?")
        
        return solution
</graph>

Here's an introduction to operators you can use: (these are all you can use, do not create new operators)
1. CustomCodeGenerate:
Usage: Generates code based on customized input instruction.
Format MUST follow: code_generate(instruction: str) -> str
The instruction should encourage operator to think step by step, do not add the specific information of the task into the input instruction.
The output can serve as the input of next operators or the final output.
2. ScEnsemble:
Usage: Evaluate every solutions, then select the best solution in the solution list.
Format MUST follow: sc_ensemble(solutions: List[str]) -> str
You can ensemble few solutions, for example:
ensembled_solution = await self.sc_ensemble(solutions=solution_list)
The output can serve as the input of next operators or the final output.
3. Test:
Usage: Modify the input solution by testing the solution using public test cases.
Format MUST follow: test(solution: str) -> str
tested_solution = await self.test(solution=pre_solution)
'''

class WorkflowRectifier:
    def __init__(self, llm, mode: str, local_model_dir=None, lora_dir=None, **kwargs):
        self.llm = llm
        self.local_model_dir = local_model_dir
        self.lora_dir = lora_dir
        self.llm_client = OpenAI(api_key="<API_KEY>", base_url="https://api2.aigcbest.top/v1")
        self.mode = mode

    def rectify(self, broken_workflow: str, error_log: str, lora_request=None) -> str:
        """
        Use LLM to fix workflow.

        Args:
            broken_workflow (str): Broken workflow script
            error_log (str): Error log during execution
            lora_request: LoRA request for fine-tuned model
        Returns:
            str: Fixed workflow script
        """
        prompt = f"""
        You are a workflow rectifier AI.

        The following Python class-based workflow failed during execution.
        Your task is to fix it based on the error log.

        Instructions:
        - Analyze the workflow source code.
        - Read the error message.
        - Fix the code accordingly.
        - Return ONLY the corrected Python code, without explanation.

        --- Workflow Template ---
        {workflow_template}

        --- Broken Workflow ---
        {broken_workflow}

        --- Error Log ---
        {error_log}

        """
        fixed_code = self.get_response(prompt, self.mode, lora_request)
        
        return fixed_code

    def get_response(self, prompt, mode: str, lora_request=None):
        if mode == "local":
            sampling_params = SamplingParams(
                temperature=0.3,
                top_p=0.95,
                max_tokens=1000,
                stop=["</graph>"]
            )
            output = self.llm.generate([prompt], sampling_params, lora_request=lora_request)
            return output[0].outputs[0].text
        else:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
            )
            return response.choices[0].message.content
        
    
def main():
    broken_workflow = '''
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
            analysis = await self.custom(instruct="Can you analyze this question and provide relevant information from the context?")
            final_answer = await self.sc_ensemble(solutions=[analysis])
            return {"solution": final_answer}
    </graph>
    '''
    error_log = '''
    Custom.__call__() got an unexpected keyword argument 'instruct'
    '''
    workflow_rectifier = WorkflowRectifier(None, "remote")
    fixed_workflow = workflow_rectifier.rectify(broken_workflow, error_log)
    print("Fixed workflow:")
    print(fixed_workflow)

if __name__ == "__main__":
    main()
