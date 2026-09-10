/**
 * Single source of truth for frontend environment variables.
 * Validates required vars at import time — fail fast if anything is missing.
 *
 * Usage: import { env } from "@/lib/env";
 * Never read import.meta.env directly in components.
 */

function required(key: string): string {
  const value = import.meta.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export const env = {
  API_BASE_URL: required("VITE_API_BASE_URL"),
  SUPABASE_URL: required("VITE_SUPABASE_URL"),
  SUPABASE_ANON_KEY: required("VITE_SUPABASE_ANON_KEY"),
} as const;
