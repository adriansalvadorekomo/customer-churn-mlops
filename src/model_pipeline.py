"""Customer churn ML pipeline — modular version of ``notebooks/customer_churn.ipynb``.

Pipeline jobs (in order):
    1. :func:`install_dependencies` — install deps from requirements.txt
    2. :func:`prepare_data` — load CSV + LabelEncode Gender + drop cols + split
    3. :func:`train_model` — RandomForestClassifier(...).fit(...)
    4. :func:`evaluate_model` — accuracy_score / classification_report /
       confusion_matrix
    5. :func:`save_model` — joblib.dump(rf, "classifier.joblib")
    6. :func:`load_model` — joblib.load (alternative to re-training)

Serving (not a training job, used by ``src/app.py``):
    - :func:`predict_model` — single-row inference with validation.

Notebook → module mapping:
    - job 1 has no notebook equivalent: notebooks assume the kernel already
      has the packages. The modular pipeline makes it explicit and
      reproducible (``pip install -r requirements.txt``).
    - cells load CSV + LabelEncode Gender + drop cols + train_test_split
      → :func:`prepare_data`
    - cell RandomForestClassifier(...).fit(...)
      → :func:`train_model`
    - cells accuracy_score / classification_report / confusion_matrix
      → :func:`evaluate_model`
    - cell joblib.dump(rf, "classifier.joblib")
      → :func:`save_model` / :func:`load_model`

Notes on intentional deviations from the notebook (documented, not hidden):
    1. The notebook creates a ``StandardScaler`` with ``fit_transform`` on
       BOTH train and test separately, then never uses it for training or
       prediction. That is a data-leakage bug + dead code (RandomForest does
       not need scaling anyway), so it is NOT reproduced here.
    2. The notebook calls ``df.isnull`` without parentheses (returns the bound
       method, not the check). The modular version has no such exploratory
       line.
    3. ``Geography`` is dropped like in the notebook. A real improvement would
       be OneHot-encoding it instead — flagged as TODO, default kept faithful
       so accuracy (~85.5 %) stays comparable.
    4. Dead imports (LinearSVC, LinearRegression, Lasso) were removed.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

__all__ = [  # noqa: RUF022 — job order (1→6) is pedagogical, not alphabetical
    "install_dependencies",  # 1
    "prepare_data",  # 2
    "train_model",  # 3
    "evaluate_model",  # 4
    "save_model",  # 5
    "load_model",  # 6
    "predict_model",  # serving helper for src/app.py
]

# ---------------------------------------------------------------------------
# Defaults — resolved relative to the project root (parent of ``src/``)
# so ``uv run python main.py`` works from the root and ``python src/...`` too.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = _PROJECT_ROOT / "notebooks" / "data" / "Churn_Modelling.csv"
DEFAULT_MODEL_PATH = _PROJECT_ROOT / "models" / "classifier.joblib"
DEFAULT_REQUIREMENTS_PATH = _PROJECT_ROOT / "requirements.txt"

# Columns dropped exactly like the notebook does:
#   Surname, Geography  → early drop
#   RowNumber, CustomerId → ID columns, no predictive signal
#   Exited → target column, separated into y
DROP_COLS_EARLY = ["Surname", "Geography"]
ID_COLS = ["RowNumber", "CustomerId"]
TARGET_COL = "Exited"

# Final feature order after preprocessing (used for the demo predict).
FEATURE_COLS = [
    "CreditScore",
    "Gender",
    "Age",
    "Tenure",
    "Balance",
    "NumOfProducts",
    "HasCrCard",
    "IsActiveMember",
    "EstimatedSalary",
]


def install_dependencies(
    requirements: str | Path = DEFAULT_REQUIREMENTS_PATH,
    upgrade_pip: bool = False,
    quiet: bool = False,
) -> bool:
    """Install project dependencies from a requirements file (job #1).

    Why a function for this? Notebooks silently assume the kernel already
    has pandas/sklearn/.... The modular pipeline makes the install step
    explicit, ordered first, and runnable from ``main.py`` so a fresh
    machine (pip or uv user) can bootstrap itself with one command.

    Equivalent shell:
        ``pip install -r requirements.txt``
        (uv users can instead run ``uv sync`` — same pins, see pyproject.toml).
        In a uv-managed venv (which has no ``pip`` module by default) the
        function automatically falls back to ``uv pip install``.

    Args:
        requirements: Path to the requirements file.
        upgrade_pip: If True, run ``pip install --upgrade pip`` first
            (skipped with a note inside uv-managed envs that have no pip).
        quiet: If True, pass ``-q`` for less noisy output.

    Returns:
        True once the install command exits with code 0.

    Raises:
        FileNotFoundError: If the requirements file does not exist.
        RuntimeError: If neither pip nor uv is available.
        subprocess.CalledProcessError: If the install command fails.

    Example:
        >>> install_dependencies()  # installs requirements.txt
        True
    """
    requirements = Path(requirements)
    if not requirements.is_file():
        raise FileNotFoundError(
            f"Requirements file not found: {requirements}\n"
            f"Hint: default is {DEFAULT_REQUIREMENTS_PATH}"
        )

    has_pip = (
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            check=False,  # probe: returncode inspected below, must not raise
        ).returncode
        == 0
    )
    has_uv = shutil.which("uv") is not None

    if upgrade_pip:
        if has_pip:
            print("Upgrading pip ...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
            )
        elif has_uv:
            print("Skipping pip upgrade (uv-managed env has no pip module).")
        else:
            raise RuntimeError("Cannot upgrade pip: neither pip nor uv found.")

    if has_pip:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements)]
    elif has_uv:
        # uv venvs have no pip module: install into THIS interpreter via uv.
        cmd = [
            "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "-r",
            str(requirements),
        ]
    else:
        raise RuntimeError(
            "No installer available: install pip or uv, then retry.\n"
            "pip users: https://pip.pypa.io/en/stable/installation/ | "
            "uv users: https://docs.astral.sh/uv/"
        )
    if quiet:
        cmd.append("-q")
    print(f"Installing dependencies from {requirements} ...")
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Dependencies installed.")
    return True


def prepare_data(
    csv_path: str | Path = DEFAULT_DATA_PATH,
    test_size: float = 0.2,
    random_state: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Load and preprocess the churn dataset, then train/test split it.

    Steps (mirror the notebook):
        1. ``pd.read_csv(csv_path)``
        2. ``LabelEncoder`` on ``Gender`` (Female/Male → 0/1)
        3. Drop ``Surname`` + ``Geography``
        4. Split ``X = df.drop(Exited)``, ``y = df[Exited]``,
           then drop ``RowNumber`` + ``CustomerId`` from ``X``
        5. ``train_test_split(test_size=0.2, random_state=1)``

    Args:
        csv_path: Path to ``Churn_Modelling.csv``.
        test_size: Fraction of data kept for testing.
        random_state: Seed for a reproducible split.

    Returns:
        Tuple ``(X_train, X_test, y_train, y_test)``.

    Example:
        >>> X_train, X_test, y_train, y_test = prepare_data()
    """
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {csv_path}\nHint: default is {DEFAULT_DATA_PATH}"
        )

    df = pd.read_csv(csv_path)

    # 1. Encode Gender (notebook: encoder.fit_transform(df['Gender']))
    encoder = LabelEncoder()
    df["Gender"] = encoder.fit_transform(df["Gender"])

    # 2. Drop non-predictive text column + Geography (faithful to notebook).
    # TODO(improvement): OneHot-encode Geography instead of dropping it.
    df = df.drop(DROP_COLS_EARLY, axis=1)

    # 3. Separate features / target, drop ID columns.
    y = df[TARGET_COL]
    X = df.drop([TARGET_COL], axis=1)
    X = X.drop(ID_COLS, axis=1)

    # 4. Split (same hyperparams as notebook).
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    return X_train, X_test, y_train, y_test


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_estimators: int = 100,
    random_state: int = 42,
) -> RandomForestClassifier:
    """Train a RandomForest classifier (same hyperparams as the notebook).

    Args:
        X_train: Training features from :func:`prepare_data`.
        y_train: Training labels from :func:`prepare_data`.
        n_estimators: Number of trees.
        random_state: Seed for reproducibility.

    Returns:
        The fitted ``RandomForestClassifier``.

    Example:
        >>> model = train_model(X_train, y_train)
    """
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
    model.fit(X_train, y_train)
    return model


