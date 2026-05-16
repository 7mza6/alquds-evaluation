# 🚀 Host Your App on GitHub & Deploy

There are several ways to host your Al-Quds evaluation app using GitHub.

## Option 1: GitHub + Heroku (FREE & EASIEST)

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `alquds-evaluation` (or any name)
3. Description: "Al-Quds University Course Evaluation Web App"
4. Choose "Public" (so others can see it)
5. Click "Create repository"

### Step 2: Upload Files to GitHub

#### Option A: Using Git (Command Line)

```bash
# 1. Create a new folder
mkdir alquds-evaluation
cd alquds-evaluation

# 2. Download the files and put them here
# - simple_app.py
# - requirements.txt
# - SIMPLE_README.md

# 3. Initialize Git
git init
git add .
git commit -m "Initial commit"
git branch -M main

# 4. Connect to GitHub (replace USERNAME and REPO)
git remote add origin https://github.com/USERNAME/alquds-evaluation.git
git push -u origin main
```

#### Option B: Using GitHub Web Interface (NO COMMAND LINE)

1. Go to your repository
2. Click "Add file" → "Upload files"
3. Drag and drop:
   - `simple_app.py`
   - `requirements.txt`
   - `README.md`
4. Click "Commit changes"

### Step 3: Deploy to Heroku (FREE)

#### Install Heroku CLI

**Windows:**
- Download from https://devcenter.heroku.com/articles/heroku-cli
- Run installer

**Mac:**
```bash
brew tap heroku/brew && brew install heroku
```

**Linux:**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

#### Create Heroku App

```bash
# 1. Login to Heroku
heroku login

# 2. Create a new Heroku app
heroku create your-app-name

# 3. Deploy from GitHub
git push heroku main

# 4. View your app
heroku open
```

Your app will be live at: `https://your-app-name.herokuapp.com`

---

## Option 2: GitHub + Railway (EASIER ALTERNATIVE)

Railway is simpler than Heroku and still free.

### Step 1: Create GitHub Repo (same as Option 1)

### Step 2: Deploy to Railway

1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project"
4. Choose "Deploy from GitHub repo"
5. Select your `alquds-evaluation` repository
6. Railway automatically detects it's a Python app
7. Click "Deploy"

Your app will be live automatically! 🚀

---

## Option 3: GitHub Pages + Netlify (For STATIC Sites Only)

**Note:** This only works if you convert to static HTML. Your Flask app needs a server, so use Option 1 or 2 instead.

---

## Important: Create These Files

Before uploading to GitHub, make sure you have:

### 1. `requirements.txt` (already exists)
```
Flask==2.3.2
requests==2.31.0
Werkzeug==2.3.6
```

### 2. `Procfile` (NEW - for Heroku/Railway)

Create a file named `Procfile` (no extension):

```
web: python simple_app.py
```

### 3. `runtime.txt` (NEW - for Heroku/Railway)

Create a file named `runtime.txt`:

```
python-3.9.13
```

---

## Final GitHub Files Structure

Your repository should have:

```
alquds-evaluation/
├── simple_app.py          ← Main app
├── requirements.txt       ← Dependencies
├── Procfile              ← For Heroku/Railway
├── runtime.txt           ← Python version
├── README.md             ← Documentation
└── .gitignore            ← What to ignore
```

---

## Deploy Steps Summary

### For Heroku:

```bash
# 1. Login
heroku login

# 2. Create app
heroku create your-unique-name

# 3. Deploy
git push heroku main

# 4. View
heroku open
```

### For Railway:

```bash
# Just go to railway.app, connect GitHub, done! 🎉
```

---

## Security: Change Secret Key!

Before deploying, CHANGE the secret key in `simple_app.py`:

Find this line (around line 10):
```python
app.secret_key = 'your-secret-key-change-this'
```

Change to something like:
```python
app.secret_key = 'aF7kDx9Lm2Pp5Qr8Ts1Uv4Wx7Yz0abCdEfGhIjKlMnOpQrStUvWxYz'
```

Generate a random key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## View Your Deployed App

After deployment:

- **Heroku:** `https://your-app-name.herokuapp.com`
- **Railway:** `https://your-app-name.railway.app`

Share this URL with friends!

---

## Troubleshooting Deployment

### App crashes after deploy?

Check logs:

**Heroku:**
```bash
heroku logs --tail
```

**Railway:**
- Go to Railway dashboard → Click app → View logs

### Common issues:

1. **Missing Procfile** - Create it with correct content
2. **Wrong Python version** - Update `runtime.txt`
3. **Missing dependencies** - Update `requirements.txt`
4. **Port not set correctly** - Heroku/Railway set PORT automatically

---

## Advanced: Use Environment Variables

Instead of hardcoding the secret key, use environment variables:

```python
import os

app.secret_key = os.environ.get('SECRET_KEY', 'default-insecure-key')
```

On Heroku:
```bash
heroku config:set SECRET_KEY='your-secret-key'
```

On Railway:
- Go to Variables → Add `SECRET_KEY`

---

## Share Your Project

After deployment, share the link:

**On GitHub:**
- Go to your repo
- Copy the URL: `https://github.com/USERNAME/alquds-evaluation`
- Share in README badge style:

```markdown
# Al-Quds Course Evaluation

Live demo: https://your-app-name.herokuapp.com

GitHub: https://github.com/USERNAME/alquds-evaluation
```

---

## Next Steps

1. ✅ Create GitHub repo
2. ✅ Upload files (including Procfile)
3. ✅ Change secret key
4. ✅ Deploy to Heroku or Railway
5. ✅ Test the live app
6. ✅ Share with friends!

---

## Free Options Compared

| Service | Price | Setup Time | Limits |
|---------|-------|-----------|--------|
| Heroku | Free (limited) | 10 min | 550 hrs/month |
| Railway | Free | 5 min | Good free tier |
| Render | Free | 10 min | 15 min idle limit |
| PythonAnywhere | Free | 5 min | Limited features |

**Recommendation: Use Railway - it's the easiest!**

---

## Getting Help

- **Heroku Docs:** https://devcenter.heroku.com/
- **Railway Docs:** https://docs.railway.app/
- **Flask Docs:** https://flask.palletsprojects.com/

---

**That's it! Your app will be live online!** 🎉
