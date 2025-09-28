PYTHON_START = '''import asyncio
from typing import Literal
import ScoreFlow.scripts.HumanEval.operator as operator
'''

PYTHON_END = '''

    async def __call__(self):
        TIMEOUT = {time}
        return await asyncio.wait_for(self.run_workflow(), timeout=TIMEOUT)'''


START_PORMPT = '''You objective is to output a workflow graph WITH llm placeholders, based on the following template (but you must modify it):

<graph>
class Workflow:
    def __init__(
        self,
        problem
    ) -> None:
        self.problem = problem
        # IMPORTANT: Each operator MUST be initialized with a model placeholder string "llm_symbol"
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

We have the task input as follow. But your output graph can not contain any specific information of the give task.
TASK: '''


END_PROMPT = '''

You need to notice:

**Ensure your graph is based on the given template and is correct to avoid runtime failures.** Do NOT import the modules operator; they have already been automatically imported. Ensure that all the prompts required by the current graph are included. Exclude any other prompts. The generated prompt must not contain any placeholders except the required string "llm_symbol" in operator constructors. Do not load the operators not provided.

**Introducing multiple operators at appropriate points can enhance performance.** Consider Python's loops (for, the iteration number MUST <= 3) to generate multiple solutions to ensemble. Consider logical and control flow (IF-ELSE, loops) for a more enhanced graphical representation.

**The graph complexity may corelate with the task complexity.** The graph complexity must < 7. Considering information loss, complex graphs may yield better results, but insufficient information transmission can omit the solution.

**As for the instruction prompt for operators. Your instruction prompt should focus on encouraging agent to think step by step. Do not ask agent to generate multiple (a few, some, etc) answers in one operator's instruction. Also note that different agents are independent, so do not use prompts like "generate another/alternative/different answer", "generate the first/second answer", etc.**

**Your output graph can not contain any specific information of the given task due to project requirement. All the information of this task will be given as input "problem" (self.problem) and other agents will execute this workflow.**

Only output the optimized graph (remember to add <graph> and </graph>, and the output can not contain any information of the given task).

Here is the graph without any task information: '''


TEMP_AVOID = '''class Workflow:
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
        
        return solution'''


""


TEST_PROMPT = {"task_id": "HumanEval/2025", "prompt": "\n\ndef my_sum(a: int, b: int) -> int:\n    \"\"\" Write a function to add two int numbers.", "entry_point": "my_sum", "canonical_solution": "    return a+b\n", "test": "\n\ndef check(candidate):\n    assert candidate(1, 2) == 3\n"}

NO_EXCEPTION_LIST = ['''.split(' ')''', '''int(''']

TIME_LIMIT_TEST = 120
TIME_LIMIT = 240
sim_threshold = 1.1

