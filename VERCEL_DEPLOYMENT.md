# Vercel Deployment Guide

## Issue: Serverless Function Size Exceeds 250 MB

This guide addresses the Vercel deployment error about serverless function size.

## Solutions Applied

### 1. Removed Large Dependencies
- **Removed `scipy` and `numpy`** from `requirements.txt` (only needed for experiments/)
- These packages are ~100-150 MB each when installed
- They're only used in `experiments/statistical_analysis.py`, not in production code

### 2. Created `.vercelignore`
- Excludes `experiments/` directory (2000+ files, likely 100+ MB)
- Excludes test files, documentation, and development files
- Excludes large PDF/DOCX files from research directories

### 3. Optimized Requirements
- `requirements.txt` - Production dependencies only (for Vercel)
- `requirements-dev.txt` - Includes dev dependencies (for local development)
- `requirements-prod.txt` - Explicit production list (backup)

## Deployment Steps

### 1. Verify Files Are Excluded

Check that `.vercelignore` is working:
```bash
# Check what would be deployed (Vercel uses .vercelignore)
# The experiments/ directory should NOT be included
```

### 2. Deploy to Vercel

```bash
# If using Vercel CLI
vercel --prod

# Or push to GitHub (if connected to Vercel)
git add .
git commit -m "Optimize for Vercel deployment"
git push
```

### 3. Verify Deployment Size

After deployment, check Vercel dashboard:
- Go to your deployment
- Check "Function Logs" or "Build Logs"
- Verify the function size is under 250 MB

## Expected Size Reduction

**Before:**
- scipy: ~150 MB
- numpy: ~100 MB
- experiments/: ~50-100 MB (2000+ files)
- Total: ~300-350 MB ❌

**After:**
- Production dependencies only: ~50-80 MB
- Excluded experiments/: 0 MB
- Total: ~50-80 MB ✅

## If Still Exceeding 250 MB

### Option 1: Further Optimize Dependencies

Some dependencies might be large. Check sizes:
```bash
pip install --dry-run -r requirements.txt
# Or use pipdeptree to see dependency tree
```

Consider alternatives:
- `xhtml2pdf` might be large - consider if PDF generation is critical
- `PyPDF2` - lightweight, should be fine
- `python-docx` - lightweight, should be fine

### Option 2: Use Vercel's Max Lambda Size Setting

Already configured in `vercel.json`:
```json
{
  "config": {
    "maxLambdaSize": "250mb"
  }
}
```

### Option 3: Split into Multiple Functions

If still too large, consider:
- Separate API routes into different functions
- Use Vercel's monorepo support
- Deploy only essential routes

### Option 4: Use External Storage

Move large static files to:
- AWS S3
- Cloudflare R2
- Vercel Blob Storage

## Local Development

For local development with all dependencies:

```bash
# Install all dependencies (including dev/experimental)
pip install -r requirements-dev.txt
```

## Production vs Development

- **Vercel (Production)**: Uses `requirements.txt` (production only)
- **Local Development**: Use `requirements-dev.txt` (includes tests, experiments)

## Monitoring

After deployment:
1. Check function size in Vercel dashboard
2. Monitor cold start times (should be <5 seconds)
3. Check if all routes work correctly
4. Verify file uploads work (if using file storage)

## Troubleshooting

### Error: "Module not found"
- Ensure all production dependencies are in `requirements.txt`
- Check that imports in `main.py`, `rules_engine.py`, `evaluator.py` don't require scipy/numpy

### Error: "Function timeout"
- Check `vercel.json` - `maxDuration` is set to 30 seconds
- Optimize slow operations (LLM calls, file processing)

### Error: "Build failed"
- Check Vercel build logs
- Verify Python version (set to 3.11 in `vercel.json`)
- Check that all required files are present

## Files Created/Modified

- ✅ `.vercelignore` - Excludes large directories
- ✅ `vercel.json` - Vercel configuration
- ✅ `requirements.txt` - Production dependencies only
- ✅ `requirements-dev.txt` - Development dependencies
- ✅ `requirements-prod.txt` - Explicit production list

## Next Steps

1. **Deploy and verify** function size is under 250 MB
2. **Test all endpoints** to ensure nothing broke
3. **Monitor performance** - cold starts, response times
4. **Consider further optimizations** if needed
