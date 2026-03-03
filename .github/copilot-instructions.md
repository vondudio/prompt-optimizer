# Copilot Instructions — Prompt Optimizer

## Build & Test

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_templates.py -v

# Run a single test
pytest tests/test_analyzer.py::test_analyze_prompt_returns_expected_keys -v
```

There is no linter or formatter configured.

## Architecture

This is a Python CLI tool that optimizes AI prompts via Azure OpenAI. The pipeline flows:

```
CLI (cli.py) → Optimizer (optimizer.py) → Analyzer / Questioner → AzureClient (azure_client.py)
                                          Templates (templates.py)
                                          History (history.py → SQLite)
```

- **`optimizer.py`** is the orchestrator — it coordinates analysis, question generation, and prompt assembly. All other modules are specialists it delegates to.
- **`azure_client.py`** wraps the Azure OpenAI SDK. It exposes `chat()` and `chat_json()`. The latter enables JSON mode (`response_format={"type": "json_object"}`) and parses the response automatically.
- **`analyzer.py`** handles prompt analysis (gap detection, scoring) and improvement. Uses temperature 0.3 for analysis, 0.5 for improvement.
- **`questioner.py`** generates follow-up questions from detected gaps and assembles a final prompt from the user's answers.
- **`templates.py`** defines `PromptComponents` (dataclass) and `assemble_prompt()`, which builds markdown-formatted prompts in a fixed section order: Role → Context → Audience → Task → Output Format → Tone → Constraints → Examples.
- **`history.py`** persists prompt pairs to SQLite (`prompt_history.db`). IDs are 12-char hex UUIDs.
- **`config.py`** loads `.env` (Azure credentials) and optional `config.json` (app preferences) into dataclasses (`AzureConfig`, `AppConfig`).

The CLI uses `argparse` with subcommands (`optimize`, `analyze`, `history`). Interactive input uses `questionary`; output uses `rich` (panels, tables, markdown).

## Conventions

- **All LLM interactions return structured JSON.** System prompts in `analyzer.py` and `questioner.py` instruct the model to output JSON with specific schemas. Always use `chat_json()` for LLM calls that need parsed results.
- **Scoring uses 4 dimensions:** clarity, specificity, structure, actionability (1–10 each). Defined in `templates.SCORING_DIMENSIONS`.
- **Temperature is intentional:** 0.3 for deterministic tasks (analysis/scoring), 0.5 for creative tasks (questions/assembly). Preserve this distinction.
- **Tests mock `AzureClient` entirely** — no real API calls. Use `MagicMock` with `client.chat_json` as the mock target. Test files use helper factories (`_mock_client()`, `_make_optimizer()`) to reduce boilerplate.
- **History errors are silently caught** in the CLI so they never interrupt the user flow.
- **Package source lives in `src/prompt_optimizer/`** with `src`-layout. Entry point is `prompt_optimizer.cli:main`.
