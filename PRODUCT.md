# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Astro + Tailwind CSS, static build served by nginx in Docker (client-side
fetch to the FastAPI backend; no server runtime).

## Users

*(Inferred from the brief — labeled assumption.)* The primary user is the
engineer/analyst evaluating this workshop project: comfortable with APIs but
willing to skip Swagger when a faster surface exists. Secondary: anyone the
project is demoed to (reviewers, classmates, recruiters) who needs to see the
model working in seconds without reading code.

## Product Purpose

A prediction console for the customer-churn model: enter one customer's
profile, get the churn verdict from the FastAPI backend, keep a local history
of predictions, and read the model's real evaluation metrics. Success means
a stranger can go from opening the page to a defensible prediction in under
a minute, and a technical reviewer finds every number traceable.

## Positioning

Front end of a fully self-hosted MLOps stack: notebook → pipeline → API →
UI, with Prefect orchestration and MLflow tracking in the same docker
compose. Nothing here fakes data or calls a third-party service.

## Operating Context

Runs locally via `docker compose up` (frontend :4321, API :8000, Prefect
:4200, MLflow :5000) or as separate dev servers (`astro dev`, `uvicorn`).
Screens are viewed on laptops andphones; the prediction form is the entry
surface, metrics is the evidence surface.

## Capabilities and Constraints

- 9-field customer form (Gender as a Female/Male control, mapped to 0/1);
  all fields validated before the API call.
- Verdict card: stays / leaves, with the model's prediction.
- Prediction history in `localStorage` (no accounts, no server storage).
- Model metrics page: verified run only — 85.55% accuracy,
  confusion matrix [[1535, 50], [239, 176]], per-class precision/recall.
- Backend contract is fixed: `POST /predict` takes the 9 preprocessed
  numeric fields, returns `{"exited": 0|1}`; `GET /health` → `{"status":"ok"}`.
- No authentication (workshop scope), no data leaves the browser except the
  single prediction request.
- API base configured by `PUBLIC_API_URL` at build time.

## Brand Commitments

Project name "Customer Churn MLOps" as used by the repo. Bilingual reality
accepted: docs are French, product surfaces English (matches repo).

## Evidence on Hand

- Real trained artifact: `models/classifier.joblib` (RandomForest, 100 trees,
  `random_state=42`), accuracy 85.55% on the 2,000-row holdout.
- Classification report: class 0 → P 0.87 / R 0.97 (support 1585); class 1 →
  P 0.78 / R 0.42 (support 415). Dataset imbalance 79.6/20.4 must be stated
  honestly wherever recall is shown.
- Demo customer (row from dataset) with known outcome for manual checks.
- No testimonials, customers, or benchmarks exist; none may be invented.

## Product Principles

1. The verdict is the page: one glance answers "will this customer leave?".
2. Domain words first, model words second — no one needs `FEATURE_COLS` to
   use it; engineers can still find the raw contract.
3. Every displayed number must come from a real run in this repo.
4. Honest about weakness: imbalance and churner recall are stated, not buried.
5. The stack is the story: backend, orchestration, and tracking are visible,
   reachable products of the same demo.

## Accessibility & Inclusion

Keyboard-operable form and navigation, visible focus, WCAG AA contrast for
text, form errors announced as text (not color alone). No product-specific
standard was established beyond this.
