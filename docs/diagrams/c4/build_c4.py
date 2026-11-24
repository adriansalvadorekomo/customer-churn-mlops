"""Draw the C4 diagrams of Customer Churn MLOps (docs/diagrams/c4/*.svg).

Three views, each in a light and a dark theme:
  c4-context    C4 level 1: who uses the system and what it depends on
  c4-container  C4 level 2: the compose stack, with the opt-in monitoring profile
  c4-component  C4 level 3: inside the worker, how a scheduled run is gated and recorded

Every element comes from the code at the commit it ships with: docker-compose.yml,
deploiement_prefect.py, src/flows.py, src/tasks.py, src/tracking.py, src/observability.py,
src/app.py and monitoring/. Drawing kit: c4kit.py (same engine as the Episteme diagrams).

    uv run --no-project --with fonttools --with brotli python docs/diagrams/c4/build_c4.py [--png]
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from c4kit import Box, Canvas, View, build

READOUT = [
    ("HOLDOUT ACCURACY", "85.55%"),
    ("CHURNER RECALL", "0.42 · 176/415"),
    ("TESTS", "15 pytest"),
]
COL = [32, 360, 688, 1016]  # four columns, 224 wide, 104 apart
W = 224


# ── C4 level 1 · context ───────────────────────────────────────────────────
def context_view(cv: Canvas):
    analyst = Box(32, 200, 192, 112)
    eng = Box(32, 376, 192, 112)
    system = Box(368, 184, 528, 304)
    data = Box(1040, 184, 208, 96)
    github = Box(1040, 288, 208, 96)
    hub = Box(1040, 392, 208, 96)

    cv.arrow([(analyst.r, 256), (system.x, 256)])
    cv.label([("scores customers", False), ("browser", True)], 296, 222)
    cv.arrow([(eng.r, 432), (system.x, 432)])
    cv.label(
        [("runs flows,", False), ("reads runs", False), ("browser UIs", True)], 296, 382
    )
    cv.arrow([(system.r, 232), (data.x, 232)])
    cv.label([("reads", False)], 968, 216)
    cv.arrow([(system.r, 336), (github.x, 336)])
    cv.label([("clones, pulls", False), ("git · local runs", True)], 968, 302)
    cv.arrow([(system.r, 440), (hub.x, 440)])
    cv.label([("pulls images", False)], 968, 424)

    cv.node(
        analyst,
        "person",
        "Person",
        "Analyst",
        None,
        ["Scores customers,", "reads the model report"],
        ["user"],
    )
    cv.node(
        eng,
        "person",
        "Person",
        "ML engineer",
        None,
        ["Runs the pipeline,", "watches model quality"],
        ["user"],
    )
    cv.node(
        system,
        "container",
        "Software system",
        "Customer Churn MLOps",
        "Docker Compose · 5 services + ELK profile",
        [
            "A bank-churn RandomForest made repeatable: four",
            "blocking code gates, three scheduled Prefect flows,",
            "every training run tracked in MLflow.",
            "",
            "FastAPI and a browser desk serve the model; an opt-in",
            "ELK profile shows traffic, predictions and quality.",
            "",
            "Holdout: 85.55% accuracy, churner recall 0.42.",
        ],
        ["prefect", "mlflow", "fastapi", "elasticsearch"],
        focal=True,
    )
    cv.node(
        data,
        "external",
        "Data · in the repo",
        "Churn_Modelling.csv",
        None,
        ["10,000 customers"],
        ["file"],
    )
    cv.node(
        github,
        "external",
        "External",
        "GitHub",
        None,
        ["Source for local runs"],
        ["github"],
    )
    cv.node(
        hub,
        "external",
        "External",
        "Docker Hub",
        None,
        ["twelvy1400/churn-mlops-*"],
        ["docker"],
    )

    cv.readout(READOUT, 1248, 96)
    cv.legend(
        536,
        [
            ("person", "person"),
            ("focal", "the system"),
            ("external", "external system or data"),
            ("call", "uses"),
        ],
    )


# ── C4 level 2 · containers ────────────────────────────────────────────────
def container_view(cv: Canvas):
    ra, rb, rc = 360, 552, 768
    analyst = Box(32, 168, 232, 96)
    eng = Box(840, 168, 248, 96)
    desk = Box(COL[0], ra, W, 128)
    api = Box(COL[1], ra, W, 128)
    prefect = Box(COL[2], ra, W, 128)
    mlflow = Box(COL[3], ra, W, 128)
    models = Box(COL[1], rb, W, 128)
    worker = Box(COL[2], rb, W, 128)
    data = Box(COL[3], rb, W, 128)
    filebeat = Box(COL[0], rc, W, 128)
    logstash = Box(COL[1], rc, W, 128)
    es = Box(COL[2], rc, W, 128)
    kibana = Box(COL[3], rc, W, 128)
    setup = Box(840, 944, 248, 88)

    cv.zone(
        Box(16, 312, 1240, 776),
        "CHURN MLOPS",
        "docker compose · churn-mlops",
        at="bottom",
    )
    cv.zone(
        Box(24, 728, 1224, 328), "MONITORING", "opt-in profile · ELK 9.5", at="bottom"
    )

    # people
    cv.arrow([(analyst.cx - 4, analyst.b), (analyst.cx - 4, desk.y)])
    cv.label(
        [("scores customers", False), ("browser · :4321", True)],
        analyst.cx + 8,
        300,
        "start",
    )
    cv.arrow(
        [(964, eng.b), (964, 332), (prefect.cx, 332), (prefect.cx, prefect.y)],
        head=False,
    )
    cv.arrow([(prefect.cx, 332), (prefect.cx, prefect.y)])
    cv.arrow([(964, 332), (mlflow.cx, 332), (mlflow.cx, mlflow.y)])
    cv.label(
        [("triggers flows, reads runs", False), ("browser · :4200 · :5000", True)],
        976,
        292,
        "start",
    )
    cv.arrow([(eng.r, 216), (1266, 216), (1266, 832), (kibana.r, 832)])
    cv.label([("dashboard", False), (":5601", True)], 1236, 742, "end")
    # serving
    cv.arrow([(desk.r, 408), (api.x, 408)])
    cv.label([("/predict", False), ("JSON · CORS", True)], 308, 372)
    cv.arrow([(api.cx, api.b), (api.cx, models.y)])
    cv.label([("loads at start", False), ("joblib", True)], api.cx + 12, 516, "start")
    # pipeline
    cv.arrow([(prefect.cx, worker.y), (prefect.cx, prefect.b)])
    cv.label(
        [("polls, reports", False), ("Prefect API", True)], prefect.cx - 12, 516, "end"
    )
    cv.arrow([(worker.r, 568), (964, 568), (964, 456), (mlflow.x, 456)])
    cv.label([("logs runs", False), ("MLflow REST", True)], 964, 504)
    cv.arrow([(worker.x, 616), (models.r, 616)])
    cv.label([("writes", False), ("joblib", True)], 636, 580)
    cv.arrow([(worker.r, 648), (data.x, 648)])
    cv.label([("reads", False), ("read-only", True)], 964, 612)
    # monitoring: Filebeat tails the Docker logs of the API and the worker
    cv.arrow(
        [
            (filebeat.cx, filebeat.y),
            (filebeat.cx, 712),
            (312, 712),
            (312, 456),
            (api.x, 456),
        ],
        dashed=True,
    )
    cv.arrow([(312, 712), (worker.cx, 712), (worker.cx, worker.b)], dashed=True)
    cv.label([("tails Docker logs", False), ("label churn_logs", True)], 560, 700)
    cv.arrow([(filebeat.r, 832), (logstash.x, 832)])
    cv.label([("ships", False), ("beats", True)], 308, 796)
    cv.arrow([(logstash.r, 832), (es.x, 832)])
    cv.label([("indexes", False)], 636, 816)
    cv.arrow([(kibana.x, 832), (es.r, 832)])
    cv.label([("queries", False)], 964, 816)
    cv.arrow([(868, setup.y), (868, es.b)])
    cv.label([("template", False)], 856, 928, "end")
    cv.arrow([(1060, setup.y), (1060, kibana.b)])
    cv.label([("dashboard", False)], 1072, 928, "start")
    cv.note("security off · ports on 127.0.0.1", 48, 1000)

    # elements
    cv.node(
        analyst, "person", "Person", "Analyst", None, ["Scores customers"], ["user"]
    )
    cv.node(
        eng,
        "person",
        "Person",
        "ML engineer",
        None,
        ["Runs flows, reads runs"],
        ["user"],
    )
    cv.node(
        desk,
        "container",
        "Container",
        "Churn Desk",
        "Astro · nginx · :4321",
        ["Static files; runs in the", "browser, calls the API"],
        ["astro", "nginx"],
    )
    cv.node(
        api,
        "container",
        "Container",
        "Prediction API",
        "FastAPI · :8000",
        ["Model loaded at start;", "/predict and /health"],
        ["fastapi", "python"],
    )
    cv.node(
        prefect,
        "container",
        "Container",
        "Prefect server",
        "Prefect 3.8 · :4200",
        ["Deployments, schedules", "and run state"],
        ["prefect"],
    )
    cv.node(
        mlflow,
        "container",
        "Container",
        "MLflow server",
        "MLflow 3.17 · :5000",
        ["SQLite + proxied", "artifacts on a volume"],
        ["mlflow"],
    )
    cv.node(
        models,
        "store",
        "Data store · volume",
        "./models",
        "classifier.joblib",
        ["Written by the worker,", "read by the API"],
    )
    cv.node(
        worker,
        "container",
        "Container",
        "Worker",
        "backend image · serve",
        ["Code gates, then train", "and evaluate, 02–06 UTC"],
        ["prefect", "python"],
        focal=True,
    )
    cv.node(
        data,
        "store",
        "Data store · read-only",
        "notebooks/data",
        "Churn_Modelling.csv",
        ["10,000 customers;", "80/20 split, seed 1"],
    )
    cv.node(
        filebeat,
        "container",
        "Container",
        "Filebeat",
        "Filebeat 9.5",
        ["Tails the containers", "labelled churn_logs"],
        ["beats"],
    )
    cv.node(
        logstash,
        "container",
        "Container",
        "Logstash",
        "Logstash 9.5 · :5044",
        ["JSON → churn-events-*", "text → churn-logs-*"],
        ["logstash"],
    )
    cv.node(
        es,
        "store",
        "Data store",
        "Elasticsearch",
        "9.5 · single node",
        ["Fields typed by an", "index template"],
        ["elasticsearch"],
    )
    cv.node(
        kibana,
        "container",
        "Container",
        "Kibana",
        "Kibana 9.5 · :5601",
        ["Traffic, predictions,", "model quality"],
        ["kibana"],
    )
    cv.node(
        setup,
        "container",
        "Container · one-shot",
        "monitoring-setup",
        "monitoring/kibana/setup.py",
        [],
    )

    cv.readout(READOUT, 1248, 96)
    cv.legend(
        1104,
        [
            ("person", "person"),
            ("container", "container"),
            ("focal", "where models are trained"),
            ("store", "data store"),
            ("call", "call / read / write"),
            ("occasional", "reads logs"),
        ],
    )


# ── C4 level 3 · components of the worker ──────────────────────────────────
def component_view(cv: Canvas):
    c1, c2, c3, c4 = 64, 372, 680, 988  # four columns, 228 wide, 80 apart
    w = 228
    deploy = Box(c1, 184, w, 128)
    gates = Box(c2, 184, 844, 128)
    flows = Box(c1, 376, w, 128)
    prep = Box(c2, 376, w, 128)
    train = Box(c3, 376, w, 128)
    evalb = Box(c4, 376, w, 128)
    track = Box(c2, 568, w, 128)
    events = Box(c3, 568, w, 128)
    save = Box(c4, 568, w, 128)
    mlflow = Box(c2, 776, w, 96)
    models = Box(c4, 776, w, 96)

    cv.zone(
        Box(32, 160, 1216, 568),
        "WORKER",
        "container · src/ + deploiement_prefect.py",
        at="bottom",
    )

    cv.arrow([(deploy.cx, deploy.b), (deploy.cx, flows.y)])
    cv.label([("triggers", False), ("cron", True)], deploy.cx + 12, 338, "start")
    cv.arrow([(flows.r, 400), (332, 400), (332, 248), (gates.x, 248)])
    cv.label([("1 · gates", False)], 332, 330)
    cv.arrow([(flows.r, 456), (prep.x, 456)])
    cv.label([("2 · jobs", False)], 332, 440)
    cv.arrow([(prep.r, 440), (train.x, 440)])
    cv.arrow([(train.r, 440), (evalb.x, 440)])
    cv.arrow([(evalb.cx, evalb.b), (evalb.cx, save.y)])
    cv.arrow(
        [(flows.cx, flows.b), (flows.cx, 536), (events.cx, 536), (events.cx, events.y)]
    )
    cv.arrow([(track.cx, 536), (track.cx, track.y)])
    cv.label([("after a run", False), ("log it, emit the event", True)], 640, 524)
    cv.arrow([(track.cx, track.b), (track.cx, mlflow.y)])
    cv.label([("logs runs", False), ("MLflow REST", True)], track.cx + 12, 748, "start")
    cv.arrow([(save.cx, save.b), (save.cx, models.y)])
    cv.label([("writes, reads", False), ("joblib", True)], save.cx + 12, 748, "start")

    cv.node(
        deploy,
        "container",
        "Component",
        "Deployments",
        "deploiement_prefect.py",
        ["all · train · evaluat", "02:00 · 04:00 · 06:00 UTC"],
        ["prefect"],
    )
    cv.node(
        gates,
        "container",
        "Components · blocking",
        "Code gates",
        "src/tasks.py · run before anything trains",
        [
            "ruff format  ·  ruff check  ·  bandit, every severity  ·  pytest, 15 tests",
            "one failure stops the flow; the same four checks run in GitHub Actions",
        ],
        focal=True,
    )
    cv.node(
        flows,
        "container",
        "Component",
        "Flows",
        "src/flows.py",
        ["all: install, gates, jobs;", "train and evaluat: subsets"],
    )
    cv.node(
        prep,
        "container",
        "Task",
        "prepare-data",
        "model_pipeline.py",
        ["Encode Gender, drop IDs", "and Geography; 80/20"],
    )
    cv.node(
        train,
        "container",
        "Task",
        "train-model",
        "RandomForestClassifier",
        ["100 trees,", "random_state 42"],
        ["scikitlearn"],
    )
    cv.node(
        evalb,
        "container",
        "Task",
        "evaluate-model",
        "accuracy · report · matrix",
        ["85.55% on 2,000 rows;", "churner recall 0.42"],
    )
    cv.node(
        track,
        "container",
        "Component",
        "Tracking",
        "src/tracking.py",
        ["Outage = warning,", "never a failure"],
        ["mlflow"],
    )
    cv.node(
        events,
        "container",
        "Component",
        "Events",
        "src/observability.py",
        ["One JSON line per run", "on stdout"],
    )
    cv.node(
        save,
        "container",
        "Task",
        "save / load",
        "joblib",
        ["Save, reload, predict", "a demo customer"],
    )
    cv.node(
        mlflow,
        "external",
        "Container · outside",
        "MLflow server",
        "experiment customer-churn",
        [],
        ["mlflow"],
    )
    cv.node(
        models, "store", "Data store · outside", "./models", "classifier.joblib", []
    )

    cv.readout(
        [
            ("CODE GATES", "4 · blocking"),
            ("SCHEDULE", "02 · 04 · 06 UTC"),
            ("FULL FLOW", "9 tasks · 5 s"),
        ],
        1248,
        96,
    )
    cv.legend(
        904,
        [
            ("container", "component"),
            ("focal", "the gates: one failure stops the flow"),
            ("store", "data store"),
            ("external", "outside the worker"),
            ("call", "call / data flow"),
        ],
    )


VIEWS = [
    View(
        "context",
        context_view,
        1280,
        592,
        "c4 model · level 1 · context",
        "Customer Churn MLOps",
        "bank churn model, retrained on a schedule behind code gates",
        "Customer Churn MLOps — C4 context view",
        "C4 context diagram: an analyst scores customers and an ML engineer runs the pipeline and reads MLflow and "
        "Kibana. The system reads the Churn_Modelling.csv dataset, clones or pulls its source from GitHub for "
        "local runs and pulls prebuilt images from Docker Hub.",
    ),
    View(
        "container",
        container_view,
        1280,
        1152,
        "c4 model · level 2 · containers",
        "The compose stack",
        "one image, two roles: it serves predictions and runs the flows",
        "Customer Churn MLOps — C4 container view",
        "C4 container diagram: nginx serves the static Churn Desk, which runs in the analyst's browser and calls the "
        "FastAPI prediction API directly; the API loads classifier.joblib from the ./models volume at start. The "
        "worker, built from the same image, polls the Prefect server for scheduled runs, reads the dataset "
        "read-only, writes the model to ./models and logs every run to MLflow. In the opt-in monitoring profile "
        "Filebeat tails the Docker logs of the API and the worker, Logstash indexes their JSON events in "
        "Elasticsearch, a one-shot setup container creates the index template and the dashboard, and Kibana "
        "shows it to the ML engineer.",
    ),
    View(
        "component",
        component_view,
        1280,
        960,
        "c4 model · level 3 · worker components",
        "Inside the pipeline",
        "pure logic in model_pipeline.py; tasks.py wraps it; flows.py chains it",
        "Customer Churn MLOps — C4 component view of the worker",
        "C4 component diagram of the worker: three Prefect deployments trigger the flows; the full flow first runs "
        "four blocking code gates (ruff format, ruff check, bandit, pytest), then prepare-data, train-model, "
        "evaluate-model and save/load. After a run, flows.py logs it to the MLflow server through tracking.py and "
        "prints a JSON event through observability.py; save/load writes classifier.joblib to the ./models volume.",
    ),
]

if __name__ == "__main__":
    build(HERE, "customer-churn-mlops", VIEWS)
