# face-analyzer

A learning project for the [Strands Agents](https://github.com/strands-agents/sdk-python) framework. Vision agents evaluate images from `input_images/` against a rubric, store results in OpenSearch, and a final selection agent picks the top images.

---

## Dev loop

The project is built in three rounds — you implement each one yourself.

### Round 1 — Build the grading pipeline

**Goal:** agents evaluate every image and write scores to OpenSearch.

1. **Define your rubric** — `configs/rubric.py`
   - Add `Criterion` entries (name, label, weight, description)
   - Run `python configs/rubric.py` to preview the rubric text

2. **Wire the OpenSearch client** — `data_store/opensearch_client.py`
   - `ensure_index()` creates the index + mapping on first run
   - `index_evaluation()` writes one document per image
   - Run `python data_store/opensearch_client.py` to test the connection

3. **Implement the grading agent** — `agents/grading_agent.py`
   - Paste your rubric text into `system_prompt`
   - Replace the `save_evaluation()` stub body with a call to `index_evaluation()`
   - Run `python agents/grading_agent.py` to smoke-test against ollama

4. **Wire it all together** — `main.py`
   - Call `list_images()` → loop (or run in parallel with `ThreadPoolExecutor`) → `grading_agent(...)`
   - Run `python main.py`

### Round 2 — Observe the memory store

**Goal:** explore the evaluations you stored.

- Open **OpenSearch Dashboards** at `http://localhost:5601`
- Stack Management → Index Patterns → create pattern `image_evaluations`, time field `evaluated_at`
- Discover tab: browse raw documents
- Visualize: bar chart of `total_score`, breakdown by criterion

### Round 3 — Build the selection agent

**Goal:** a final agent reads all evaluations and selects the best images.

- Query OpenSearch for the top-N documents by `total_score`
- Build a new `Agent` in `agents/` that reasons over the aggregated scores
- Output the ranked list (and optionally copy/link the top images)

---

## Setup

### Prerequisites

- Python 3.13 (managed by `mise` — run `mise install`)
- [ollama](https://ollama.com) running locally with a vision model pulled:
  ```bash
  ollama pull qwen3.5:9b
  ```
- Docker + Docker Compose (for OpenSearch/Dashboards/Logstash)

### First-time setup

```bash
cp .env.example .env          # edit OLLAMA_MODEL etc. if needed
source .venv/bin/activate
pip install -r requirements.txt
```

### Start infrastructure

```bash
docker compose up opensearch opensearch-dashboards logstash -d
```

Services:
| URL | What |
|---|---|
| `http://localhost:9200` | OpenSearch API |
| `http://localhost:5601` | OpenSearch Dashboards |

### Run the app

```bash
python main.py
```

---

## How Strands Agents works

```python
from strands import Agent, tool
from strands.models.ollama import OllamaModel

model = OllamaModel(host="http://localhost:11434", model_id="qwen3.5:9b")

@tool
def my_tool(param: str) -> str:
    """The docstring is what the LLM reads to decide when to call this."""
    return "result"

agent = Agent(model=model, tools=[my_tool], system_prompt="Your role...")
result = agent("Your prompt")   # str(result) for the text response
```

When the agent runs it reasons, optionally calls your `@tool` functions, feeds results back to the model, and returns when done. Tools are how the agent writes to OpenSearch, reads files, or does anything outside of pure text reasoning.

### Parallel agents pattern

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def evaluate_one(image_path):
    # each call is independent — safe to run in parallel
    result = grading_agent(f"Evaluate {image_path} ...")
    return image_path, result

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(evaluate_one, p): p for p in images}
    for future in as_completed(futures):
        path, result = future.result()
```

Start with `max_workers=4` and tune down if ollama runs out of VRAM.

---

## Environment variables

All config is in `.env` (local dev) — copy from `.env.example`.

| Variable           | Default                  | Notes                               |
| ------------------ | ------------------------ | ----------------------------------- |
| `OLLAMA_BASE_URL`  | `http://localhost:11434` | ollama runs on host, not in Docker  |
| `OLLAMA_MODEL`     | `qwen3.5:9b`             | swap without code changes           |
| `OPENSEARCH_URL`   | `http://localhost:9200`  | use `opensearch:9200` inside Docker |
| `OPENSEARCH_INDEX` | `image_evaluations`      |                                     |
| `INPUT_IMAGES_DIR` | `./input_images`         |                                     |

---

## Stack

| Component                                                      | Role                           |
| -------------------------------------------------------------- | ------------------------------ |
| [Strands Agents](https://github.com/strands-agents/sdk-python) | Agent framework                |
| [ollama](https://ollama.com) (`qwen3.5:9b`)                    | Local vision LLM               |
| OpenSearch 3.6                                                 | Evaluation document store      |
| OpenSearch Dashboards 3.6                                      | Visualization / review         |
| Logstash                                                       | App log ingestion → OpenSearch |
