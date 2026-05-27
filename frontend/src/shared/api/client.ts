const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...init
  });
  if (!response.ok) {
    const method = init?.method ?? 'GET';
    const message = await response.text();
    throw new Error(formatApiError(method, path, response.status, response.statusText, message));
  }
  return response.json() as Promise<T>;
}

export function isApiNotFound(error: unknown, method: string, path: string): boolean {
  return error instanceof Error && error.message.startsWith(`${method} ${path} failed (404):`);
}

function formatApiError(method: string, path: string, status: number, statusText: string, body: string): string {
  const detail = parseApiErrorDetail(body);
  const reason = detail || statusText || 'Request failed';
  return `${method} ${path} failed (${status}): ${reason}`;
}

function parseApiErrorDetail(body: string): string {
  if (!body) return '';
  try {
    const parsed = JSON.parse(body) as unknown;
    if (isErrorWithDetail(parsed)) {
      return typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
    }
    return typeof parsed === 'string' ? parsed : JSON.stringify(parsed);
  } catch {
    return body;
  }
}

function isErrorWithDetail(value: unknown): value is { detail: unknown } {
  return typeof value === 'object' && value !== null && 'detail' in value;
}
