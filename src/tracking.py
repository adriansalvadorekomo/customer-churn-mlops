"""MLflow tracking — log each training run (params, accuracy, model).

Where the runs are stored comes from ``MLFLOW_TRACKING_URI``:

    - docker-compose → ``http://mlflow:5000`` (the mlflow service)
    - local default  → ``./mlruns`` (file store, no server needed)

Called by the ``train`` and ``all`` flows right after training. If the
tracking backend is unreachable the pipeline keeps going (warning printed):
serving a model must not depend on MLflow being up.
"""

import os

import mlflow
import mlflow.sklearn
from sklearn.metrics import accuracy_score

EXPERIMENT_NAME = "customer-churn"


def tracking_uri() -> str:
    """MLflow server URL, or the local ``./mlruns`` file store."""
    return os.getenv("MLFLOW_TRACKING_URI", "./mlruns")


def log_training_run(model, X_test, y_test, params: dict) -> float | None:
    """Log one MLflow run: params, test accuracy, the fitted model.

    Returns the accuracy, or ``None`` when tracking failed (warning only).
    """
    try:
        mlflow.set_tracking_uri(tracking_uri())
        mlflow.set_experiment(EXPERIMENT_NAME)
        with mlflow.start_run():
            mlflow.log_params(params)
            accuracy = float(accuracy_score(y_test, model.predict(X_test)))
            mlflow.log_metric("accuracy", accuracy)
            # MLflow 3 serializes sklearn models with skops, which refuses
            # tree internals unless trusted — and this model was created
            # in-process by our train task, never loaded from a file.
            mlflow.sklearn.log_model(
                model,
                name="model",
                skops_trusted_types=["sklearn.tree._tree.Tree"],
            )
        print(
            f"MLflow run logged in '{EXPERIMENT_NAME}' ({tracking_uri()}): "
            f"accuracy={accuracy:.4f}"
        )
        return accuracy
    except Exception as exc:  # noqa: BLE001 — tracking must never break training
        print(f"WARNING: MLflow logging failed, training continues: {exc!r}")
        return None
