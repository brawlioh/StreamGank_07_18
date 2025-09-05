# 🚨 URGENT: Railway Production URL Fix

## Problem Identified

Your StreamGank app on Railway is using `localhost:3000` instead of the production domain `https://streamgank-app-production.up.railway.app`.

## Root Cause

-   Frontend `APIService.ts` was hardcoded to fallback to `localhost:3000`
-   Docker configuration was using hardcoded localhost URLs
-   Environment variables were not properly configured for production

## ✅ Fixes Applied

### 1. Updated APIService.ts

-   Smart URL detection: uses `window.location.origin` in production
-   Production-first fallback logic
-   Added debugging logs to track URL resolution

### 2. Updated Docker Configuration

-   `docker-compose.vm-optimized.yml` now uses environment variables
-   `VITE_BACKEND_URL`, `BACKEND_URL`, and `WEBHOOK_BASE_URL` are configurable

### 3. Updated Vite Configuration

-   Production-first environment variable handling
-   Better fallback logic for different environments

### 4. Created Deployment Scripts

-   `set-production-env.sh` - Sets all required environment variables
-   Production environment configuration template

## 🚀 Railway Deployment Steps

### Option 1: Quick Fix (Immediate)

Set these environment variables in your Railway dashboard:

```bash
NODE_ENV=production
APP_ENV=production
VITE_BACKEND_URL=https://streamgank-app-production.up.railway.app
BACKEND_URL=https://streamgank-app-production.up.railway.app
WEBHOOK_BASE_URL=https://streamgank-app-production.up.railway.app
```

### Option 2: Complete Setup

1. **Set Environment Variables in Railway:**

    - Go to your Railway project dashboard
    - Navigate to Variables tab
    - Add all variables from `set-production-env.sh`

2. **Add Your API Keys:**

    ```bash
    OPENAI_API_KEY=your_key_here
    HEYGEN_API_KEY=your_key_here
    CREATOMATE_API_KEY=your_key_here
    CLOUDINARY_URL=your_url_here
    ```

3. **Redeploy:**
    - Push your changes to trigger a new deployment
    - Or manually trigger a redeploy in Railway dashboard

## 🔍 Verification Steps

1. **Check Console Logs:**

    - Open browser dev tools
    - Look for: `🔗 APIService initialized with baseURL: https://streamgank-app-production.up.railway.app`

2. **Test API Endpoints:**

    - Go to `/api/health` - should return success
    - Check queue status at `/api/queue/status`
    - Verify all requests use production domain

3. **Network Tab:**
    - All API requests should go to `streamgank-app-production.up.railway.app`
    - No requests should go to `localhost:3000`

## 🛠️ Troubleshooting

### If still showing localhost:

1. Clear browser cache completely
2. Check Railway environment variables are set
3. Verify deployment completed successfully
4. Check browser console for APIService initialization log

### If API requests fail:

1. Verify all environment variables are set in Railway
2. Check Railway logs for startup errors
3. Ensure Redis is properly configured
4. Verify API keys are valid

## 📱 Expected Result

After deployment, your app should:

-   ✅ Use `https://streamgank-app-production.up.railway.app` for all API calls
-   ✅ Display proper queue status and job management
-   ✅ Show real-time updates without localhost errors
-   ✅ Work correctly on the production domain

## 🔗 Quick Test URLs

-   Health Check: https://streamgank-app-production.up.railway.app/health
-   Queue Status: https://streamgank-app-production.up.railway.app/api/queue/status
-   Dashboard: https://streamgank-app-production.up.railway.app/dashboard
