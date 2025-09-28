import re
import string
from collections import Counter
from typing import Callable, List, Tuple, Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from ScoreFlow.benchmark.benchmark import BaseBenchmark
from metagpt.logs import logger


class NQBenchmark(BaseBenchmark):
    def __init__(self, name: str, file_path: str, log_path: str):
        super().__init__(name, file_path, log_path)

    def normalize_answer(self, s: str) -> str:
        def remove_articles(text):
            return re.sub(r"\b(a|an|the)\b", " ", text)

        def white_space_fix(text):
            return " ".join(text.split())

        def remove_punc(text):
            exclude = set(string.punctuation)
            return "".join(ch for ch in text if ch not in exclude)

        def lower(text):
            return text.lower()

        return white_space_fix(remove_articles(remove_punc(lower(s))))

    def extract_best_span(self, prediction: str, target: str) -> str:
        """Extract the most relevant span from prediction that matches target"""
        pred_tokens = self.normalize_answer(prediction).split()
        target_tokens = self.normalize_answer(target).split()

        if not pred_tokens or not target_tokens:
            return prediction

        target_len = len(target_tokens)
        max_overlap = 0
        best_span = prediction

        for window_size in range(target_len, min(len(pred_tokens) + 1, target_len + 10)):
            for start in range(len(pred_tokens) - window_size + 1):
                window_tokens = pred_tokens[start:start + window_size]
                common = Counter(window_tokens) & Counter(target_tokens)
                overlap = sum(common.values())

                if overlap > max_overlap:
                    max_overlap = overlap
                    best_span = " ".join(window_tokens)

        return best_span

    def calculate_f1(self, prediction_tokens: List[str], ground_truth_tokens: List[str]) -> float:
        """Calculate F1 score between two token lists"""
        if not prediction_tokens or not ground_truth_tokens:
            return 0.0

        common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
        num_same = sum(common.values())

        if num_same == 0:
            return 0.0

        precision = 1.0 * num_same / len(prediction_tokens)
        recall = 1.0 * num_same / len(ground_truth_tokens)

        if precision + recall == 0:
            return 0.0

        f1 = (2 * precision * recall) / (precision + recall)
        return f1

    def calculate_score(self, ground_truth: str, prediction: str) -> Tuple[float, str]:
        if isinstance(ground_truth, list):
            max_f1 = 0.0
            best_answer = ""
            best_extracted_span = prediction

            for answer in ground_truth:
                extracted_span = self.extract_best_span(prediction, answer)

                prediction_tokens = self.normalize_answer(extracted_span).split()
                answer_tokens = self.normalize_answer(answer).split()
                f1 = self.calculate_f1(prediction_tokens, answer_tokens)

                if f1 > max_f1:
                    max_f1 = f1
                    best_answer = answer
                    best_extracted_span = extracted_span

            return max_f1, best_extracted_span
        else:
            extracted_span = self.extract_best_span(prediction, ground_truth)

            prediction_tokens = self.normalize_answer(extracted_span).split()
            ground_truth_tokens = self.normalize_answer(ground_truth).split()
            f1 = self.calculate_f1(prediction_tokens, ground_truth_tokens)

            return f1, extracted_span

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_outputs(self, graph):
        return await graph()

    async def _filter(self, extraction, question, answer):
        return await extraction(question, answer)

    async def judge_answer(self, judger, question, model_answer, right_answer):
        return await judger(question, model_answer, right_answer)

    def get_input_text(self, problem):

        question = problem.get("question_text", "")
        document = problem.get("document_text", "")

        if document:
            return f"Context: {document}\nQuestion: {question}"
        else:
            return question

    def get_graph_input_text(self, problem):
        return problem.get("question_text", "")

    def get_problem_id(self, problem):
        return problem.get("example_id", None)

    def _first_gold(self, problem):

        gold = problem.get("answers")
        if isinstance(gold, list) and gold:
            return gold  
        elif gold:
            return [str(gold)] 
        else:
            return [""]  

    async def evaluate_problem(self, problem: dict, extraction: Optional[Callable], judger: Optional[Callable], graph: Callable) -> Tuple[str, str, str, float]:
        question = problem.get("question_text", "")
        expected_output_list = self._first_gold(problem) 
        input_text = self.get_input_text(problem)

        try:
            output = await self._generate_outputs(graph)
            if extraction is not None:
                output = await self._filter(extraction, question, output)
            if judger is None:
                score, _ = self.calculate_score(expected_output_list, output)
            else:
                first_answer = expected_output_list[0] if expected_output_list else ""
                score = await self.judge_answer(judger, question, output, first_answer)
                try:
                    score = float(score)
                except Exception:
                    normalized_output = self.normalize_answer(output)
                    score = 1.0 if any(self.normalize_answer(ans) in normalized_output for ans in expected_output_list) else 0.0

            
            gold_for_display = expected_output_list[0] if expected_output_list else ""
            return question, output, gold_for_display, score

        except Exception as e:
            logger.info(f"Maximum retries reached. Skipping this sample. Error: {e}")
            gold_for_display = expected_output_list[0] if expected_output_list else ""
            return question, str(e), gold_for_display, 0.0

    def get_result_columns(self) -> List[str]:
        return ["question", "prediction", "expected_output", "score"]


