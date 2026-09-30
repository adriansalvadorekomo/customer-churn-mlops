"""Prefect flows — each flow chains one or more tasks.

The three flows required by the brief:

    - ``all``     → jobs 2-3-4-5-6 (prepare → train → evaluate → save → load),
                    plus the automation header: fetch → install → code gates.
    - ``train``   → data preparation + model training (+ save so it persists).
    - ``evaluat`` → load a saved model + evaluate it (name kept as in brief).

Run locally (no server needed)::

    uv run python -c "from src.flows import train_flow; train_flow()"

Or schedule them daily (see ``deploiement_prefect.py``).
"""

from pathlib import Path

import pandas as pd
from prefect import flow

from src.model_pipeline import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_REQUIREMENTS_PATH,
    FEATURE_COLS,
)
from src.tasks import (
    REPO_BRANCH_DEFAULT,
    REPO_URL_DEFAULT,
    evaluate_task,
    fetch_source_code_task,
    format_task,
    install_task,
    lint_task,
    load_task,
    prepare_task,
    save_task,
    security_task,
    train_task,
    unittest_task,
)

# Same demo customer as main.py / the notebook's manual predict cell.
DEMO_SAMPLE = [[850, 0, 43, 2, 125510.82, 1, 1, 1, 79084.10]]


def _maybe_fetch(fetch_code: bool, repo_url: str, branch: str) -> str | None:
    """First pipeline step (Étape 06) — clone/pull, or skip if disabled."""
    if not fetch_code:
        print("Skipping fetch-source-code (fetch_code=False).")
        return None
    return fetch_source_code_task(repo_url=repo_url, branch=branch)


def _quality_gates() -> None:
    """Code gates, always right after the dependency download (Étape 04)."""
    format_task()
    lint_task()
    security_task()
    unittest_task()


@flow(name="all")
def all_flow(
    repo_url: str = REPO_URL_DEFAULT,
    branch: str = REPO_BRANCH_DEFAULT,
    fetch_code: bool = True,
    run_install: bool = True,
    run_quality_gates: bool = True,
    requirements: str | Path = DEFAULT_REQUIREMENTS_PATH,
    data: str | Path = DEFAULT_DATA_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    test_size: float = 0.2,
    n_estimators: int = 100,
) -> dict:
    """Full pipeline: fetch → install → gates → prepare → train →
    evaluate → save → load. Returns metrics + artifact paths."""
    _maybe_fetch(fetch_code, repo_url, branch)

    if run_install:
        install_task(requirements=requirements)
    else:
        print("Skipping install-dependencies (run_install=False).")

    if run_quality_gates:
        _quality_gates()
    else:
        print("Skipping code gates (run_quality_gates=False).")

    X_train, X_test, y_train, y_test = prepare_task(csv_path=data, test_size=test_size)
    model = train_task(X_train, y_train, n_estimators=n_estimators)
    metrics = evaluate_task(model, X_test, y_test)
    saved_path = save_task(model, filepath=model_path)

    # Job 6 — prove the saved artifact reloads and predicts.
    reloaded = load_task(filepath=model_path)
    demo_pred = reloaded.predict(pd.DataFrame(DEMO_SAMPLE, columns=FEATURE_COLS))
    print(f"Reloaded model demo predict → Exited={demo_pred[0]}")

    return {
        "accuracy": metrics["accuracy"],
        "confusion_matrix": metrics["confusion_matrix"].tolist(),
        "model_path": saved_path,
        "demo_exited": int(demo_pred[0]),
    }


@flow(name="train")
def train_flow(
    repo_url: str = REPO_URL_DEFAULT,
    branch: str = REPO_BRANCH_DEFAULT,
    fetch_code: bool = True,
    data: str | Path = DEFAULT_DATA_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    test_size: float = 0.2,
    n_estimators: int = 100,
) -> dict:
    """Prepare the data and train the model, then save it."""
    _maybe_fetch(fetch_code, repo_url, branch)

    X_train, X_test, y_train, _y_test = prepare_task(csv_path=data, test_size=test_size)
    model = train_task(X_train, y_train, n_estimators=n_estimators)
    saved_path = save_task(model, filepath=model_path)
    return {
        "train_shape": list(X_train.shape),
        "test_shape": list(X_test.shape),
        "model_path": saved_path,
    }


@flow(name="evaluat")
def evaluat_flow(
    repo_url: str = REPO_URL_DEFAULT,
    branch: str = REPO_BRANCH_DEFAULT,
    fetch_code: bool = True,
    data: str | Path = DEFAULT_DATA_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    test_size: float = 0.2,
) -> dict:
    """Load a saved model and evaluate it on the test split."""
    _maybe_fetch(fetch_code, repo_url, branch)

    _, X_test, _, y_test = prepare_task(csv_path=data, test_size=test_size)
    model = load_task(filepath=model_path)
    metrics = evaluate_task(model, X_test, y_test)
    return {
        "accuracy": metrics["accuracy"],
        "confusion_matrix": metrics["confusion_matrix"].tolist(),
    }
