/**
 * Login / Sign-up page for Driftwood Capital analysts.
 *
 * Single form that toggles between sign-in and sign-up modes.
 * Uses Supabase email auth — strictly monochromatic design.
 */

import { type FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";

export function LoginPage() {
  const { user, loading } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [signUpSuccess, setSignUpSuccess] = useState(false);

  // Already signed in — go to the app
  if (!loading && user) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        });
        if (signUpError) {
          setError(signUpError.message);
        } else {
          setSignUpSuccess(true);
        }
      } else {
        const { error: signInError } =
          await supabase.auth.signInWithPassword({ email, password });
        if (signInError) {
          setError(signInError.message);
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Header with DC brand badge */}
        <div className="text-center flex flex-col items-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-foreground text-background font-bold text-sm shadow-xs mb-3">
            DC
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Document Copilot
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Driftwood Capital — SEC Filing Research Assistant
          </p>
        </div>

        {signUpSuccess ? (
          <div className="rounded-xl border border-border bg-muted/50 p-4 text-center text-xs text-foreground space-y-2">
            <p className="font-semibold text-sm">Account created</p>
            <p className="text-muted-foreground">
              Check your email for a confirmation link, then sign in.
            </p>
            <button
              type="button"
              onClick={() => {
                setIsSignUp(false);
                setSignUpSuccess(false);
              }}
              className="mt-2 text-xs font-medium text-foreground underline underline-offset-4 hover:text-foreground/80 cursor-pointer"
            >
              Back to sign in
            </button>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-2xl border border-border bg-card p-6 shadow-xs"
          >
            {/* Email */}
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="block text-xs font-medium text-foreground"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@driftwood.com"
                className="block w-full rounded-lg border border-input bg-background px-3 py-2 text-xs text-foreground shadow-2xs placeholder:text-muted-foreground focus:border-foreground/50 focus:outline-hidden focus:ring-1 focus:ring-foreground/20"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-xs font-medium text-foreground"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete={isSignUp ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                minLength={6}
                className="block w-full rounded-lg border border-input bg-background px-3 py-2 text-xs text-foreground shadow-2xs placeholder:text-muted-foreground focus:border-foreground/50 focus:outline-hidden focus:ring-1 focus:ring-foreground/20"
              />
            </div>

            {/* Error */}
            {error && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              className="flex w-full justify-center rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground shadow-xs transition-colors hover:bg-primary/90 disabled:opacity-40 cursor-pointer"
            >
              {submitting
                ? "Please wait…"
                : isSignUp
                  ? "Create Account"
                  : "Sign In"}
            </button>
          </form>
        )}

        {/* Toggle sign-in / sign-up */}
        {!signUpSuccess && (
          <p className="text-center text-xs text-muted-foreground">
            {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
            <button
              type="button"
              onClick={() => {
                setIsSignUp(!isSignUp);
                setError(null);
              }}
              className="font-medium text-foreground underline underline-offset-4 hover:text-foreground/80 cursor-pointer"
            >
              {isSignUp ? "Sign in" : "Create account"}
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
