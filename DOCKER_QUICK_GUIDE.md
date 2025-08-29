# 🚀 StreamGank Docker Quick Reference

**⚡ Fast commands to avoid re-downloading dependencies!**

**🚨 IMPORTANT:** For code changes, use `vm-start` (rebuilds) NOT `vm-simple-restart` (doesn't rebuild)

---

## 🎯 **Most Common Operations (99% of the time)**

### **🟢 Start the App**

```bash
bash vm-docker-management.sh vm-start
```

**Use when:** Starting fresh or containers are stopped

---

### **🔄 Code Changes (JavaScript, Python, HTML, CSS)**

```bash
# Stop containers (if running)
docker-compose -f docker-compose.vm-optimized.yml down

# Start with rebuilt code (RECOMMENDED)
bash vm-docker-management.sh vm-start
```

**Time:** ~30-60 seconds (rebuilds with cache)  
**Use when:** You modified any code files

**Alternative (faster):**

```bash
# Update without stopping first
bash vm-docker-management.sh vm-update
```

---

### **🔄 Simple Restart (No Code Changes)**

```bash
# Fast restart without rebuilding (SAVES DISK SPACE!)
bash vm-docker-management.sh vm-simple-restart
```

**Time:** ~10-15 seconds  
**Use when:** Service issues, container problems, no code changes
**Benefit:** Saves 50GB of Docker cache buildup!

---

### **📝 .env Changes Only**

```bash
# Stop containers
docker-compose -f docker-compose.vm-optimized.yml down

# Start again (no rebuild needed)
bash vm-docker-management.sh vm-start
```

**Time:** ~10 seconds  
**Use when:** You only changed environment variables

---

## 🛑 **Stop Everything**

```bash
docker-compose -f docker-compose.vm-optimized.yml down
```

---

## ⚠️ **Slow Operations (Avoid Unless Necessary)**

### **🐌 Full Rebuild (Re-downloads Everything)**

```bash
bash vm-docker-management.sh vm-rebuild
```

**Time:** 3-5 minutes _(re-downloads all dependencies)_  
**⚠️ ONLY use when:**

-   Added new Python packages to `requirements.txt`
-   Added new Node.js packages to `package.json`
-   Changed system dependencies in `Dockerfile`
-   **NOT for code changes!**

---

## 📊 **Quick Decision Chart**

| **What Changed?**                     | **Command**         | **Time**  |
| ------------------------------------- | ------------------- | --------- |
| 🔧 **Code files** (py, js, html, css) | `vm-start`          | 30-60 sec |
| 🔄 **Nothing** (just restart)         | `vm-simple-restart` | 10-15 sec |
| 📝 **`.env` only**                    | `vm-start`          | 10 sec    |
| 📦 **`requirements.txt`**             | `vm-rebuild`        | 3-5 min   |
| 📦 **`package.json`**                 | `vm-rebuild`        | 3-5 min   |
| 🐳 **`Dockerfile`**                   | `vm-rebuild`        | 3-5 min   |

---

## 🔍 **Check Status**

```bash
# See running containers
docker ps

# Check logs
docker logs streamgank-app

# Check GUI
curl http://localhost:3000
```

---

## 💡 **Pro Tips**

### **✅ Docker Layer Caching**

-   Docker caches each step in `Dockerfile`
-   `vm-build` reuses cached dependencies → FAST
-   `vm-rebuild` ignores cache → SLOW

### **✅ Best Practice Workflow**

1. Make code changes
2. `docker-compose -f docker-compose.vm-optimized.yml down`
3. `bash vm-docker-management.sh vm-build` _(fast)_
4. `bash vm-docker-management.sh vm-start`

### **❌ Don't Do This**

```bash
# ❌ This re-downloads everything for no reason!
bash vm-docker-management.sh vm-rebuild  # (for code changes)
```

### **✅ Do This Instead**

```bash
# ✅ This uses cache and is 200x faster!
bash vm-docker-management.sh vm-build    # (for code changes)
```

---

## 🚨 **Emergency Commands**

### **Clean Everything (Nuclear Option)**

```bash
# Stop all containers
docker-compose -f docker-compose.vm-optimized.yml down

# Remove all containers, images, and volumes (⚠️ LOSES DATA!)
docker system prune -a --volumes

# Start from scratch
bash vm-docker-management.sh vm-start
```

**⚠️ WARNING:** This deletes all Docker data including your videos/assets!

### **Just Clean Build Cache**

```bash
docker builder prune -a
```

**Use when:** Build cache is taking too much disk space

---

## 📱 **Quick Reference Card**

| **Goal**       | **Fast Command**    |
| -------------- | ------------------- |
| Start app      | `vm-start`          |
| Code changed   | `down` → `vm-start` |
| Simple restart | `vm-simple-restart` |
| .env changed   | `down` → `vm-start` |
| Stop app       | `down`              |
| New packages   | `vm-rebuild`        |

---

## 🎯 **Remember**

-   **Code changes = `vm-start` (rebuilds with code)**
-   **Simple restart = `vm-simple-restart` (saves 50GB!)**
-   **New packages = `vm-rebuild` (slow)**
-   **When in doubt, try `vm-simple-restart` first!**

---

## 💾 **Disk Space Management**

### **📊 Check Docker Disk Usage**

```bash
docker system df
```

**Shows:** Images, containers, build cache sizes

---

### **🧹 Clean Build Cache (Most Common Issue)**

```bash
# Clean all build cache (can save 10-20GB!)
docker builder prune -a
```

**Use when:** Docker using too much disk space  
**Safe:** Yes, just rebuilds slower next time

---

### **🗑️ Clean Unused Images**

```bash
# Remove unused images
docker image prune -a
```

**Use when:** You have old/unused Docker images

---

### **🚨 Full Cleanup (Nuclear)**

```bash
# Clean everything (⚠️ LOSES DATA!)
docker system prune -a --volumes
```

**⚠️ WARNING:** Deletes all Docker data including videos/assets!

---

### **💡 Disk Space Pro Tips**

-   **Build cache grows over time** → Clean monthly with `docker builder prune -a`
-   **Most space issues = build cache** → Start with `docker builder prune -a`
-   **Check first:** `docker system df` to see what's using space
-   **Prevention:** Clean build cache weekly/monthly

---

## 👥 **Multi-Worker Queue System**

### **⚙️ Configuration**

Set in your `.env` file:

```bash
# Max concurrent workers (1-5 recommended)
MAX_WORKERS=3

# Enable concurrent processing
ENABLE_CONCURRENT_PROCESSING=true
```

**Default**: 3 workers, concurrent processing enabled

---

### **🔄 How It Works**

-   **Multiple jobs run simultaneously** (up to MAX_WORKERS)
-   **Redis queue manages job distribution** automatically
-   **Each job gets its own Python process**
-   **Worker slots are recycled** when jobs complete

---

### **📊 Benefits**

| **Workers** | **Speed Boost**     | **Use Case**                    |
| ----------- | ------------------- | ------------------------------- |
| 1 worker    | 1x (default)        | Single user, limited resources  |
| 2 workers   | ~2x faster          | Small team, moderate load       |
| 3 workers   | ~3x faster          | **Recommended for most setups** |
| 4+ workers  | Diminishing returns | High-load production only       |

---

### **🎛️ Control Options**

```bash
# Disable concurrent processing (back to 1-at-a-time)
ENABLE_CONCURRENT_PROCESSING=false

# Reduce workers for low-resource systems
MAX_WORKERS=1

# Increase for powerful systems (not recommended >5)
MAX_WORKERS=5
```

---

## 🚄 **Railway Cloud Deployment** ⭐

### **✅ Current Docker Compatibility Check**

Your StreamGank project is **mostly Railway-ready**! Here's what needs adjustment:

#### **✅ What Already Works:**

-   Single Dockerfile with Python + Node.js
-   Port 3000 configuration
-   Environment variables setup
-   Health checks configured

#### **⚠️ What Needs Railway Modifications:**

-   Multi-container setup (docker-compose has 2 services)
-   Local volume mounts (`./docker_volumes`)
-   Separate Redis container

### **🛠️ Railway Deployment Steps**

#### **1️⃣ Use Railway-Optimized Files**

```bash
# Railway-specific Dockerfile (already created)
railway.dockerfile

# Railway environment template (already created)
railway.env
```

#### **2️⃣ Create Railway Account & Setup** _(5 minutes)_

```bash
# 1. Create account at https://railway.app
# - Sign up with GitHub (recommended)
# - Or use email/password
# - Verify email if needed

# 2. Install Railway CLI
npm install -g @railway/cli

# 3. Login from terminal
railway login
# → Opens browser to authorize CLI

# 4. Create new project
railway new streamgank-videos
# → Creates project on Railway dashboard

# 5. Add Redis plugin (replaces your local Redis)
railway add redis
# → Adds managed Redis instance

# 6. Deploy your app
railway up --dockerfile railway.dockerfile
# → Builds and deploys your StreamGank app
```

#### **3️⃣ Configure Environment**

In Railway dashboard, copy values from `railway.env`:

-   `APP_ENV=production`
-   `OPENAI_API_KEY=your-key`
-   `HEYGEN_API_KEY=your-key`
-   `CREATOMATE_API_KEY=your-key`
-   `MAX_WORKERS=2` _(Railway optimized)_

#### **4️⃣ Access Your Deployed App**

```bash
# Get your unique URL
railway status

# Example output:
# https://streamgank-production-a1b2c3.up.railway.app
```

### **💰 Railway Pricing**

| Plan    | Cost      | RAM   | CPU    | Best For          |
| ------- | --------- | ----- | ------ | ----------------- |
| Hobby   | $5/month  | 512MB | 1 vCPU | Testing           |
| **Pro** | $20/month | 8GB   | 8 vCPU | **Production** ⭐ |

### **🔐 Privacy & Access**

-   **Private by default** - only accessible via your unique Railway URL
-   **Team sharing** - Add collaborators in Railway dashboard
-   **Custom domain** - Connect your own domain later

### **📊 Railway vs Local Development**

| Feature           | Local Docker   | Railway             |
| ----------------- | -------------- | ------------------- |
| **Setup Time**    | 30+ minutes    | 10 minutes          |
| **Maintenance**   | Manual updates | Automatic           |
| **Accessibility** | Local only     | Internet accessible |
| **Redis**         | Self-managed   | Managed service     |
| **SSL**           | Manual setup   | Automatic HTTPS     |
| **Monitoring**    | Custom logs    | Built-in dashboard  |

---

## 🔄 **Updating Your Railway App** _(Super Easy!)_

### **🚀 Method 1: Git Push Auto-Deploy** _(Recommended)_

```bash
# Make your code changes locally
git add .
git commit -m "✨ Added new video filter feature"
git push origin main

# 🎉 Railway automatically deploys in ~2-3 minutes!
# No manual steps needed!
```

**How it works:**

-   Railway watches your GitHub repo
-   **Every push to main branch = automatic deployment**
-   Build logs show real-time progress
-   **Zero downtime** - old version runs until new one is ready

---

### **🔧 Method 2: Railway CLI** _(For quick testing)_

```bash
# Deploy current local changes (without git commit)
railway up

# Deploy specific dockerfile
railway up --dockerfile railway.dockerfile

# Watch deployment progress
railway logs
```

**Use case:** Testing changes before committing to git

---

### **📱 Method 3: Railway Dashboard** _(One-click)_

```bash
# In Railway dashboard:
# 1. Go to your project
# 2. Click "Deploy" tab
# 3. Click "Deploy Latest Commit"
# 4. Done! ✅
```

---

### **⚡ Development Workflow**

#### **🎯 Typical Update Process:**

```bash
# 1. Code locally with hot reload
npm run dev              # Test changes locally

# 2. Commit and push
git add src/new-feature.py gui/new-component.js
git commit -m "🎬 Added genre-specific video templates"
git push origin main

# 3. Watch automatic deployment
railway logs --follow    # See live deployment logs

# 4. Test on live URL
curl https://your-app.railway.app/health
```

**⏱️ Total time:** ~3-5 minutes from code to live!

---

### **🔥 Hot Features for Updates**

#### **📊 Real-time Deployment Tracking**

```bash
# See what's happening during deployment
railway logs --follow

# Example output:
# ✅ Building Docker image...
# ✅ Installing dependencies...
# ✅ Starting application...
# 🚀 Deployment successful!
```

#### **🔄 Rollback Protection**

```bash
# If new version fails, Railway auto-reverts
railway rollback         # Manual rollback to previous version
railway deployments     # See all deployment history
```

#### **🌿 Environment Variables**

```bash
# Update environment variables instantly
railway variables set OPENAI_API_KEY=new-key-here
railway variables set MAX_WORKERS=4

# 🔄 App automatically restarts with new variables
```

---

### **📈 Advanced Update Strategies**

#### **🎯 Feature Branches** _(Professional workflow)_

```bash
# Create feature branch
git checkout -b feature/new-video-templates
git push origin feature/new-video-templates

# Railway can auto-deploy PR previews!
# Each branch gets its own URL for testing
```

#### **🔍 Environment-based Deployment**

```bash
# Development branch → Staging environment
# Main branch → Production environment

# Set in Railway dashboard:
# - Dev project: watches 'develop' branch
# - Prod project: watches 'main' branch
```

---

### **⚡ Speed Comparison**

| Update Method     | Time to Live  | Complexity      | Best For            |
| ----------------- | ------------- | --------------- | ------------------- |
| **Git Push**      | 2-3 minutes   | ⭐ Easy         | Daily development   |
| **Railway CLI**   | 1-2 minutes   | ⭐⭐ Medium     | Quick testing       |
| **Dashboard**     | 2-3 minutes   | ⭐ Easy         | Non-technical users |
| **Manual Server** | 15-30 minutes | ⭐⭐⭐⭐⭐ Hard | Never recommended   |

---

### **🎉 Example: Adding New Feature**

```bash
# 1. Add new video generation feature locally
# 2. Test with local Docker
docker-compose up --build

# 3. Commit and push
git add ai/new_model_integration.py
git commit -m "🤖 Added GPT-4 script generation"
git push origin main

# 4. Railway automatically:
#    ✅ Detects changes
#    ✅ Builds new Docker image
#    ✅ Tests health checks
#    ✅ Deploys with zero downtime
#    ✅ Sends deployment notification

# 5. New feature is live! 🚀
# https://your-app.railway.app (updated automatically)
```

**Result:** Your team can test the new feature immediately!

---

### **🛡️ Safety Features**

-   **🔄 Automatic rollback** if deployment fails
-   **🏥 Health checks** ensure app is working before switching traffic
-   **📊 Build logs** help debug any issues
-   **⏰ Deployment history** - see every change with timestamps
-   **🔒 Environment variable encryption** keeps secrets safe

---

_🚀 Happy coding! Update features in minutes, not hours!_
