# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development commands

```bash
# Environment setup
cp .env.example .env          # first-time setup
uv venv                       # creates .venv
uv pip install -r requirements.txt

# Run the app
python main.py

# Smoke-test individual modules (each file has an __main__ block)
python agents/grading_agent.py          # verifies ollama reachability
python data_store/opensearch_client.py  # verifies OpenSearch connection
python utils/image_utils.py             # lists images found in INPUT_IMAGES_DIR
python configs/rubric.py                # prints the current rubric

# Infrastructure (OpenSearch + Dashboards + Logstash)
docker compose up opensearch opensearch-dashboards logstash -d
docker compose down

# Full stack (adds Python app container)
docker compose --env-file .env.docker --profile full up -d
```

## Architecture

This project is a learning scaffold for the [Strands Agents](https://github.com/strands-agents/sdk-python) framework. The intended flow is:

```
input_images/ → grading agents → OpenSearch → OpenSearch Dashboards
```

**Iteration roadmap** (the user implements each round):
- **Round 1** — Define rubric → build grading agents → write evaluations to OpenSearch
- **Round 2** — Observe/query the evaluation store via Dashboards (`localhost:5601`)
- **Round 3** — Build a selection agent that reads all evaluations and ranks images

### Key modules

| File | Purpose |
|---|---|
| `configs/rubric.py` | `Criterion` dataclass + `RUBRIC` list. `rubric_text()` generates the system-prompt block. |
| `agents/grading_agent.py` | Strands `Agent` definition. `OllamaModel` + `@tool save_evaluation`. |
| `data_store/opensearch_client.py` | `ensure_index()` and `index_evaluation()` — the write path to OpenSearch. |
| `utils/image_utils.py` | `list_images()`, `load_image_base64()`, `image_media_type()`. |
| `main.py` | Entry point — wire the above together here. |

### Strands Agents pattern

```python
from strands import Agent, tool
from strands.models.ollama import OllamaModel

model = OllamaModel(host="http://localhost:11434", model_id="qwen3-vl:8b")

@tool
def my_tool(param: str) -> str:
    """Docstring becomes the tool's LLM-visible description — write it clearly."""
    return "result"

agent = Agent(model=model, tools=[my_tool], system_prompt="...")
result = agent("prompt")   # returns AgentResult; str(result) for text
```

The `ollama` Python package must be installed alongside `strands-agents` — it is not pulled in automatically.

### Parallel agents

Use `concurrent.futures.ThreadPoolExecutor` for the ~1 800-image workload. Start with `max_workers=2–4` to avoid exhausting GPU VRAM (RTX 5090 Laptop, 24 GB). Each worker gets its own agent instance.

### OpenSearch document schema

```json
{
  "image_id": "photo_001.jpg",
  "image_path": "./input_images/photo_001.jpg",
  "rubric_version": "v0.1",
  "scores": { "<criterion_name>": 0.0 },
  "total_score": 0.0,
  "agent_id": "grading_agent",
  "evaluated_at": "<ISO-8601>",
  "raw_response": "..."
}
```

Criterion keys in `scores` must match `Criterion.name` values in `configs/rubric.py`. `total_score` is computed as the mean of all criterion scores in `index_evaluation()`.

### Infrastructure

- **OpenSearch 3.6** — single-node, security disabled, port `9200`
- **OpenSearch Dashboards 3.6** — `localhost:5601`; create index pattern `image_evaluations` on first use
- **Logstash** — reads `./logs/*.log`, writes to `app-logs-YYYY.MM.dd` index
- **ollama** — runs natively on the host (GPU access); not in Docker

### Environment variables

All config lives in `.env` (local dev) or `.env.docker` (containerised). Key vars:

```
OLLAMA_BASE_URL   default http://localhost:11434
OLLAMA_MODEL      default qwen3-vl:8b
OPENSEARCH_URL    default http://localhost:9200
OPENSEARCH_INDEX  default image_evaluations
INPUT_IMAGES_DIR  default ./input_images
```
