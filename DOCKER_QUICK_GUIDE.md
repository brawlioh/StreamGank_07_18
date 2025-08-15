# 🚀 StreamGank Docker Quick Reference

**⚡ Fast commands to avoid re-downloading dependencies!**

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
# Stop containers
docker-compose -f docker-compose.vm-optimized.yml down

# Quick rebuild (uses cache - FAST!)
bash vm-docker-management.sh vm-build

# Start again
bash vm-docker-management.sh vm-start
```

**Time:** ~1-2 seconds (uses Docker cache)  
**Use when:** You modified any code files

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

| **What Changed?**                     | **Command**             | **Time** |
| ------------------------------------- | ----------------------- | -------- |
| 🔧 **Code files** (py, js, html, css) | `vm-build` → `vm-start` | 1-2 sec  |
| 📝 **`.env` only**                    | `vm-start`              | 10 sec   |
| 📦 **`requirements.txt`**             | `vm-rebuild`            | 3-5 min  |
| 📦 **`package.json`**                 | `vm-rebuild`            | 3-5 min  |
| 🐳 **`Dockerfile`**                   | `vm-rebuild`            | 3-5 min  |

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

| **Goal**     | **Fast Command**                 |
| ------------ | -------------------------------- |
| Start app    | `vm-start`                       |
| Code changed | `down` → `vm-build` → `vm-start` |
| .env changed | `down` → `vm-start`              |
| Stop app     | `down`                           |
| New packages | `vm-rebuild`                     |

---

## 🎯 **Remember**

-   **Code changes = `vm-build` (fast)**
-   **New packages = `vm-rebuild` (slow)**
-   **When in doubt, try `vm-build` first!**

---

_🚀 Happy coding! No more waiting for unnecessary downloads!_
