# Prompt Optimizer

A Python CLI tool that transforms rough ideas into well-structured, effective prompts for AI assistants. Powered by Azure OpenAI.

## Features

- **Interactive Q&A Mode** — Analyzes your prompt, asks targeted follow-up questions, and assembles an optimized prompt
- **One-Shot Analysis** — Paste an existing prompt and get an improved version with scoring
- **Batch Analysis** — Analyze multiple prompts from a file with JSON or Markdown export
- **Prompt Comparison** — Compare two prompts side-by-side with scored analysis
- **Prompt Scoring** — Rates prompts on clarity, specificity, structure, and actionability (1-10)
- **Prompt History** — Save, search, and re-use past optimized prompts (SQLite)

## Quick Start

### 1. Install

```bash
cd prompt-optimizer
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -e ".[dev]"
```

### 2. Configure Azure OpenAI

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21
```

### 3. Run

```bash
# Interactive mode (default)
prompt-optimizer optimize

# One-shot analysis
prompt-optimizer analyze

# Compare two prompts
prompt-optimizer compare --prompt1 "first prompt" --prompt2 "second prompt"

# Or run as a module
python -m prompt_optimizer optimize
python -m prompt_optimizer analyze
```

## Usage

### Interactive Mode (`optimize`)

1. Enter your rough prompt idea
2. The tool analyzes it and identifies gaps (missing context, vague intent, etc.)
3. Answer targeted follow-up questions
4. Get a polished, optimized prompt — scored and ready to copy

```
$ prompt-optimizer optimize

🚀 Prompt Optimizer — Interactive Mode

? Enter your rough prompt idea: write me a blog post about python

Initial Analysis
  Summary: Request to write a blog post about Python
  Gaps found: missing role, no audience, no format, no constraints

I have 4 question(s) to help refine your prompt:

? What role should the AI assume?
  › A senior Python developer and technical blogger
? Who is the target audience?
  › Intermediate developers learning Python
...

╭── Optimized Prompt ─────────────────────────────────────────╮
│ You are a senior Python developer and technical blogger.     │
│                                                              │
│ **Context:** ...                                             │
│ **Task:** Write a blog post about Python...                  │
│ **Output Format:** Markdown, 800-1200 words...               │
│ **Audience:** Intermediate developers...                     │
╰──────────────────────────────────────────────────────────────╯
```

### One-Shot Mode (`analyze`)

Paste an existing prompt and get an improved version with a before/after comparison.

```
$ prompt-optimizer analyze

🔍 Prompt Optimizer — One-Shot Analysis

? Paste your prompt to optimize: <your prompt here>

┌─ Original Scores ──────┐
│ Clarity       5/10     │
│ Specificity   3/10     │
│ Structure     4/10     │
│ Actionability 6/10     │
└────────────────────────┘

Changes Made:
  ✓ Added clear role definition
  ✓ Specified output format
  ✓ Added constraints and boundaries

╭── Optimized Prompt ──╮
│ ...                   │
╰──────────────────────╯
```

#### Batch Analysis & Export

Analyze multiple prompts from a file and export the results:

```bash
# Input: JSON array or one prompt per line
prompt-optimizer analyze --input prompts.txt --output results.md

# Export as JSON
prompt-optimizer analyze -i prompts.json -o results.json
```

Supported input formats:
- **JSON array** — `["prompt one", "prompt two", ...]`
- **Line-delimited** — one prompt per line in a plain text file

Supported output formats:
- **`.json`** — structured JSON with scores, changes, and improved prompts
- **`.md`** — formatted Markdown report

### History Management

```bash
# List recent prompts
prompt-optimizer history list

# Search history
prompt-optimizer history search "python"

# View a specific entry
prompt-optimizer history view abc123def456

# Delete an entry
prompt-optimizer history delete abc123def456
```

### Compare Mode (`compare`)

Compare two prompts side-by-side with scored analysis:

```bash
# Inline prompts
prompt-optimizer compare --prompt1 "Write me a blog post" --prompt2 "You are a tech blogger. Write a 1000-word post about Python async patterns for intermediate developers."

# From files
prompt-optimizer compare -p1 prompt_v1.txt -p2 prompt_v2.txt
```

The tool analyzes both prompts independently and displays a comparison table showing per-dimension scores (clarity, specificity, structure, actionability) with a winner for each dimension and an overall total.

## Configuration

### `config.json` (optional)

Create a `config.json` in the project root for app preferences:

```json
{
  "default_mode": "interactive",
  "history_db_path": "prompt_history.db",
  "max_follow_up_questions": 5,
  "scoring_enabled": true
}
```

## How It Works

The optimizer follows a structured approach based on prompt engineering best practices:

1. **Analysis** — Uses Azure OpenAI to evaluate your prompt and identify gaps
2. **Questioning** — Generates targeted questions to fill missing elements
3. **Assembly** — Combines your answers into a structured prompt following the pattern:
   - **Role** → Who should the AI be?
   - **Context** → What background is needed?
   - **Task** → What exactly needs to be done?
   - **Format** → What should the output look like?
   - **Constraints** → What are the boundaries?
   - **Examples** → Any reference examples?

### Architecture

```
CLI (cli.py) → Optimizer (optimizer.py) → Analyzer (analyzer.py)
                                        → Questioner (questioner.py)
                                        → Templates (templates.py)
                                        → Schemas (schemas.py)
               LLMClient (client.py) ←── AzureClient (azure_client.py)
               History (history.py → SQLite)
```

- **`client.py`** defines the `LLMClient` protocol — the backend interface exposing `chat()` and `chat_json()`.
- **`azure_client.py`** implements `LLMClient` for Azure OpenAI.
- **`optimizer.py`** orchestrates the pipeline — delegates analysis, question generation, and prompt assembly to specialist modules.
- **`schemas.py`** defines Pydantic models (`AnalysisResult`, `ImprovementResult`, `Question`, etc.) for validating structured LLM responses.
- **`templates.py`** handles prompt assembly in a fixed section order: Role → Context → Audience → Task → Output Format → Tone → Constraints → Examples.
- **`history.py`** persists prompt pairs to a local SQLite database.

## Development

```bash
# Run tests
pytest

# Run a specific test file
pytest tests/test_templates.py -v
```

## License

MIT
