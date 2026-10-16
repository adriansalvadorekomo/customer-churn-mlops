// The ledger: every scored case is filed in this browser (localStorage).
// No accounts, no server storage — clear-your-ledger means clear everywhere.

import type { LedgerEntry } from "./api";

const KEY = "churn-desk.ledger.v1";

export function loadLedger(): LedgerEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function appendEntry(entry: LedgerEntry): LedgerEntry[] {
  const entries = [entry, ...loadLedger()];
  try {
    localStorage.setItem(KEY, JSON.stringify(entries));
  } catch {
    /* storage full or blocked — the verdict still stands, it just won't file */
  }
  return entries;
}

export function clearLedger(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* nothing to clear */
  }
}

/** Case reference, e.g. CD-2610-0042 — year, month, sequence on file. */
export function makeRef(ts: number, seq: number): string {
  const d = new Date(ts);
  const yy = String(d.getFullYear()).slice(2);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `CD-${yy}${mm}-${String(seq).padStart(4, "0")}`;
}

const MONTHS = [
  "JAN",
  "FEB",
  "MAR",
  "APR",
  "MAY",
  "JUN",
  "JUL",
  "AUG",
  "SEP",
  "OCT",
  "NOV",
  "DEC",
];

/** 15 OCT 2026 · 22:41 */
export function formatWhen(ts: number): string {
  const d = new Date(ts);
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${day} ${MONTHS[d.getMonth()]} ${d.getFullYear()} · ${hh}:${min}`;
}

export function formatMoney(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

/** "F · 43 · $125,510.82 · 1 product" — the one-line case summary. */
export function summarize(customer: LedgerEntry["customer"]): string {
  const gender = customer.Gender === 1 ? "M" : "F";
  const product = customer.NumOfProducts === 1 ? "product" : "products";
  return `${gender} · ${customer.Age} · ${formatMoney(customer.Balance)} · ${customer.NumOfProducts} ${product}`;
}
