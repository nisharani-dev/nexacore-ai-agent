# Quick Start: Deploy with Hindsight Cloud

## 🎯 Goal

Get NexaCore running in production with self-hosted Hindsight memory service.

## 📋 Prerequisites

- Render account
- GitHub repo connected to Render
- Groq API key

## 🚀 Deploy in 3 Steps

### Step 1: Deploy Hindsight Service (5 min)

1. **Go to Render Dashboard** → New → Web Service

2. **Configure:**
   - **Name:** `nexacore-hindsight`
   - **Runtime:** Docker
   - **Image URL:** `ghcr.io/vectorize-io/hindsight:latest`
   - **Region:** Oregon (or your preferred region)
   - **Instance Type:** Starter (512MB)

3. **Environment Variables:**
   ```
   HINDSIGHT_API_LLM_PROVIDER = groq
   HINDSIGHT_API_LLM_API_KEY = <your-groq-api-key>
   PORT = 8888
   ```

4. **Add Disk (CRITICAL!):**
   - Click "Add Disk"
   - **Name:** `hindsight-data`
   - **Mount Path:** `/home/hindsight/.pg0`
   - **Size:** 1 GB

5. **Create Web Service**

6. **Wait for deployment** (2-3 minutes)

7. **Note the URL:** `https://nexacore-hindsight.onrender.com`

### Step 2: Update Backend Config (2 min)

1. **Go to your backend service** (`nexacore-backend`)

2. **Add/Update Environment Variables:**
   ```
   HINDSIGHT_BACKEND = http
   HINDSIGHT_BASE_URL = https://nexacore-hindsight.onrender.com
   HINDSIGHT_PROJECT = ramp-onboarding-demo
   ```

3. **Also ensure these are set:**
   ```
   DATABASE_URL = <your-postgres-url>
   GROQ_API_KEY = <your-groq-key>
   CORS_ALLOW_ORIGINS = https://nexacore-frontend.onrender.com
   FRONTEND_URL = https://nexacore-frontend.onrender.com
   ```

4. **Save** (auto-redeploys)

### Step 3: Update Frontend Config (1 min)

1. **Go to your frontend service** (`nexacore-frontend`)

2. **Add/Update Environment Variables:**
   ```
   BACKEND_URL = https://nexacore-backend.onrender.com
   BACKEND_HOST = nexacore-backend.onrender.com
   VITE_API_BASE = /api
   ```

3. **Save** (auto-redeploys)

## ✅ Verify It Works

### Test Hindsight

```bash
curl https://nexacore-hindsight.onrender.com/health
# Should return: {"status":"healthy","database":"connected"}
```

### Test Backend

```bash
curl https://nexacore-backend.onrender.com/health
# Should return: {"status":"ok",...}

curl https://nexacore-backend.onrender.com/ready
# Check hindsight status in response
```

### Test Frontend

Visit `https://nexacore-frontend.onrender.com` and:
1. Try to create a session
2. Should work without 403/421 errors
3. Chat should function properly

## 🔍 Check Logs

**Hindsight logs** should show:
```
✓ Database connected
✓ API server running on port 8888
```

**Backend logs** should show:
```
INFO  Hindsight HTTP client initialized | base_url=https://nexacore-hindsight... | bank_id=ramp-onboarding-demo
INFO  Startup demo seed complete in Xs
INFO  Your service is live 🎉
```

## 🐛 Troubleshooting

### "Falling back to local store"

**Problem:** Backend can't reach Hindsight

**Fix:**
```bash
# Test Hindsight health
curl https://nexacore-hindsight.onrender.com/health

# Check backend env vars
echo $HINDSIGHT_BASE_URL  # Should match Hindsight URL
```

### "Memories disappear on restart"

**Problem:** No persistent disk on Hindsight service

**Fix:**
1. Go to Hindsight service → Settings → Disks
2. Verify disk mounted at `/home/hindsight/.pg0`
3. If missing, add it and redeploy

### "Database connection refused"

**Problem:** Hindsight's embedded Postgres not starting

**Fix:**
- Check Hindsight service logs
- Verify disk permissions
- Try Manual Deploy to restart cleanly

## 💰 Cost

**Render Free Tier:**
- Hindsight: $7/month (Starter)
- Backend: $7/month (Starter)
- Frontend: $7/month (Starter)
- Postgres: Free tier available
- Disk: $0.25/GB ($0.25 for 1GB)
- **Total: ~$21/month** or ~$7/month with free DB

## 📚 Alternative: render.yaml (One-Click Deploy)

Instead of manual setup, use the blueprint:

1. **Push render.yaml** to your repo (already done!)

2. **Go to Render Dashboard** → New → Blueprint

3. **Connect GitHub repo**

4. **Render will create:**
   - Hindsight service with persistent disk
   - Backend service
   - Frontend service
   - PostgreSQL database
   - All connections automatically configured!

5. **Just set these secrets manually:**
   - `GROQ_API_KEY` on backend
   - `HINDSIGHT_API_LLM_API_KEY` on hindsight

6. **Deploy!**

## 🎉 Done!

Your NexaCore app is now running with:
- ✅ Self-hosted Hindsight for memory/knowledge
- ✅ Persistent storage (survives restarts)
- ✅ Scalable architecture (all services independent)
- ✅ Production-ready setup

## 📖 Next Steps

- Read `HINDSIGHT_SETUP.md` for advanced configuration
- Check `DEPLOYMENT.md` for infrastructure details
- See `README.md` for feature documentation

## 🆘 Need Help?

1. Check service logs on Render dashboard
2. Run `python3 test_hindsight_api.py` locally
3. Verify all environment variables are set correctly
4. Ensure services are in the same region for lower latency

---

**Happy deploying!** 🚀
