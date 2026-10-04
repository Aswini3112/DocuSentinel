# DocuSentinel AI — Deployment Guide

Deploy the **backend on Render** and the **frontend on Vercel**.

```
User Browser
     │
     ▼
Vercel (frontend)          ← React/Vite SPA
     │  /api/* rewrites
     ▼
Render (backend)           ← FastAPI + SQLite + NumPy vector store
```

---

## Part 1 — Deploy Backend on Render

### Prerequisites
- GitHub repo pushed (done ✅)
- Free Render account at https://render.com

### Steps

#### 1. Create a new Web Service

1. Go to https://dashboard.render.com
2. Click **New** → **Web Service**
3. Connect your GitHub account → select **Aswini3112/DocuSentinel**
4. Configure:

| Field | Value |
|---|---|
| **Name** | `docusentinel-api` |
| **Region** | Singapore (or nearest to you) |
| **Branch** | `main` |
| **Root Directory** | *(leave blank — repo root)* |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |

5. Select **Free** plan → **Create Web Service**

Your backend URL will be: `https://docusentinel-api.onrender.com`

---

#### 2. Add Environment Variables

In the Render dashboard → your service → **Environment** tab, add:

| Key | Value | Required? |
|---|---|---|
| `RENDER` | `true` | Yes |
| `LLM_API_KEY` | `gsk_...` (your Groq/OpenAI key) | Strongly recommended |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Yes |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Yes (Groq) or blank (OpenAI) |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app,http://localhost:5173` | Yes — update after Vercel deploy |
| `DATABASE_URL` | `sqlite+aiosqlite:////opt/data/docusentinel.db` | Yes |
| `UPLOAD_DIR` | `/opt/data/uploads` | Yes |
| `VECTORSTORE_DIR` | `/opt/data/vectorstore` | Yes |
| `CHUNK_SIZE` | `150` | Optional |
| `TOP_K_RETRIEVAL` | `8` | Optional |
| `SIMILARITY_THRESHOLD` | `0.05` | Optional |

> **Free plan note:** Render free tier has **ephemeral storage** — the database and vector store reset on every deploy. After each deploy, click **Load Demo Data** on the Documents page to re-ingest the demo documents. To persist data across deploys, upgrade to the Starter plan ($7/mo) and add a **Disk** mount at `/opt/data`.

---

#### 3. Add Persistent Disk (Starter plan only)

1. In the Render dashboard → your service → **Disks** tab
2. Click **Add Disk**:
   - **Name:** `docusentinel-data`
   - **Mount Path:** `/opt/data`
   - **Size:** 1 GB
3. Save — your data now survives redeploys

---

#### 4. Verify backend health

Once deployed, open:
```
https://docusentinel-api.onrender.com/api/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "ok",
  "vector_store": "ok (0 vectors)",
  "llm_status": "CONFIGURED"
}
```

---

## Part 2 — Deploy Frontend on Vercel

### Prerequisites
- Free Vercel account at https://vercel.com

### Steps

#### 1. Update vercel.json with your Render URL

Before deploying, update `vercel.json` — replace the placeholder with your actual Render URL:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://docusentinel-api.onrender.com/api/:path*"
    }
  ]
}
```

If your Render service is named differently, use the actual URL from the Render dashboard.

#### 2. Commit the updated vercel.json

```bash
git add vercel.json
git commit -m "chore: update Render backend URL in vercel.json"
git push
```

#### 3. Import to Vercel

1. Go to https://vercel.com/new
2. Click **Import Git Repository**
3. Select **Aswini3112/DocuSentinel**
4. Configure:

| Field | Value |
|---|---|
| **Framework Preset** | Other (or Vite) |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

5. Click **Deploy**

Your frontend URL will be: `https://docusentinel-ai.vercel.app` (or similar)

---

#### 4. Update CORS on Render

After Vercel deploys, copy the frontend URL and update the `ALLOWED_ORIGINS` environment variable on Render:

```
https://docusentinel-ai.vercel.app,http://localhost:5173
```

Render will auto-redeploy with the new CORS setting.

---

## Part 3 — First-time Setup After Deploy

1. Open your Vercel frontend URL
2. Go to **Documents** page
3. Click **Load Demo Data**
4. Wait ~30 seconds for all 5 documents to reach **Ready** status
5. Go to **Investigate** and ask: *"What is the project deadline?"*
6. You should see **CONFLICTING** with evidence from multiple documents

---

## Troubleshooting

### Backend shows 502 Bad Gateway
- Render free tier **sleeps after 15 minutes of inactivity** — first request takes ~30s to wake up
- Click the Render dashboard → **Manual Deploy** to force a fresh boot
- Upgrade to Starter plan to avoid cold starts

### Frontend shows "Network Error" or blank data
- Check browser DevTools → Network tab → `/api/health` request
- If it returns 200 but with HTML: the Vercel rewrite is not matching — check `vercel.json`
- If it returns CORS error: update `ALLOWED_ORIGINS` on Render with your exact Vercel URL (no trailing slash)

### Documents stuck in "Extracting" on Render free tier
- Render free tier has 512MB RAM — PDF processing may be slow
- Large PDFs (>20 pages) may hit memory limits — use TXT files for the demo
- Check Render logs: Dashboard → your service → **Logs**

### LLM shows NOT_CONFIGURED
- Add `LLM_API_KEY` in Render dashboard → Environment → Add Variable
- Get a free key at https://console.groq.com
- Render will redeploy automatically

---

## Architecture

```
GitHub (source)
       │
       ├── Vercel reads frontend/ ──► React SPA ──► https://your-app.vercel.app
       │                                  │
       │                               /api/* rewrite
       │                                  │
       └── Render reads backend/ ──► FastAPI ──► https://docusentinel-api.onrender.com
                                         │
                                    /opt/data/  (persistent disk)
                                    ├── docusentinel.db   (SQLite)
                                    ├── uploads/          (uploaded files)
                                    └── vectorstore/      (numpy vectors + vocab)
```
