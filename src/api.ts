
import { firebaseAuth } from "./firebase"

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function apiError(response: Response): Promise<Error> {
  let detail = "The server could not complete the request. Check the API connection and try again.";
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const value = (body as { detail?: unknown }).detail;
      if (typeof value === "string" && value.trim()) detail = value;
    }
  } catch {
    // Avoid displaying proxy/HTML error pages in the product UI.
  }
  return new Error(`${detail} (HTTP ${response.status})`);
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await firebaseAuth?.currentUser?.getIdToken()
  if (!token) {
    throw new Error("Sign in to Privora before accessing your data.")
  }
  return { Authorization: `Bearer ${token}` }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: await authHeaders(),
  });

  if (!response.ok) {
    throw await apiError(response);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      ...(await authHeaders()),
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw await apiError(response);
  }

  return response.json() as Promise<T>;
}
