export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function createApiUrl(baseUrl: string, path: string): string {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${normalizedBaseUrl}${normalizedPath}`;
}

type ApiErrorPayload = {
  error?: unknown;
  detail?: unknown;
  message?: unknown;
};

export function apiErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload !== "object" || payload === null) {
    return fallback;
  }

  const candidate = payload as ApiErrorPayload;
  if (typeof candidate.error === "object" && candidate.error !== null) {
    const structuredError = candidate.error as { message?: unknown };
    if (typeof structuredError.message === "string") {
      return structuredError.message;
    }
  }
  if (typeof candidate.detail === "string") {
    return candidate.detail;
  }
  if (typeof candidate.message === "string") {
    return candidate.message;
  }
  return fallback;
}

export async function readResponseError(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status}`;
  try {
    return apiErrorMessage(await response.json(), fallback);
  } catch {
    return fallback;
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(createApiUrl(API_BASE_URL, path));

  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }

  return response.json() as Promise<T>;
}
