# Plan: Google Flow API Industrial Engine

**Source**: User Request & Interactive Alignment (/grill-me)
**Selected Milestone**: Phase 1 - Architecture, Stealth RPC Driver, FastAPI Server & End-to-End Pipeline
**Complexity**: Large

---

## 1. Summary
Transform Google Flow (Google Labs / Veo 2 / Imagen 3) into an industrial REST API service. 
The architecture uses a **Hybrid Stealth Driver** combining a persistent logged-in Playwright profile (`google_flow_session/`) with direct network interception of Google Labs internal RPC/REST endpoints. 
Each generation batch creates a dedicated project on Google Flow, provides rich parameter configuration (T2V, I2V, T2I, Frames-to-Video, aspect ratios, durations, variations), performs automated polling, executes AI-curated upscaling via Google Flow's native upscaler (or Gemini QC), and downloads production-grade MP4/JPG assets directly into the StockCont pipeline.

---

## 2. Patterns to Mirror

| Category | Source File & Line | Pattern to Mirror |
| :--- | :--- | :--- |
| **Atomic File I/O** | `src/analyzer/director.py:165` | Atomic JSON writing via unique `.tmp.{pid}.json` and `Path.replace()` (ADR-02) |
| **Cryptographic Ledger** | `src/factory/prompt_queue.py:80` | SHA-256 prompt hashing for idempotency and duplicate avoidance (ADR-03) |
| **Stealth Automation** | `src/factory/stealth_profile.py:20` | User-agent spoofing, evasion flags, persistent Chromium profile context |
| **FastAPI REST Server** | `src/dashboard/app.py:1` | FastAPI async routers, CORS middleware, Pydantic request validation, Swagger docs |
| **UTF-8 Console Shield** | `main.py` | Explicit `sys.stdout.reconfigure(encoding="utf-8")` on Windows (ADR-01) |
| **Media Probing & Processing** | `src/video/video_metadata.py` | FFmpeg probe, audio stripping (`-an`), QuickTime atom metadata injection |

---

## 3. Files to Create & Modify

| File | Action | Purpose |
| :--- | :--- | :--- |
| `src/integrations/google_flow/__init__.py` | CREATE | Package initialization and public exports |
| `src/integrations/google_flow/config.py` | CREATE | Environment settings, session paths, model registries, timeout limits |
| `src/integrations/google_flow/models.py` | CREATE | Pydantic schemas for requests, responses, jobs, and project entities |
| `src/integrations/google_flow/auth_manager.py` | CREATE | Persistent Google session manager, headed 1-click login, token extraction & refresh |
| `src/integrations/google_flow/rpc_client.py` | CREATE | Intercepted RPC/REST client for Google Labs/Flow internal APIs |
| `src/integrations/google_flow/stealth_driver.py` | CREATE | Playwright browser runner with stealth flags and network interceptor hooks |
| `src/integrations/google_flow/qc_curator.py` | CREATE | Gemini Vision multimodal evaluator to select the best variation before upscaling |
| `src/integrations/google_flow/downloader.py` | CREATE | Streaming asset downloader, MP4/JPG verification, and StockCont ingestion |
| `src/integrations/google_flow/service.py` | CREATE | Orchestration service binding auth, project creation, generation, polling, and upscale |
| `src/integrations/google_flow/api_server.py` | CREATE | Standalone FastAPI service (`http://localhost:8000`) with OpenAPI `/docs` |
| `src/integrations/google_flow/cli.py` | CREATE | CLI entry point for testing and standalone batch processing |
| `main.py` | UPDATE | Add `--flow` flags to orchestrate Google Flow directly from the root CLI |
| `tests/test_google_flow_api.py` | CREATE | Pytest suite with mock RPC responses, schema validation, and pipeline integration tests |

---

## 4. Tasks Breakdown

### Task 1: Data Contracts & Models Specification (`models.py`, `config.py`)
- **Action**: Implement Pydantic schemas for all Google Flow operations:
  - `ProjectCreateRequest`, `ProjectResponse`
  - `GenerationRequest`:
    - `prompt`: str (supports 500-1000 word cinematic prompts)
    - `mode`: `"t2v"` | `"i2v"` | `"frames2v"` | `"t2i"`
    - `model`: `"veo-2.0"` | `"veo-3.0"` | `"imagen-3.0"`
    - `aspect_ratio`: `"16:9"` | `"9:16"` | `"1:1"` | `"4:3"`
    - `duration_seconds`: `5` | `8`
    - `variations_count`: `1` | `2` | `4`
    - `ingredients`: List of input image filepaths or URLs
    - `auto_upscale`: `bool` (default True)
    - `selection_strategy`: `"best_by_ai"` | `"upscale_all"` | `"first"`
    - `webhook_url`: Optional callback URL
  - `JobStatusResponse`: tracks status (`queued`, `generating`, `ready_for_review`, `upscaling`, `completed`, `failed`), progress %, previews, upscale links.
- **Mirror**: Pydantic schemas from `src/dashboard/app.py`.
- **Validate**: `pytest tests/test_google_flow_api.py -k test_models`

