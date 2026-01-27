# Stripe Live Mode Setup

## Switching from Sandbox/Test to Live Mode

To switch from Stripe test mode to live/production mode, you need to:
1. Create a webhook endpoint in Stripe's live mode (if you don't have one)
2. Get your live API keys
3. Update your `.env` file with live Stripe keys

### Steps

1. **Get Live Stripe Keys from Stripe Dashboard**
   - Go to https://dashboard.stripe.com/
   - Switch to **Live mode** (toggle in top right)
   - Navigate to **Developers** → **API keys**
   - Copy your **Secret key** (starts with `sk_live_...`)
   - Copy your **Publishable key** (starts with `pk_live_...`) if needed

2. **Create Live Webhook Endpoint**
   
   If you don't have a webhook in live mode yet, create one:
   
   - In Stripe Dashboard (Live mode), go to **Developers** → **Webhooks**
   - Click **Add endpoint**
   - Enter your webhook URL: `https://triage-gamma.vercel.app/stripe-webhook`
     - This is your production webhook endpoint
     - The endpoint must be HTTPS in production
   - Select events to listen for:
     - `checkout.session.completed` (required)
   - Click **Add endpoint**
   - After creation, click on the webhook to view details
   - Copy the **Signing secret** (starts with `whsec_...`)
   
   **Note**: If you're testing locally, you can use Stripe CLI to forward webhooks:
   ```bash
   stripe listen --forward-to localhost:8000/stripe-webhook
   ```
   This will give you a test webhook secret for local testing, but you'll still need a live webhook for production.

3. **Update `.env` File**

   Replace test keys with live keys:

   ```env
   # Stripe Configuration (LIVE MODE)
   STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_SECRET_KEY_HERE
   STRIPE_WEBHOOK_SECRET=whsec_YOUR_LIVE_WEBHOOK_SECRET_HERE
   
   # Production Mode
   DEV_MODE=false
   ```

   **Important**: 
   - Live keys start with `sk_live_` (not `sk_test_`)
   - Live webhook secrets start with `whsec_` (same format, but from live webhook)
   - Set `DEV_MODE=false` for production mode
   - **Webhook URL must be HTTPS** in production (Stripe requires HTTPS for live webhooks)
   - Your webhook endpoint is: `https://triage-gamma.vercel.app/stripe-webhook`

4. **Verify Configuration**

   **For Local Testing:**
   ```bash
   uvicorn main:app --reload
   ```
   (`--reload` auto-restarts on code changes - use for development only)

   **For Production (Vercel):**
   - No need to run manually - Vercel handles deployment
   - After updating environment variables in Vercel Dashboard, redeploy
   - Vercel will automatically restart with new environment variables

   Check the startup logs - you should see:
   ```
   Mode=PROD | Stripe=ON | OpenAI=REQUIRED
   Application BASE_URL set to: https://triage-gamma.vercel.app
   ```

### Key Differences: Test vs Live

| Feature | Test Mode | Live Mode |
|---------|-----------|-----------|
| Secret Key Prefix | `sk_test_...` | `sk_live_...` |
| Publishable Key Prefix | `pk_test_...` | `pk_live_...` |
| Charges | No real money | **Real charges** |
| Webhook Secret | From test webhook | From live webhook |
| Dashboard | Test mode toggle | Live mode toggle |

### Security Notes

⚠️ **WARNING**: Live mode processes **real payments**. Ensure:
- Your `.env` file is in `.gitignore` (never commit live keys)
- Use HTTPS in production
- Verify webhook endpoint is secure
- Test thoroughly in test mode first

### Testing the Switch

1. **Before going live**: Test all payment flows in test mode
2. **After switching**: Make a small test payment to verify
3. **Monitor**: Check Stripe Dashboard → Payments to see live transactions

### Troubleshooting

**Issue**: "STRIPE_SECRET_KEY is required in production mode"
- **Solution**: Ensure `DEV_MODE=false` and `STRIPE_SECRET_KEY` is set in `.env`

**Issue**: Webhook not working
- **Solution**: 
  - Verify `STRIPE_WEBHOOK_SECRET` matches the live webhook signing secret
  - Check webhook endpoint URL is accessible from Stripe (must be HTTPS in production)
  - Ensure webhook is listening for `checkout.session.completed` events
  - Check Stripe Dashboard → Webhooks → Your endpoint → Recent events for delivery status
  - Verify your server is publicly accessible (not behind a firewall blocking Stripe's IPs)

**Issue**: Still seeing test charges
- **Solution**: Verify keys start with `sk_live_` (not `sk_test_`)
- Check Stripe Dashboard is in Live mode
