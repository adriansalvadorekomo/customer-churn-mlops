"""Prefect tasks — one @task per pipeline job.

Pure logic lives in ``model_pipeline.py`` (importable and unit-testable
WITHOUT Prefect). This module only adds orchestration: retries, run names
and visibility in the Prefect UI.

Job order (see ``flows.py``):
    fetch → install → format → lint → security → tests →
    prepare → train → evaluate → save → load
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

from prefect import task

from src.model_pipeline import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_REQUIREMENTS_PATH,
    evaluate_model,
    install_dependencies,
    load_model,
    prepare_data,
    save_model,
    train_model,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_URL_DEFAULT = "https://github.com/adriansalvadorekomo/customer-churn-mlops.git"
REPO_BRANCH_DEFAULT = "main"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_logged(cmd: list[str], step: str) -> str:
    """Run a shell command, stream its output to the flow logs, fail loudly."""
    print(f"[{step}] + {' '.join(cmd)}")
    proc = subprocess.run(
        cmd, cwd=_PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    return proc.stdout


def _module_cmd(module: str, *args: str) -> list[str]:
    """Build ``python -m <module> ...`` or raise a helpful error if missing."""
    if importlib.util.find_spec(module) is None:
        raise RuntimeError(
            f"Module '{module}' is not installed. "
            f"Run job 1 first: install_dependencies() "
            f"('pip install -r requirements.txt' / 'uv sync')."
        )
    return [sys.executable, "-m", module, *args]


# ---------------------------------------------------------------------------
# Job 0 — fetch the project (Étape 06: first pipeline step)
# ---------------------------------------------------------------------------
@task(name="fetch-source-code")
def fetch_source_code_task(
    repo_url: str = REPO_URL_DEFAULT,
    dest: str | Path = _PROJECT_ROOT,
    branch: str = REPO_BRANCH_DEFAULT,
) -> str:
    """Clone the project if missing, else pull latest (graceful offline).

    - dest has ``.git`` + an ``origin`` remote → ``git pull --ff-only``.
    - dest has ``.git`` but no remote (fresh local init) → skip with a note.
    - dest missing/empty → ``git clone --branch <branch> <url> <dest>``.

    Returns a short human-readable summary of what happened.
    """
    dest = Path(dest)
    is_repo = (dest / ".git").is_dir()

    if is_repo:
        has_origin = (
            subprocess.run(
                ["git", "-C", str(dest), "remote", "get-url", "origin"],
                capture_output=True,
                check=False,  # probe: returncode inspected, must not raise
            ).returncode
            == 0
        )
        if not has_origin:
            msg = f"No 'origin' remote in {dest}: using local checkout as-is."
            print(msg)
            return msg
        _run_logged(["git", "-C", str(dest), "pull", "--ff-only"], "fetch-source-code")
        msg = f"Pulled latest '{branch}' into {dest}."
        print(msg)
        return msg

    if dest.exists() and any(dest.iterdir()):
        raise RuntimeError(f"Cannot clone into non-empty, non-git directory: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run_logged(
        ["git", "clone", "--branch", branch, repo_url, str(dest)],
        "fetch-source-code",
    )
    msg = f"Cloned {repo_url} (branch {branch}) into {dest}."
    print(msg)
    return msg


# ---------------------------------------------------------------------------
# Job 1 — install dependencies
# ---------------------------------------------------------------------------
@task(name="install-dependencies")
def install_task(
    requirements: str | Path = DEFAULT_REQUIREMENTS_PATH,
    upgrade_pip: bool = False,
    quiet: bool = False,
) -> bool:
    """Install deps from requirements.txt (wraps ``install_dependencies``)."""
    return install_dependencies(
        requirements=requirements, upgrade_pip=upgrade_pip, quiet=quiet
    )


# ---------------------------------------------------------------------------
# Code gates — run right after the dependency download (Étape 04)
# ---------------------------------------------------------------------------
@task(name="format-code")
def format_task(
    paths: tuple[str, ...] = ("src", "tests", "main.py", "deploiement_prefect.py"),
) -> str:
    """1. Code formatting — ``ruff format`` (applies the canonical style)."""
    return _run_logged(_module_cmd("ruff", "format", *paths), "format-code")


@task(name="lint-code")
def lint_task(
    paths: tuple[str, ...] = ("src", "tests", "main.py", "deploiement_prefect.py"),
) -> str:
    """2. Code quality — ``ruff check`` (fails the flow on any violation)."""
    return _run_logged(_module_cmd("ruff", "check", *paths), "lint-code")


@task(name="scan-security")
def security_task(target: str = "src") -> str:
    """3. Code security — ``bandit`` (medium severity and above).

    ``-ll`` keeps the gate green for intentional, safe patterns used here
    (e.g. ``subprocess`` with an arg list and no ``shell=True``), while
    still catching real issues.
    """
    return _run_logged(
        _module_cmd("bandit", "-r", target, "-ll", "-q"), "scan-security"
    )


@task(name="run-unit-tests")
def unittest_task(args: tuple[str, ...] = ("-q",)) -> str:
    """4. Unit tests — ``pytest`` (example suite in ``tests/``)."""
    return _run_logged(_module_cmd("pytest", *args), "run-unit-tests")


# ---------------------------------------------------------------------------
# Jobs 2–6 — ML pipeline (thin wrappers over model_pipeline.py)
# ---------------------------------------------------------------------------
@task(name="prepare-data", retries=1)
def prepare_task(
    csv_path: str | Path = DEFAULT_DATA_PATH,
    test_size: float = 0.2,
    random_state: int = 1,
) -> tuple:
    """Job 2 — load + clean + train/test split. Returns the 4 splits."""
    X_train, X_test, y_train, y_test = prepare_data(
        csv_path=csv_path, test_size=test_size, random_state=random_state
    )
    print(f"train={X_train.shape}, test={X_test.shape}")
    return X_train, X_test, y_train, y_test


@task(name="train-model", retries=1)
def train_task(X_train, y_train, n_estimators: int = 100, random_state: int = 42):
    """Job 3 — fit the RandomForest. Returns the fitted model."""
    model = train_model(
        X_train, y_train, n_estimators=n_estimators, random_state=random_state
    )
    print(f"Trained RandomForest(n_estimators={n_estimators}).")
    return model


@task(name="evaluate-model")
def evaluate_task(model, X_test, y_test) -> dict:
    """Job 4 — accuracy + report + confusion matrix. Returns metrics dict."""
    return evaluate_model(model, X_test, y_test)


@task(name="save-model")
def save_task(model, filepath: str | Path = DEFAULT_MODEL_PATH) -> str:
    """Job 5 — persist the model with joblib. Returns the path as str."""
    return str(save_model(model, filepath))


@task(name="load-model", retries=1)
def load_task(filepath: str | Path = DEFAULT_MODEL_PATH):
    """Job 6 — reload a persisted model. Returns the deserialized model."""
    return load_model(filepath)
