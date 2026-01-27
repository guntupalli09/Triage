# Stripe Live Mode - Final Checklist

## ✅ Configuration Checklist

Before going live, verify these settings in your `.env` file:

### Required Settings

- [ ] **DEV_MODE=false** (must be `false` for production)
- [ ] **STRIPE_SECRET_KEY=sk_live_...** (live secret key, not test)
- [ ] **STRIPE_WEBHOOK_SECRET=whsec_...** (from live webhook)
- [ ] **OPENAI_API_KEY=sk-...** (required in production mode)

### Recommended Settings

- [ ] **BASE_URL=https://triage-gamma.vercel.app** (optional but recommended for stable redirects)

### Stripe Dashboard Setup

- [ ] Webhook endpoint created in **Live mode**
- [ ] Webhook URL: `https://triage-gamma.vercel.app/stripe-webhook`
- [ ] Event selected: `checkout.session.completed`
- [ ] Webhook signing secret copied to `.env`

## Verification Steps

1. **Check your `.env` file contains:**
   ```env
   DEV_MODE=false
   STRIPE_SECRET_KEY=sk_live_YOUR_KEY
   STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET
   OPENAI_API_KEY=sk-YOUR_KEY
   BASE_URL=https://triage-gamma.vercel.app
   ```

2. **Restart your application**
   - **Local testing**: `uvicorn main:app --reload` (or without `--reload` for production-like mode)
   - **Vercel**: Redeploy after updating environment variables in Vercel Dashboard

3. **Check startup logs** - you should see:
   ```
   Mode=PROD | Stripe=ON | OpenAI=REQUIRED
   Application BASE_URL set to: https://triage-gamma.vercel.app
   ```

4. **Test the payment flow:**
   - Upload a contract
   - Complete a test payment (use Stripe test card: 4242 4242 4242 4242)
   - Verify webhook is received (check Stripe Dashboard → Webhooks → Recent events)

## Important Notes

⚠️ **For Vercel Deployment:**
- Make sure environment variables are set in Vercel Dashboard → Settings → Environment Variables
- After updating `.env`, you need to redeploy on Vercel for changes to take effect
- Vercel automatically provides HTTPS, so webhook security is handled

⚠️ **Testing:**
- Even in live mode, you can use Stripe test cards for testing
- Monitor Stripe Dashboard → Payments to see transactions
- Check Stripe Dashboard → Webhooks → Your endpoint → Recent events for webhook delivery

## If Something Goes Wrong

1. **Check Vercel logs** for startup errors
2. **Check Stripe Dashboard** → Webhooks → Recent events for delivery failures
3. **Verify environment variables** are set correctly in Vercel Dashboard
4. **Test webhook endpoint** manually using Stripe CLI:
   ```bash
   stripe trigger checkout.session.completed
   ```
