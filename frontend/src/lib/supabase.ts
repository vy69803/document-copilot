/**
 * Browser-side Supabase client for authentication.
 *
 * This client uses the anon (public) key and is safe to run in the browser.
 * It manages session state, token refresh, and provides the access token
 * that other modules (http.ts) inject into backend API calls.
 */

import { createClient } from "@supabase/supabase-js";

import { env } from "@/lib/env";

export const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY);

/**
 * Returns the current user's access token, or null if not signed in.
 * Used by http.ts to inject the Authorization header into backend calls.
 */
export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
