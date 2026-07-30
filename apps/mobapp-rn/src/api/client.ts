import { getDeviceId } from '@/services/deviceId';
import { ApiError, type ApiErrorBody } from '@/api/types';

const DEFAULT_BASE = 'http://localhost:8000';

function apiBase(): string {
  const raw = process.env.EXPO_PUBLIC_API_URL?.trim() || DEFAULT_BASE;
  return raw.replace(/\/$/, '');
}

function formatDetail(body: unknown): string {
  if (!body || typeof body !== 'object') return 'Request failed';
  const detail = (body as ApiErrorBody).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
      .join('; ');
  }
  return 'Request failed';
}

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
};

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const base = `${apiBase()}/api/v1${path.startsWith('/') ? path : `/${path}`}`;
  if (!query) return base;
  const parts: string[] = [];
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  }
  return parts.length ? `${base}?${parts.join('&')}` : base;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, query, signal } = options;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Device-Id': getDeviceId(),
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, formatDetail(parsed), parsed);
  }

  return parsed as T;
}

export function getApiBaseUrl(): string {
  return apiBase();
}
