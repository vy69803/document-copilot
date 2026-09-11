# Railway Deployment Runbook — Document Copilot

This guide outlines the end-to-end procedure for deploying **Document Copilot** (FastAPI backend + React SPA frontend) to [Railway](https://railway.com) using containerized services, connected to hosted Supabase Postgres and Gemini LLM.

---

## 1. Prerequisites

Before starting, ensure you have:
1. **GitHub Repository**: [vy69803/document-copilot](https://github.com/vy69803/document-copilot) with latest commits pushed.
2. **Railway Account**: [railway.com](https://railway.com) account linked to GitHub.
3. **Supabase Project Credentials** (from [supabase-setup.md](supabase-setup.md)):
   - Direct Postgres URL (`postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`)
   - Supabase URL (`https://[PROJECT-REF].supabase.co`)
   - `anon` public key
   - `service_role` secret key
4. **LLM API Key**:
   - Google Gemini API Key (`GEMINI_API_KEY`)

---

## 2. Deployment Architecture

Railway will host **two separate services** inside a single project from the same GitHub repository:

| Service | Root Directory | Build / Runtime | Healthcheck Path | Public Networking |
| :--- | :--- | :--- | :--- | :--- |
| **`backend`** | `/backend` | Dockerfile (`python:3.12` + `uv` + `alembic`) | `/health` | `https://copilot-api-production.up.railway.app` |
| **`frontend`** | `/frontend` | Dockerfile (`node:22` build + `nginx:alpine`) | `/` | `https://copilot-app-production.up.railway.app` |

---

## 3. Step-by-Step Deployment Instructions

### Step 3.1: Create Project on Railway
1. Log in to [Railway Dashboard](https://railway.com/dashboard).
2. Click **"+ New Project"**.
3. Select **"Deploy from GitHub repo"**.
4. Choose **`vy69803/document-copilot`**.

---

### Step 3.2: Configure & Deploy Backend Service

1. In the Railway project canvas, click on the newly created service.
2. Navigate to the **"Settings"** tab:
   - **Service Name**: Rename to `document-copilot-backend`.
   - **Root Directory**: Set to `/backend`.
   - **Healthcheck Path**: Set to `/health`.
3. Navigate to the **"Variables"** tab and add the backend environment variables:

| Variable Name | Example Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enables production mode |
| `DATABASE_URL` | `postgresql://postgres:pwd@db.ref.supabase.co:5432/postgres` | **Direct** connection string (port 5432, session mode for migrations) |
| `SUPABASE_URL` | `https://ref.supabase.co` | Supabase API endpoint |
| `SUPABASE_ANON_KEY` | `eyJhbGci...` | Supabase client anon key |
| `SUPABASE_SERVICE_ROLE_KEY`| `eyJhbGci...` | Supabase service role secret |
| `GEMINI_API_KEY` | `AIzaSy...` | Gemini API key |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Temporary value; will update with frontend URL in Step 3.4 |

4. Navigate to the **"Networking"** section in **Settings**:
   - Click **"Generate Domain"** (e.g. `document-copilot-backend-production.up.railway.app`).
   - Copy this URL (save for frontend setup).
5. Click **"Deploy"** (or let Railway auto-trigger the build).
   - Railway will build the backend Docker image, run `uv run alembic upgrade head` on startup, and launch Uvicorn.
   - Verify: Open `https://<backend-domain>.up.railway.app/health` in your browser. You should see `{"status":"ok","environment":"production"}`.

---

### Step 3.3: Configure & Deploy Frontend Service

1. In the same Railway project canvas, click **"+ New"** (top right) → **"Service"** → **"GitHub Repo"**.
2. Select **`vy69803/document-copilot`** again.
3. Click on the new service and go to the **"Settings"** tab:
   - **Service Name**: Rename to `document-copilot-frontend`.
   - **Root Directory**: Set to `/frontend`.
4. Navigate to the **"Variables"** tab and add the frontend build variables:

| Variable Name | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://<backend-domain>.up.railway.app` | Backend URL generated in Step 3.2 |
| `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` | Supabase Project URL |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbGci...` | Supabase anon key (browser-safe) |

> **Note on Vite Build Args:** Railway automatically passes service environment variables as Docker build arguments (`ARG`) during build time, so Vite will bake them directly into the compiled SPA bundle.

5. Navigate to the **"Networking"** section in **Settings**:
   - Click **"Generate Domain"** (e.g. `document-copilot-frontend-production.up.railway.app`).
   - Copy this frontend URL.
6. Click **"Deploy"**.
   - Railway will compile the TypeScript bundle, build Vite static assets, and start the lightweight Nginx container.

---

### Step 3.4: Wire CORS on Backend

Now that the frontend has a production domain:
1. Return to the **`document-copilot-backend`** service in Railway.
2. Go to the **"Variables"** tab.
3. Update `ALLOWED_ORIGINS` to include the frontend domain (comma-separated):
   ```text
   https://<frontend-domain>.up.railway.app,http://localhost:5173
   ```
4. Railway will automatically redeploy the backend service with zero downtime.

---

## 4. Verification & Smoke Testing Checklist

Once both services are active with green status indicators:

- [ ] **1. Healthcheck**:
  Visit `https://<backend-domain>.up.railway.app/health` → returns `{"status":"ok","environment":"production"}`.
- [ ] **2. Frontend Initial Load**:
  Visit `https://<frontend-domain>.up.railway.app` → renders login screen without console errors.
- [ ] **3. SPA Routing & Fallback**:
  Reload the browser while on `https://<frontend-domain>.up.railway.app/login` → verifies Nginx `try_files` loads `index.html` instead of a 404.
- [ ] **4. Authentication**:
  Sign in or sign up with an email address → session token stored and user redirected to the main chat interface.
- [ ] **5. Retrieval & Agent Streaming**:
  Select a suggested analyst prompt (e.g. Apple 2024 revenue mix) → status updates stream in (`Searching corpus...` → `Analyzing passages...` → `Validating citations...`), followed by streamed response.
- [ ] **6. Citation Drawer**:
  Click any inline citation badge (e.g. `[AAPL 2024 10-K, Item 7]`) → slide-over drawer opens showing exact excerpt and metadata.

---

## 5. Troubleshooting & Gotchas

### Issue 1: CORS Network Error on Chat Stream
- **Symptom**: Frontend displays *"Network / CORS connection error"* or requests to `/chat/stream` fail with `Failed to fetch`.
- **Fix**: Check `ALLOWED_ORIGINS` on the backend service in Railway. Ensure:
  1. The frontend origin matches exactly (no trailing slash: `https://foo.up.railway.app`, NOT `https://foo.up.railway.app/`).
  2. The protocol is `https://`.

### Issue 2: Alembic Migration Failure on Startup
- **Symptom**: Backend container crashes immediately on deploy with `sqlalchemy.exc.OperationalError` or timeout.
- **Fix**: Ensure `DATABASE_URL` is using the **direct connection** (port 5432, host `db.<ref>.supabase.co`), **NOT** the Supabase transaction pooler (port 6543, `pooler.supabase.com`). If your database password has special characters, ensure they are URL-encoded.

### Issue 3: Missing Environment Variables at Frontend Runtime
- **Symptom**: Frontend console throws `Missing required environment variable: VITE_API_BASE_URL`.
- **Fix**: Because Vite variables are embedded at build time, any changes to `VITE_*` in Railway require a new deployment build. Trigger **"Redeploy"** in Railway after saving frontend variables.
