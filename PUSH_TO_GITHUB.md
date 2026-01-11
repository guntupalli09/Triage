# Push to GitHub - Instructions

## Step 1: Create Repository on GitHub

1. Go to https://github.com/new
2. **Repository name**: `Triage`
3. **Description**: `Your AI Contract Risk evaluator`
4. Choose **Public** or **Private** (your choice)
5. **IMPORTANT**: Do NOT check any of these:
   - ❌ Add a README file
   - ❌ Add .gitignore
   - ❌ Choose a license
6. Click **"Create repository"**

## Step 2: Push Your Code

### Option A: Using the PowerShell Script (Recommended)

```powershell
.\setup-github.ps1
```

Follow the prompts to enter your GitHub username.

### Option B: Manual Commands

Replace `YOUR_USERNAME` with your GitHub username:

```powershell
# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/Triage.git

# Push to GitHub
git push -u origin main
```

### Option C: Using SSH (if you have SSH keys set up)

```powershell
git remote add origin git@github.com:YOUR_USERNAME/Triage.git
git push -u origin main
```

## Step 3: Verify

After pushing, visit:
```
https://github.com/YOUR_USERNAME/Triage
```

You should see all your files including:
- Source code (main.py, rules_engine.py, evaluator.py)
- Templates (index.html, results.html)
- Documentation (docs/ folder)
- README.md
- requirements.txt

## Troubleshooting

### Authentication Issues

If you get authentication errors:

1. **For HTTPS**: You may need to use a Personal Access Token
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a token with `repo` scope
   - Use the token as your password when prompted

2. **For SSH**: Make sure your SSH key is added to GitHub
   - Check: `ssh -T git@github.com`

### Remote Already Exists

If you get "remote origin already exists":

```powershell
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/Triage.git
git push -u origin main
```

### Branch Name Issues

If you get branch name errors:

```powershell
git branch -M main
git push -u origin main
```

## What's Included

The repository includes:
- ✅ Complete source code
- ✅ Full documentation suite
- ✅ Templates and UI
- ✅ Requirements and configuration
- ✅ .gitignore (excludes .env, __pycache__, etc.)

**Note**: The `.env` file is NOT included (it's in .gitignore) for security. Users will need to create their own from `.env.example`.
