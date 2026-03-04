# Plan: Foundry Local NPU Support + Simplification

## Problem
The prompt-optimizer is tightly coupled to Azure OpenAI (`AzureOpenAI` client, `AzureConfig`). The goal is to also support **Foundry Local** (Microsoft's on-device inference runtime, with NPU acceleration) as a backend, using the `foundry-local-sdk` for lifecycle management. Additionally, strip out the history/DB layer to simplify the app down to pure prompt refinement.

## Approach
Introduce a **backend abstraction** so the tool can talk to either Azure OpenAI or a local Foundry Local model. Use `foundry-local-sdk` to auto-start the service and load models. Add JSON robustness for smaller local models. Remove all history/DB code.

---

## Todos

### 1. `strip-history` — Remove history/DB layer
- Delete `src/prompt_optimizer/history.py`
- Remove all history imports, `_save_to_history()`, and the `history` CLI subcommand from `cli.py`
- Remove `history_db_path` from `AppConfig` in `config.py`
- Delete `prompt_history.db` if present
- Remove `test` references to history if any exist

### 2. `backend-abstraction` — Create a backend client abstraction
- Create `src/prompt_optimizer/client.py` with a base protocol/ABC `LLMClient` exposing `chat()` and `chat_json()` signatures
- Refactor `AzureClient` to implement this interface
- Create `LocalClient` that uses the standard `openai.OpenAI` pointed at the Foundry Local endpoint
- All downstream code (`analyzer.py`, `questioner.py`, `optimizer.py`) already depends on the duck-typed `AzureClient` — update type hints to use `LLMClient` instead

### 3. `foundry-local-integration` — Integrate foundry-local-sdk
**Depends on:** `backend-abstraction`
- Add `foundry-local-sdk` as an optional dependency in `pyproject.toml` (e.g., `[project.optional-dependencies] local = ["foundry-local-sdk"]`)
- In `LocalClient.__init__`, use `FoundryLocalManager` to:
  - Start the Foundry Local service if not running
  - Load the requested model (default: `phi-4-mini-reasoning` or configurable)
  - Discover the endpoint URL and api_key
- Create the `openai.OpenAI` client pointed at `manager.endpoint`

### 4. `json-robustness` — Add JSON extraction fallback for local models
**Depends on:** `backend-abstraction`
- In `LocalClient.chat_json()`, wrap the JSON parse in a fallback:
  1. Try `json.loads(raw)` directly
  2. If that fails, try extracting JSON from markdown code fences (` ```json ... ``` `)
  3. If that fails, retry the LLM call once with a stronger "return only valid JSON" system prompt
  4. If all fail, raise a clear error
- This only applies to `LocalClient`; `AzureClient` keeps the existing behavior

### 5. `config-update` — Update config for dual-backend support
**Depends on:** `backend-abstraction`
- Add a `backend` field to `AppConfig` (values: `"azure"` | `"local"`, default `"azure"`)
- Add `local_model` field to `AppConfig` (default: `"phi-4-mini-reasoning"`)
- Update `load_config()` to read these from env vars (`PROMPT_OPT_BACKEND`, `PROMPT_OPT_LOCAL_MODEL`) and/or `config.json`
- Make Azure credentials optional when backend is `"local"` (don't raise ValueError)

### 6. `cli-update` — Update CLI for backend selection
**Depends on:** `config-update`, `foundry-local-integration`
- Add `--backend` / `-b` global argument to the CLI (`azure` or `local`)
- Add `--model` / `-m` argument for specifying the local model alias
- Update `_get_client_and_optimizer()` to instantiate the correct client based on backend choice
- Show which backend/model is being used in the startup banner

### 7. `update-tests` — Update tests for new architecture
**Depends on:** all above
- Remove history-related test code
- Update existing tests to use `LLMClient` protocol instead of `AzureClient`
- Add basic tests for `LocalClient` (mocked, no real Foundry needed)
- Add tests for JSON extraction fallback logic
- Ensure all existing analyzer/questioner/optimizer tests still pass

### 8. `update-deps-and-docs` — Update dependencies and README
**Depends on:** all above
- Update `pyproject.toml` with new optional dependency group
- Update `README.md` with:
  - Foundry Local setup instructions
  - New CLI flags (`--backend local`, `--model`)
  - Updated architecture description

---

## Key Design Decisions

- **`openai.OpenAI` vs `AzureOpenAI`**: Foundry Local exposes an OpenAI-compatible API, so `LocalClient` uses the standard `openai.OpenAI` class (not `AzureOpenAI`). Same SDK, different constructor.
- **`foundry-local-sdk` is optional**: Users who only use Azure don't need to install it. Guard the import with a try/except and give a helpful error.
- **JSON mode may not be supported by all local models**: The `response_format={"type": "json_object"}` parameter may not work on all Foundry Local models. `LocalClient` should attempt it but fall back gracefully.
- **Model selection**: Default to a model known to work on NPU (e.g., `phi-4-mini-reasoning`), but let the user override via `--model` or config.

## Notes
- The Foundry Local service auto-detects hardware (CPU/GPU/NPU) and picks the right model variant, so no NPU-specific code is needed.
- Smaller local models may need higher `max_tokens` or adjusted temperatures — we should test and tune.
