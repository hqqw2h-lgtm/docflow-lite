const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

async function unwrap(res: Response) {
  if (res.ok) {
    if (res.status === 204) return null;
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  }
  let detail: unknown = res.statusText;
  try {
    const body = await res.json();
    detail = (body && (body.detail ?? body.message)) ?? body;
  } catch {
    /* ignore */
  }
  const message =
    typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object'
        ? JSON.stringify(detail)
        : `${res.status} ${res.statusText}`;
  throw new Error(message);
}

export const http = {
  get<T>(path: string): Promise<T> {
    return fetch(`${API_BASE}${path}`).then(unwrap) as Promise<T>;
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(unwrap) as Promise<T>;
  },
  patch<T>(path: string, body: unknown): Promise<T> {
    return fetch(`${API_BASE}${path}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }).then(unwrap) as Promise<T>;
  },
  upload<T>(path: string, form: FormData): Promise<T> {
    return fetch(`${API_BASE}${path}`, { method: 'POST', body: form }).then(unwrap) as Promise<T>;
  },
};
