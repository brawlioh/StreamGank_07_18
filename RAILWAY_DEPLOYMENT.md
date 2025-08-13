# 🚀 Railway Deployment Guide for StreamGank

This guide will help you deploy your StreamGank Python backend to Railway and configure your Netlify frontend to communicate with it.

## 📋 Prerequisites

-   ✅ GitHub repository with your StreamGank project
-   ✅ Railway account (free signup at [railway.app](https://railway.app))
-   ✅ Netlify account for frontend deployment

## 🚂 Step 1: Deploy Backend to Railway

### 1.1 Connect Repository to Railway

1. Go to [railway.app](https://railway.app) and sign up/login
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your StreamGank repository
5. Railway will automatically detect Python and deploy

### 1.2 Configure Environment Variables

In your Railway project dashboard, add these environment variables:

```bash
# Required Environment Variables
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
CLOUDINARY_CLOUD_NAME=your_cloudinary_name
CLOUDINARY_API_KEY=your_cloudinary_key
CLOUDINARY_API_SECRET=your_cloudinary_secret
HEYGEN_API_KEY=your_heygen_key
CREATOMATE_API_KEY=your_creatomate_key

# Optional - Railway sets this automatically
PORT=8000
RAILWAY_ENVIRONMENT=production
```

### 1.3 Get Your Railway URL

After deployment, Railway will provide you with a URL like:

```
https://your-app-name.railway.app
```

**Important:** Copy this URL - you'll need it for the frontend configuration.

## 🌐 Step 2: Configure Frontend for Railway

### 2.1 Update GUI Configuration

Edit `gui/config.js` and replace the Railway URL:

```javascript
// Replace this line:
BACKEND_API_URL: 'https://streamgank-api.railway.app',

// With your actual Railway URL:
BACKEND_API_URL: 'https://your-actual-app-name.railway.app',
```

### 2.2 Update Auto-Detection URLs

In the same file, update all instances of the Railway URL:

```javascript
// Line ~25
STREAMGANK_CONFIG.BACKEND_API_URL = 'https://your-actual-app-name.railway.app';

// Line ~40
STREAMGANK_CONFIG.BACKEND_API_URL = 'https://your-actual-app-name.railway.app';
```

## 🚀 Step 3: Deploy Frontend to Netlify

### 3.1 Prepare Frontend Files

Your `gui/` folder contains:

-   `index.html` - Main interface
-   `js/script.js` - Frontend logic
-   `css/style.css` - Styling
-   `config.js` - Backend URL configuration

### 3.2 Deploy to Netlify

**Option A: Drag & Drop**

1. Go to [netlify.com](https://netlify.com)
2. Drag your `gui/` folder to the deploy area
3. Netlify will deploy and give you a URL like `https://amazing-name-123456.netlify.app`

**Option B: Git Integration**

1. Push your code to GitHub
2. Connect your repository to Netlify
3. Set build settings:
    - **Build command:** `echo "No build needed"`
    - **Publish directory:** `gui`

## 🔗 Step 4: Test the Connection

### 4.1 Test Railway Backend

Visit your Railway URL:

```
https://your-app-name.railway.app
```

You should see the StreamGank API dashboard.

Test the health endpoint:

```
https://your-app-name.railway.app/health
```

### 4.2 Test Frontend-Backend Connection

1. Open your Netlify frontend URL
2. Try generating a video
3. Check browser console for any connection errors
4. Monitor Railway logs for incoming requests

## 🐛 Troubleshooting

### Common Issues

**1. CORS Errors**

-   ✅ Already configured in `api_server.py`
-   Supports `*.netlify.app` and `*.netlify.com` domains

**2. Environment Variables Missing**

-   Check Railway dashboard > Variables tab
-   Ensure all required API keys are set

**3. Module Import Errors**

-   Check Railway build logs
-   Ensure all dependencies are in `requirements.txt`

**4. Frontend Can't Connect**

-   Verify Railway URL in `gui/config.js`
-   Check browser network tab for failed requests
-   Ensure Railway app is not sleeping (keep-alive)

### Railway Logs

Monitor your deployment:

```bash
# Install Railway CLI (optional)
npm install -g @railway/cli

# View logs
railway logs
```

## 📊 Monitoring & Scaling

### Railway Features

-   ✅ **Auto-scaling** - Handles traffic spikes
-   ✅ **Health checks** - Automatic restarts if unhealthy
-   ✅ **Metrics** - CPU, memory, request monitoring
-   ✅ **Custom domains** - Add your own domain

### Cost Optimization

-   **Hobby Plan**: $5/month - Perfect for development
-   **Pro Plan**: $20/month - Production ready
-   **Usage-based**: Pay only for what you use

## 🎯 Final Architecture

```
User Request Flow:
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Browser   │───▶│   Netlify    │───▶│   Railway   │
│             │    │  (Frontend)  │    │  (Backend)  │
└─────────────┘    └──────────────┘    └─────────────┘
                           │                    │
                           │                    ▼
                           │            ┌─────────────┐
                           │            │  Supabase   │
                           │            │ (Database)  │
                           │            └─────────────┘
                           │                    │
                           │                    ▼
                           │            ┌─────────────┐
                           │            │ External    │
                           │            │ APIs        │
                           │            │ (HeyGen,    │
                           │            │ Creatomate, │
                           │            │ OpenAI)     │
                           │            └─────────────┘
```

## ✅ Success Checklist

-   [ ] Railway backend deployed and accessible
-   [ ] All environment variables configured
-   [ ] Frontend `config.js` updated with Railway URL
-   [ ] Netlify frontend deployed
-   [ ] Frontend can communicate with Railway backend
-   [ ] Video generation workflow tested
-   [ ] Monitoring and logs configured

## 🆘 Support

If you encounter issues:

1. **Check Railway logs** for backend errors
2. **Check browser console** for frontend errors
3. **Verify environment variables** are set correctly
4. **Test API endpoints** directly with curl/Postman
5. **Review CORS configuration** if seeing connection issues

---

**🎉 Congratulations!** Your StreamGank application is now deployed with a professional architecture: Netlify frontend + Railway backend!
