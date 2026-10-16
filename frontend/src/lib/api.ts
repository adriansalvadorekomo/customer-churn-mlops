// Client for the FastAPI churn service. The base URL is baked in at build
// time (PUBLIC_API_URL); inside docker compose it points at the published
// backend port, in `astro dev` at the local uvicorn.

export const API_BASE: string =
  import.meta.env.PUBLIC_API_URL ?? "http://localhost:8000";

/** The 9 preprocessed features the API expects, in FEATURE_COLS order. */
export type Customer = {
  CreditScore: number;
  Gender: number;
  Age: number;
  Tenure: number;
  Balance: number;
  NumOfProducts: number;
  HasCrCard: number;
  IsActiveMember: number;
  EstimatedSalary: number;
};

export type LedgerEntry = {
  ref: string;
  ts: number;
  exited: number;
  customer: Customer;
};

/** GET /health — true when the backend answers. */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(4000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** POST /predict — returns the model verdict (0 stays, 1 leaves). */
export async function fetchPrediction(customer: Customer): Promise<number> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(customer),
      signal: AbortSignal.timeout(15000),
    });
  } catch (error) {
    // Network down, CORS wall, or a backend that never answered.
    const timedOut =
      error instanceof DOMException && error.name === "TimeoutError";
    throw new Error(
      timedOut
        ? "no answer within 15s — the desk gave up waiting"
        : String(error),
    );
  }

  if (!res.ok) {
    let reason = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) reason += ` — ${JSON.stringify(body.detail)}`;
    } catch {
      /* keep the status line */
    }
    throw new Error(reason);
  }

  const data = await res.json();
  if (typeof data?.exited !== "number") {
    throw new Error("Unexpected response shape from /predict");
  }
  return data.exited;
}
