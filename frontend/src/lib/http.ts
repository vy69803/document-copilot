/**
 * Thin fetch wrapper with base URL, JSON handling, Supabase bearer token
 * injection, timeouts, and typed error responses.
 *
 * All backend calls should go through this module or the higher-level api.ts.
 */

import { env } from "@/lib/env";
import { getAccessToken } from "@/lib/supabase";

const DEFAULT_TIMEOUT_MS = 30_000;

/** Structured error returned by the backend or generated client-side. */
export class ApiError extends Error {
  readonly status: number;
  readonly isNetworkError: boolean;

  constructor(
    message: string,
    status: number,
    isNetworkError: boolean = false,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}


type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  timeoutMs?: number;
  /** Skip automatic bearer token injection (e.g. for public endpoints). */
  skipAuth?: boolean;
};

/**
 * Core fetch wrapper.
 * - Prepends `VITE_API_BASE_URL`
 * - Injects `Authorization: Bearer <token>` from Supabase session
 * - Serializes body as JSON
 * - Applies a timeout via AbortController
 * - Throws `ApiError` on non-2xx responses and network failures
 */
export async function http<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, timeoutMs = DEFAULT_TIMEOUT_MS, skipAuth = false, headers: extraHeaders, ...init } = options;

  const headers = new Headers(extraHeaders);
  headers.set("Content-Type", "application/json");

  if (!skipAuth) {
    const token = await getAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${env.API_BASE_URL}${path}`, {
      ...init,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const json = await response.json();
        detail = json.detail ?? json.message ?? detail;
      } catch {
        // response body wasn't JSON — keep statusText
      }
      throw new ApiError(detail, response.status);
    }

    // 204 No Content — return undefined as T
    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;

    // Network / CORS / timeout failures
    const message =
      error instanceof DOMException && error.name === "AbortError"
        ? "Request timed out"
        : `Network error — unable to reach backend (${env.API_BASE_URL}). Ensure the backend is running.`;

    throw new ApiError(message, 0, true);
  } finally {
    clearTimeout(timeout);
  }
}