def evaluate_model(
    model: RandomForestClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:
    """Evaluate the model and print accuracy / report / confusion matrix.

    Mirrors the notebook cells using ``accuracy_score`` and
    ``confusion_matrix`` (+ adds ``classification_report``, which the
    notebook imported but never printed).

    Args:
        model: A fitted classifier with a ``.predict`` method.
        X_test: Test features from :func:`prepare_data`.
        y_test: Test labels from :func:`prepare_data`.

    Returns:
        Dict with keys ``accuracy`` (float 0-1), ``report`` (dict),
        ``confusion_matrix`` (2x2 array) and ``y_pred`` (array).

    Example:
        >>> metrics = evaluate_model(model, X_test, y_test)
        >>> print(metrics["accuracy"])
    """
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    matrix = confusion_matrix(y_test, y_pred)

    print(f"Accuracy score: {accuracy * 100:.2f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred))
    print("Confusion matrix:")
    print(matrix)

    return {
        "accuracy": accuracy,
        "report": report,
        "confusion_matrix": matrix,
        "y_pred": y_pred,
    }


def save_model(
    model: RandomForestClassifier,
    filepath: str | Path = DEFAULT_MODEL_PATH,
) -> Path:
    """Persist a trained model with joblib.

    Replaces the notebook's manual ``open(..., "wb")`` / ``close()``
    pattern with a safer one-liner that also creates parent folders.

    Args:
        model: The fitted model to save.
        filepath: Destination ``.joblib`` file.

    Returns:
        The resolved path the model was written to.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, filepath)
    print(f"Model saved to {filepath}")
    return filepath


def load_model(filepath: str | Path = DEFAULT_MODEL_PATH) -> RandomForestClassifier:
    """Load a joblib-persisted model from disk.

    Args:
        filepath: Path to a ``.joblib`` file written by :func:`save_model`.

    Returns:
        The deserialized classifier, ready for ``.predict()``.

    Raises:
        FileNotFoundError: If ``filepath`` does not exist.
    """
    filepath = Path(filepath)
    if not filepath.is_file():
        raise FileNotFoundError(
            f"Model file not found: {filepath}\n"
            "Hint: train first with train_model() + save_model()."
        )
    model = joblib.load(filepath)
    print(f"Model loaded from {filepath}")
    return model


def predict_model(
    features: list[float] | tuple[float, ...],
    model_path: str | Path = DEFAULT_MODEL_PATH,
    model: RandomForestClassifier | None = None,
) -> int:
    """Predict churn for ONE customer (serving helper for ``src/app.py``).

    Args:
        features: 9 numeric values in :data:`FEATURE_COLS` order
            (CreditScore, Gender, Age, Tenure, Balance, NumOfProducts,
            HasCrCard, IsActiveMember, EstimatedSalary).
            Gender is already encoded (Female=0, Male=1).
        model_path: Model file used when ``model`` is not provided.
        model: Optional pre-loaded model — lets the API load once at
            startup instead of on every request.

    Returns:
        ``1`` if the customer is predicted to exit, else ``0``.

    Raises:
        ValueError: If ``features`` does not contain exactly 9 values.

    Example:
        >>> predict_model([850, 0, 43, 2, 125510.82, 1, 1, 1, 79084.10])
        0
    """
    if len(features) != len(FEATURE_COLS):
        raise ValueError(
            f"Expected {len(FEATURE_COLS)} features in order {FEATURE_COLS}, "
            f"got {len(features)}: {list(features)}"
        )
    if model is None:
        model = load_model(model_path)
    row = pd.DataFrame([list(features)], columns=FEATURE_COLS)
    return int(model.predict(row)[0])
