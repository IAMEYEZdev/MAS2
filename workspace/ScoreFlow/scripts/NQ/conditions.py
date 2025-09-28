PYTHON_START = '''import asyncio
from typing import Literal
import ScoreFlow.scripts.NQ.operator as operator
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
        self.custom = operator.Custom("llm_symbol", self.problem)
        self.sc_ensemble = operator.ScEnsemble("llm_symbol", self.problem)
        self.answer_generate = operator.AnswerGenerate("llm_symbol", self.problem)
        self.review = operator.Review("llm_symbol", self.problem)

    async def run_workflow(self):
        """
        This is a workflow graph.
        """
        solution = await self.answer_generate()

        return solution
</graph>


Here's an introduction to operators you can use: (these are all you can use, do not create new operators)
1. Custom:
Usage: Generates anything based on fixed input problem and modifiable instruction.
Format MUST follow: custom(instruction: str) -> str
2. AnswerGenerate:
Usage: Directly generate answer (including thought) to the given problem.
Format MUST follow: answer_generate() -> str
3. ScEnsemble:
Usage: Evaluate every solutions, then select the best solution in the solution list.
Format MUST follow: sc_ensemble(solutions: List[str]) -> str
4. Review:
Usage: Given previous solution, Review operator reviews the previous solution to regenerate the solution.
Format MUST follow: review(pre_solution: str) -> str


We have the problem input as follow. But your output graph can not contain any specific information of the this problem.
Question: '''

END_PROMPT = '''

You need to notice:

Ensure your graph is based on the given template and is correct to avoid runtime failures. Do NOT import the modules operator; they have already been automatically imported. Do not load the operators not provided.

Introducing multiple operators at appropriate points can enhance performance. Consider Python's loops (for, list comprehensions) to generate multiple solutions to ensemble.

Every operator(agent)'s output should contribute to the final return output, otherwise, do not use them.

The graph complexity must between 3 and 8.

Your output graph must be optimized and different from the given template graph. Do not output graph without modification!

Your output graph can not contain any information of the given problem due to project requirement. All the information of this problem will be given as input "problem" (self.problem) and other agents will execute this workflow.

Only output the optimized graph (remember to add <graph> and </graph>, and the output can not contain any information of the given problem).

Ensure each operator is initialized with the placeholder string "llm_symbol" as the first argument, so that another system can fill concrete models later.

Here is the optimized graph without any problem information: '''


TEMP_AVOID = '''class Workflow:
    def __init__(
        self,
        problem
    ) -> None:
        self.problem = problem
        self.custom = operator.Custom("llm_symbol", self.problem)
        self.sc_ensemble = operator.ScEnsemble("llm_symbol", self.problem)
        self.answer_generate = operator.AnswerGenerate("llm_symbol", self.problem)
        self.review = operator.Review("llm_symbol", self.problem)

    async def run_workflow(self):
        """
        This is a workflow graph.
        """
        solution = await self.answer_generate()

        return solution'''


TEST_PROMPT = "What is the answer?"

NO_EXCEPTION_LIST = ['''.split(' ')''', '''int(''']

TIME_LIMIT_TEST = 60
TIME_LIMIT = 1000
sim_threshold = 0.75


