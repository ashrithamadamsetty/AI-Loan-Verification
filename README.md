# AI Loan Verification — Local Gemini Edition

A local-first loan document verification application that keeps **FastAPI as the backend API framework**, with a React dashboard, OCR/document-forensics pipeline, SQLite workflow state, local filesystem artifacts, and Google Gemini for every generative-AI operation.

The application does **not** require cloud infrastructure or cloud-provider credentials. The only external service used by the application is the Gemini API.

## Architecture

```text
React/Vite dashboard (localhost:3000)
              |
              v
FastAPI API (localhost:8000)
  |           |               |
  |           |               +-- GeminiService --> Gemini API
  |           +-- SQLite (application queues/status)
  +-- local filesystem (documents, results, GradCAM images)
              |
              v
VerificationOrchestrator
  +-- document forensic analyzer (ELA, OCR, CNN, GradCAM)
  +-- Gemini document extraction and cross-validation
  +-- deterministic Account Aggregator checks
  +-- Gemini risk and loan decision
```

### Local replacements

| Previous responsibility | Local implementation |
| --- | --- |
| Hosted object storage | `LocalStorage` rooted at `LOCAL_STORAGE_PATH` |
| Hosted application lists/status | SQLite through `LoanDatabase` |
| Hosted generative models | Google Gemini through the centralized `GeminiService` |
| Hosted logs | Python application logging to the terminal |
| Serverless workflow execution | Normal FastAPI and Python service modules |
| Managed secrets | Local `.env` file (never commit it) |

No queue or scheduler was present in the original implementation, so no Redis or cron service is required.

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer and npm
- [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- [Poppler](https://poppler.freedesktop.org/) command-line tools for PDF rasterization
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

On Ubuntu/Debian, the native OCR dependencies can typically be installed with:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

On Windows, install Tesseract and Poppler and either add them to `PATH` or configure `TESSERACT_CMD` and `POPPLER_PATH` in `.env`.

## Quick start

### Linux/macOS

```bash
./setup.sh
```

Then edit `.env`, set `GEMINI_API_KEY`, and run:

```bash
./start_app.sh
```

### Windows PowerShell

```powershell
.\setup.ps1
```

Then edit `.env`, set `GEMINI_API_KEY`, and run:

```powershell
.\start_app.ps1
```

### Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
npm --prefix frontend install
cp .env.example .env                     # Windows: Copy-Item .env.example .env
python scripts/init_local.py
```

Start the services in separate terminals:

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bash
npm --prefix frontend run dev
```

Open:

- Dashboard: <http://localhost:3000>
- API: <http://localhost:8000>
- Interactive API docs: <http://localhost:8000/docs>

## Gemini setup

1. Create an API key in [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Copy `.env.example` to `.env`.
3. Set:

   ```dotenv
   GEMINI_API_KEY=your_real_key
   GEMINI_MODEL=gemini-2.5-flash
   ```

`gemini-2.5-flash` is the default stable model because the workflow makes several structured extraction and comparison calls. Change `GEMINI_MODEL` in `.env` to switch models without modifying code.

All generative calls are centralized in `gemini_service.py`. Document extraction and cross-validation request JSON responses directly from Gemini, and the decision adapter preserves the previous callable response contract.

## Local data layout

The default local storage root is `data/documents`. Create one directory per loan/customer ID:

```text
data/documents/
└── LID12345678/
    ├── AA_data.json
    ├── payslip.pdf
    ├── offer_letter.pdf
    ├── bank_statement.pdf
    └── form16.pdf                 # optional
```

Accepted document extensions are PDF, PNG, JPG, and JPEG. The workflow recognizes files by keywords in their names:

- payslip: filename contains `payslip`
- offer letter: filename contains `offer`
- bank statement: filename contains `bank`, `account`, or `statement`
- Form 16: filename contains `form16` (optional)

After adding or removing customer folders, initialize/synchronize the SQLite records:

```bash
python scripts/init_local.py
```

The backend also discovers new customer folders when `/customers` is requested.

Generated data remains local:

```text
data/documents/LID12345678/
├── results.json
└── gradcam/
    └── <generated heatmap>.png

data/loan_verification.db
```

The `data/` contents and `.env` are ignored by Git.

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes for AI workflows | empty | Gemini Developer API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Model used by every LLM feature |
| `LOCAL_STORAGE_PATH` | No | `data/documents` | Local customer documents and artifacts |
| `SQLITE_DATABASE_PATH` | No | `data/loan_verification.db` | Local application-status database |
| `BACKEND_HOST` | No | `127.0.0.1` | FastAPI bind host |
| `BACKEND_PORT` | No | `8000` | FastAPI port |
| `CORS_ORIGINS` | No | local React/Vite ports | Comma-separated FastAPI CORS origins |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | FastAPI URL used by the frontend |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `TESSERACT_CMD` | No | executable on `PATH` | Optional full Tesseract executable path |
| `POPPLER_PATH` | No | executables on `PATH` | Optional Poppler `bin` directory |

The API can start and expose local status/result routes without a Gemini key. A key is required only when running an LLM-powered verification workflow.

## API compatibility

FastAPI remains the application server and continues to expose interactive OpenAPI documentation at `/docs` and `/redoc`. The existing UI-facing routes remain available:

- `GET /customers`
- `POST /run_workflow`
- `GET /results/{customer_id}`
- `GET /gradcam/{customer_id}/{filename}`
- `POST /send_email`
- `POST /send_sms`
- `POST /escalate`
- `POST /approve_loan`
- `GET /approved-loans`
- `GET /human-escalations`

The response property `descision_making_agent` intentionally remains misspelled to preserve the existing frontend/API contract.

Email and SMS endpoints currently record the requested action in local application logs; they do not contact an external delivery provider.

## Tests and checks

```bash
python -m pytest
python -m compileall -q . -x frontend/node_modules
npm --prefix frontend run build
```

A live end-to-end verification additionally requires sample customer documents, native OCR tools, and a valid `GEMINI_API_KEY`.

## Troubleshooting

### `GEMINI_API_KEY is not configured`

Copy `.env.example` to `.env`, add a valid key, and restart the backend.

### Tesseract is not found

Install Tesseract and ensure `tesseract` is on `PATH`, or set `TESSERACT_CMD` to the executable's full path.

### PDF page count or Poppler error

Install Poppler tools and ensure `pdftoppm` is on `PATH`, or set `POPPLER_PATH` to the Poppler binary directory.

### Customer is not shown

Ensure the customer has a folder under `LOCAL_STORAGE_PATH`, then run:

```bash
python scripts/init_local.py
```

### Reset local state

Stop the application and remove the SQLite file and generated outputs:

```bash
rm -f data/loan_verification.db
find data/documents -name results.json -delete
rm -rf data/documents/*/gradcam
python scripts/init_local.py
```
