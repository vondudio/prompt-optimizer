# Prompt Optimizer

A Python CLI tool that transforms rough ideas into well-structured, effective prompts for AI assistants. Supports **Azure OpenAI** and **Foundry Local** (on-device NPU/GPU/CPU inference).

## Features

- **Interactive Q&A Mode** — Analyzes your prompt, asks targeted follow-up questions, and assembles an optimized prompt
- **One-Shot Analysis** — Paste an existing prompt and get an improved version with scoring
- **Prompt Scoring** — Rates prompts on clarity, specificity, structure, and actionability (1-10)
- **Dual Backend** — Use Azure OpenAI in the cloud or Foundry Local for private, on-device inference

## Quick Start

### 1. Install

```bash
cd prompt-optimizer
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -e ".[dev]"
```

For **Foundry Local** (on-device) support, also install:

```bash
pip install -e ".[local]"
```

### 2. Configure

#### Option A: Azure OpenAI

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

#### Option B: Foundry Local

No credentials needed — Foundry Local runs entirely on your machine. Install the [Foundry Local runtime](https://github.com/microsoft/foundry-local), then:

```bash
# Set the backend via environment variable...
export PROMPT_OPT_BACKEND=local

# ...or pass it on the command line
prompt-optimizer --backend local optimize
```

### 3. Run

```bash
# Interactive mode (default) — Azure backend
prompt-optimizer optimize

# One-shot analysis — Azure backend
prompt-optimizer analyze

# Interactive mode — Foundry Local backend
prompt-optimizer --backend local optimize

# Foundry Local with a specific model
prompt-optimizer --backend local --model phi-4-mini-reasoning optimize

# Or run as a module
python -m prompt_optimizer optimize
```

## Usage

### Backend Selection

| Flag | Description |
|------|-------------|
| `--backend azure` (default) | Use Azure OpenAI |
| `--backend local` / `-b local` | Use Foundry Local (on-device) |
| `--model MODEL` / `-m MODEL` | Model alias for local backend (default: `phi-4-mini-reasoning`) |

You can also set these via environment variables (`PROMPT_OPT_BACKEND`, `PROMPT_OPT_LOCAL_MODEL`) or `config.json`.

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

## Configuration

### `config.json` (optional)

Create a `config.json` in the project root for app preferences:

```json
{
  "default_mode": "interactive",
  "max_follow_up_questions": 5,
  "scoring_enabled": true,
  "backend": "azure",
  "local_model": "phi-4-mini-reasoning"
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (default: `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-10-21`) |
| `PROMPT_OPT_BACKEND` | Backend: `azure` or `local` |
| `PROMPT_OPT_LOCAL_MODEL` | Foundry Local model alias |

## Architecture

```
CLI (cli.py) → Optimizer (optimizer.py) → Analyzer / Questioner
                                          Templates (templates.py)
               ┌─────────────┐
               │  LLMClient   │  ← Protocol (client.py)
               │  (Protocol)  │
               └──────┬───────┘
                ┌─────┴──────┐
          AzureClient    LocalClient
        (azure_client.py) (local_client.py)
                             │
                       FoundryLocalManager
                       (foundry-local-sdk)
```

- **`client.py`** defines the `LLMClient` protocol with `chat()` and `chat_json()` methods
- **`azure_client.py`** wraps the Azure OpenAI SDK (`AzureOpenAI`)
- **`local_client.py`** wraps Foundry Local via the standard `openai.OpenAI` client, with JSON extraction fallback for smaller models
- **`optimizer.py`** orchestrates the pipeline — all downstream code depends only on the `LLMClient` protocol

## Development

```bash
# Run tests
pytest

# Run a specific test file
pytest tests/test_templates.py -v
```

## License

MIT