### Task 2: Auth Manager & Stealth Playwright Bridge (`auth_manager.py`, `stealth_profile.py`)
- **Action**: Build session manager maintaining `google_flow_session/`:
  - `ensure_authenticated()`: checks validity of stored session cookies/tokens.
  - `interactive_login()`: launches headed Chrome window for 1-time Google 2FA login if session is absent or expired.
  - `extract_session_headers()`: extracts fresh Bearer tokens, cookies (`__Secure-1PSID`, `SAPISID`), and Google Labs project headers directly from browser network events.
  - Heartbeat worker to periodically refresh token context in background.
- **Mirror**: `src/factory/stealth_profile.py` evasion techniques.
- **Validate**: Verification of session directory creation and header extraction.

### Task 3: Reverse-Engineered RPC Client (`rpc_client.py`)
- **Action**: Implement direct asynchronous HTTP client (`httpx`) using captured session headers:
  - `create_project(name, description)`: Calls Google Labs project creation endpoint.
  - `submit_generation(...)`: Sends payload for Veo 2 / Imagen 3 generation with full media parameters.
  - `poll_job(job_id)`: Checks generation progress and retrieves candidate video/image URLs.
  - `trigger_upscale(project_id, generation_id)`: Dispatches native Google Flow Upscaler.
  - Fallback to headless DOM automation if Google rotates an RPC payload signature.
- **Mirror**: Atomic error handling and retries from `src/uploader/ftp_distributor.py`.
- **Validate**: Unit tests with mocked Google Labs API responses.

### Task 4: Smart QC Curator & Asset Downloader (`qc_curator.py`, `downloader.py`)
- **Action**:
  - `qc_curator.py`: Evaluates preview frames of candidates using Gemini Vision (from `src/analyzer/director.py`) to score sharpness, lighting, and cinematic framing, choosing the #1 candidate.
  - `downloader.py`: Downloads full-res upscaled MP4 / JPG.
  - Ingestion into StockCont:
    - Saves videos into `data/final/videos/` and images into `data/final/images/`.
    - Strips audio (`-an`) for microstock agency compliance.
    - Appends metadata to `data/processed/google_flow_history.json` with SHA-256 prompt hash.
- **Mirror**: Ingestion flow from `src/video/video_metadata.py`.
- **Validate**: Integration tests verifying file saving and ledger integrity.

### Task 5: FastAPI REST Server & OpenAPI Documentation (`api_server.py`)
- **Action**: Create standalone REST API on port `8000`:
  - `POST /api/v1/auth/login` (Trigger interactive login)
  - `GET /api/v1/auth/status` (Check active session)
  - `POST /api/v1/projects` (Create project)
  - `GET /api/v1/projects` (List projects)
  - `POST /api/v1/generate` (Enqueue generation batch)
  - `GET /api/v1/jobs/{job_id}` (Poll job status)
  - `POST /api/v1/jobs/{job_id}/upscale` (Trigger upscale)
  - `GET /api/v1/jobs/{job_id}/download` (Download assets)
  - `GET /api/v1/health` (Healthcheck & quota status)
  - Integrated Swagger UI at `http://localhost:8000/docs`.
- **Mirror**: `src/dashboard/app.py` routing patterns.
- **Validate**: `pytest tests/test_google_flow_api.py -k test_endpoints`

### Task 6: CLI & Main Orchestrator Integration (`cli.py`, `main.py`)
- **Action**: Expose Google Flow commands:
  - `python main.py --flow --login` (Interactive login)
  - `python main.py --flow --generate "Cinematic prompt..." --model veo-2.0 --ratio 16:9`
  - `python main.py --flow --process-queue` (Process pending queue from `google_veo_queue.json`)
  - `python main.py --flow --serve --port 8000` (Start API server)
- **Mirror**: Argument parsing in `main.py`.
- **Validate**: CLI execution with `--help` and dry-run flag.

---

## 5. Validation Plan

```bash
# 1. Run unit and integration tests for Google Flow module
pytest tests/test_google_flow_api.py -v

# 2. Run complete repository regression suite to ensure zero breakages
pytest

# 3. Test API server startup and health endpoint
python main.py --flow --serve --port 8000 &
curl http://localhost:8000/api/v1/health
```

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Google Session Expiration** | Medium | Medium | Heartbeat worker keeps cookies warm; API returns HTTP 401 with clear prompt to run 1-click re-login. |
| **Internal RPC Payload Changes** | Low-Medium | High | Hybrid fallback: if RPC fails, `stealth_driver.py` automatically falls back to Playwright DOM automation. |
| **Google Rate Limits / Quotas** | Medium | Medium | Queue manager throttles concurrent dispatches with exponential backoff and jitter. |
| **High GPU Video Render Latency (1-3 min)** | High | Low | Pure asynchronous architecture: jobs return immediate `job_id`, polling via `/jobs/{id}` or webhooks. |

---

## 7. Acceptance Criteria
- [ ] Pydantic models cover all generation and project parameters.
- [ ] Persistent Playwright session preserves Google login across daemon restarts.
- [ ] Direct RPC client can dispatch Veo 2 / Imagen 3 generation and trigger upscale.
- [ ] Downloaded assets are saved to `data/final/` and registered in `google_flow_history.json`.
- [ ] FastAPI server exposes complete REST API with functional Swagger docs at `/docs`.
- [ ] All new tests pass with 100% green build on the entire test suite.
