from typing import Any, List

from ScoreFlow.scripts.NQ.operator_an import (
    GenerateOp,
    ScEnsembleOp,
    AnswerGenerateOp,
    ReviewOp,
)
from ScoreFlow.scripts.NQ.op_prompt import (
    SC_ENSEMBLE_PROMPT,
    SC_ENSEMBLE_PROCESS_PROMPT,
    REVIEW_PROMPT,
    ANSWER_GENERATION_PROMPT,
)

from ScoreFlow.scripts.HotpotQA.operator import Operator as OperatorBase


class Operator(OperatorBase):
    pass


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
        if isinstance(self.problem, dict):
            question = self.problem.get("question_text", "")
            document = self.problem.get("document_text", "")
            if document and len(document) > 0:
                prompt = f"{instruction}\n\nContext: {document[:2000]}\n\nQuestion: {question}"
            else:
                prompt = f"{instruction}\n\nQuestion: {question}"
        else:
            prompt = instruction + str(self.problem)

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

    async def __call__(self) -> str:

        if isinstance(self.problem, dict):
            question = self.problem.get("question_text", "")
            document = self.problem.get("document_text", "")
            if document and len(document) > 0:
                problem_text = f"Context: {document[:2000]}\n\nQuestion: {question}"
            else:
                problem_text = question
        else:
            problem_text = str(self.problem)

        prompt = ANSWER_GENERATION_PROMPT.format(input=problem_text)
        response = await self._fill_node(AnswerGenerateOp, prompt, mode="xml_fill")
        answer = response.get("answer", "")
        thought = response.get("thought", "")
        final_response = thought + "\n So we have the final results: " + answer
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
        if isinstance(self.problem, dict):
            question = self.problem.get("question_text", "")
            document = self.problem.get("document_text", "")
            if document and len(document) > 0:
                problem_text = f"Context: {document[:2000]}\n\nQuestion: {question}"
            else:
                problem_text = question
        else:
            problem_text = str(self.problem)

        prompt = REVIEW_PROMPT.format(problem=problem_text, solution=pre_solution)
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
        if isinstance(self.problem, dict):
            question = self.problem.get("question_text", "")
            document = self.problem.get("document_text", "")
            if document and len(document) > 0:
                problem_text = f"Context: {document[:2000]}\n\nQuestion: {question}"
            else:
                problem_text = question
        else:
            problem_text = str(self.problem)

        answer_mapping = {}
        solution_text = ""
        for index, solution in enumerate(solutions):
            answer_mapping[chr(65 + index)] = index
            solution_text += f"{chr(65 + index)}: \n{str(solution)}\n\n\n"
        prompt = SC_ENSEMBLE_PROMPT.format(problem=problem_text, solutions=solution_text)
        response = await self._fill_node(ScEnsembleOp, prompt, mode="xml_fill")
        answer = response.get("solution_letter", "").strip().upper()
        return solutions[answer_mapping[answer]]



