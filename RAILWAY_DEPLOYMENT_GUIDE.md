# 🚄 Railway Deployment Guide

Simple guide for updating code and environment variables on Railway.

## 🔧 **Update Environment Variables**

### **Method 1: Railway Dashboard (Easiest)**

1. Go to: https://railway.com/project/78f910b9-2107-4b46-862b-950a0d272a75
2. Click **"streamgank-app"** service
3. Click **"Variables"** tab
4. Click **"+ New Variable"**
5. Enter name and value → **Auto-deploys!**

### **Method 2: CLI**

```bash
# Single variable
railway variables --set "VARIABLE_NAME=value"

# Multiple variables
railway variables --set "VAR1=value1" --set "VAR2=value2"

# View current variables
railway variables
```

---

## 💻 **Update Code on Railway**

### **Method 1: Git Push (Recommended)**

```bash
# 1. Make changes to your code
# 2. Commit and push
git add .
git commit -m "Your update message"
git push origin main

# ✅ Railway auto-deploys in 2-3 minutes
```

### **Method 2: Direct Deploy**

```bash
# Deploy current local files immediately
railway up --detach

# Monitor deployment
railway logs
```

---

## 🏠 **Local Development**

### **Work Locally Without Affecting Railway:**

```bash
# 1. Copy Railway environment to local
cp railway.env .env

# 2. Test locally
docker-compose up --build
# Visit: http://localhost:3000

# 3. When ready, deploy to Railway
git push origin main
```

### **Branch-Based Development:**

```bash
# Create development branch
git checkout -b feature-branch

# Make changes and test locally
# ...

# Deploy when ready
git checkout main
git merge feature-branch
git push origin main
```

---

## 📊 **Monitor Deployments**

### **Check Status:**

```bash
# View logs
railway logs

# Check deployment status
railway status

# See deployment history
railway deployments
```

### **Dashboard:**

-   Visit: https://railway.com/project/78f910b9-2107-4b46-862b-950a0d272a75
-   Click **"Deployments"** for build progress
-   View real-time logs

---

## 🎯 **Quick Reference**

| Task                | Command                     | Time    |
| ------------------- | --------------------------- | ------- |
| **Update env vars** | Railway Dashboard           | Instant |
| **Deploy code**     | `git push origin main`      | 2-3 min |
| **Quick deploy**    | `railway up --detach`       | 1-2 min |
| **View logs**       | `railway logs`              | Instant |
| **Local test**      | `docker-compose up --build` | 1 min   |

---

## ⚡ **Common Workflows**

### **Environment Variable Update:**

```bash
# Update via dashboard → Auto-redeploys
```

### **Code Update:**

```bash
# Edit files locally
git add .
git commit -m "Fixed YouTube downloads"
git push origin main
# Wait 2-3 minutes → Live!
```

### **Emergency Fix:**

```bash
# Quick local fix
railway up --detach
railway logs  # Monitor results
```

---

## 🚨 **Important Notes**

-   **Git push to `main`** = automatic Railway deployment
-   **Environment variables** via dashboard = instant auto-redeploy
-   **Local testing** doesn't affect Railway
-   **Zero downtime** - old version runs until new one is ready
-   **Build logs** show deployment progress

---

**Your Railway App:** https://streamgank-app-production.up.railway.app

**Dashboard:** https://railway.com/project/78f910b9-2107-4b46-862b-950a0d272a75
