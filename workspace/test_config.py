START_LINE = 1  
END_LINE = 12  

OUTPUT_DIR = "nq_test_results"

AVAILABLE_LLMS = [
    "gpt-4o-mini",
    "gpt-4o",
    "qwen/qwen-2.5-72b-instruct",
    "qwen/qwq-32b",
]

TIMEOUT = 100000

VERBOSE = True

MAX_RETRIES = 3

DATA_FILE = "data/NQ.jsonl"

NQ_PASS_F1 = 0.8

CONFIG_FILE = "config/config2.yaml"

LLM_FILL_METHOD = "implementer" 

GENERATOR_MODEL_DIR = "models/Qwen3-8B-local"
GENERATOR_LORA_DIR = "models/finetuned_generator"

IMPLEMENTER_MODEL_DIR = "models/Qwen3-8B-local"
IMPLEMENTER_LORA_DIR = "models/finetuned_implementer"

RECTIFIER_MODEL_DIR = "models/Qwen3-8B-local"
RECTIFIER_LORA_DIR = "models/finetuned_rectifier"

VLLM_HOST = "localhost"
VLLM_PORT = 8000

MAX_WORKFLOW_GENERATION_ATTEMPTS = 5
MAX_WORKFLOW_RECTIFICATION_ATTEMPTS = 3