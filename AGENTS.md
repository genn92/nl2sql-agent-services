# AGENTS.md

NL2SQL agent (Chinese-language project: docs, comments, and SQL are in Chinese — match that). Early-stage: the FastAPI/langgraph app is still a placeholder (`app/main.py`); most real content lives in infra config and SQL.

## Tooling

- Python 3.14, managed with `uv` (`uv.lock` at root). Never use `pip`; use `uv sync` then `.venv/bin/...` or `uv run ...`.
- Lint/format only: `uv run ruff check .` and `uv run ruff format .` (configured in `pyproject.toml`, line-length 88, selects E/F/I).
- No tests, no typecheck, no CI, no `.pre-commit-config.yaml` (pre-commit is in dev deps but unconfigured). Ruff is the only verification gate.
- Git repo has no commits yet.

## Config

- Secrets live in root `.env` (gitignored; copy `.env.example`). Both the app and docker compose read this same file.
- `app/config/app_config.py` loads `.env` and `config/app_config.yaml` via `Path(__file__).parents[2]` — it only works if `app/config/` stays exactly two levels deep. Don't move/rename these files or add a nesting level.
- YAML uses OmegaConf `${oc.env:VARS}` interpolation for `MYSQL_USER`, `MYSQL_PASSWORD`, `LLM_API_KEY`; missing env vars will not error until used.

## Docker

Start everything from the repo root:

```bash
docker compose --env-file .env -f docker/docker-compose.yaml up -d
docker compose --env-file .env -f docker/docker-compose.yaml down
```

- `docker/mysql/meta.sql` and `dw.sql` auto-run ONLY when the MySQL volume is first created. To reapply schema after edits: `docker compose ... down -v`, then `up -d`.
- **Gotcha:** both SQL files `GRANT ... TO 'genn'@'%'` with `genn` hardcoded — `MYSQL_USER` in `.env` must be `genn`, or the app user won't have privileges.
- Embedding service runs the TEI CPU image pinned to `platform: linux/amd64` (emulated on Apple Silicon). The `bge-large-zh-v1.5` model (1024-dim) is committed in-repo under `docker/embedding/`.

## Schema mapping

- `mysql` DB: metadata store for the agent — `table_info`, `column_info`, `metric_info`, `column_metric` (table/column/metric catalogs).
- `dw` DB: the analysis data warehouse — `dim_region`, `dim_customer`, `dim_product`, `dim_date`, `fact_order`.