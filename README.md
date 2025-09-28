# MAS²: Self-Generative, Self-Configuring, Self-Rectifying Multi-Agent Systems


This repository contains the official implementation for our project, **MAS²**, a dynamic, self-rectifying multi-agent framework designed to solve complex tasks with optimal cost-performance.

## 📖 Introduction

**MAS²** tackles complex problems by programmatically decomposing them into structured, executable workflows. It leverages a heterogeneous **LLM Pool** to dynamically assign the most suitable language model to each subtask. This methodology allows MAS² to achieve state-of-the-art performance while minimizing computational cost, thereby optimizing its position on the cost-performance Pareto frontier.

## ✨ Core Features

- **Self-Generative Workflow**: Automatically breaks down a high-level task into a detailed, step-by-step workflow graph.
- **Self-Configuring LLM Allocation**: Intelligently selects the best-suited LLM for each step from a diverse pool, balancing performance with cost.
- **Self-Rectifying Pipeline**: If a workflow fails during execution, the system analyzes the error, automatically attempts to correct the workflow, and re-runs the task.
- **Heterogeneous LLM Pool**: Supports a mix of different models (e.g., GPT-4o, Qwen-2.5, local models) to ensure the right tool is always used for the job.

## 🔧 Installation

We recommend using Conda to manage the environment for this project.

1. **Create and Activate Conda Environment**:

   ```
   conda create -n mas2 python=3.10
   source activate mas2
   ```

2. **Install Local MetaGPT Dependency**: The core framework relies on a modified local version of MetaGPT.

   ```
   unzip metagpt_local.zip
   cd metagpt_local
   pip install .
   cd ..
   ```

3. **Install Project Requirements**: Finally, install the remaining Python packages.

   ```
   pip install -r requirement.txt
   ```

## 🚀 Running the NQ Benchmark

The primary script for running tests is `workspace/test.py`, which is pre-configured to evaluate the framework on the Natural Questions (NQ) dataset.

#### 1. Configure Your Models

Before running, you must configure the paths to your local models in `workspace/test_config.py`. Update the following variables with the correct paths to your downloaded model weights:

```
# workspace/test_config.py

# Directory for the model that generates the initial workflow
GENERATOR_MODEL_DIR = "/path/to/your/generator_model"

# Directory for the model that implements the workflow into code
IMPLEMENTER_MODEL_DIR = "/path/to/your/implementer_model"

# Directory for the model that fixes broken workflows
RECTIFIER_MODEL_DIR = "/path/to/your/rectifier_model"
```

#### 2. Execute the Test Script

Run the test from the root directory of the project using the following command:

```
python workspace/test.py --data_file workspace/data/NQ.jsonl
```

You can also specify a range of questions to process using the `--start_line` and `--end_line` flags. This is useful for debugging or running smaller test batches.

```
# Run on the first 10 questions from the dataset
python workspace/test.py --data_file workspace/data/NQ.jsonl --start_line 1 --end_line 10
```

Results, including logs, generated workflows, and final scores, will be saved in the directory specified by the `OUTPUT_DIR` variable in `test_config.py`.

## 📁 Project Structure

```
MAS-2/
├── workspace/                  # Core operational scripts and data
│   ├── test.py                 # Main script for running benchmarks
│   ├── test_config.py          # Configuration for models, paths, and parameters
│   ├── workflow_generator.py   # Agent for generating workflows
│   ├── workflow_implementer.py # Agent for implementing workflows
│   └── workflow_rectifier.py   # Agent for fixing failed workflows
│   │
│   ├── ScoreFlow/              # Framework for workflow execution and evaluation
│   │   ├── benchmark/          # Scripts for evaluating on different benchmarks
│   │   │   └── nq.py           # NQ benchmark evaluation logic
│   │   └── scripts/            # Task-specific scripts (e.g., operators, prompts)
│   │       └── NQ/
│   │           ├── operator.py # Defines executable operations for the NQ task
│   │           └── op_prompt.py  # Contains prompts for the NQ operators
│   │
│   ├── data/
│   │   └── NQ.jsonl            # Natural Questions (NQ) benchmark dataset
│   │
│   └── config/
│       ├── config1.yaml        # Example configuration files
│       └── config2.yaml
│
├── metagpt_local/              # Local dependency based on the MetaGPT framework
│
└── requirement.txt             # Python package requirements

```

## 🙏 Acknowledgements

- We sincerely thank the authors of [ScoreFlow](https://arxiv.org/abs/2502.04306), as their work provided significant inspiration for our project.
- We also extend our heartfelt thanks to the [MetaGPT](https://github.com/geekan/MetaGPT) team for their open-source framework, which served as a valuable foundation for our implementation.

