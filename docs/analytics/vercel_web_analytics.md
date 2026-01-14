# Vercel Web Analytics Integration

## Overview

This project has been integrated with **Vercel Web Analytics** to track user visits and page views. Vercel Web Analytics provides privacy-preserving analytics that measure real user experiences without collecting personally identifiable information.

## Setup Requirements

To enable Vercel Web Analytics for this project:

### 1. Create a Vercel Account
If you don't have one, [sign up for free](https://vercel.com/signup).

### 2. Create or Deploy Project to Vercel
Deploy this project to Vercel using the [Vercel Dashboard](https://vercel.com) or the Vercel CLI.

### 3. Enable Web Analytics in Vercel Dashboard
1. Go to the [Vercel Dashboard](/dashboard)
2. Select your project
3. Click the **Analytics** tab
4. Click **Enable** from the dialog

> **💡 Note:** Enabling Web Analytics will add new routes (scoped at `/_vercel/insights/*`) after your next deployment.

## Implementation Details

### Frontend Integration

For this FastAPI application with plain HTML templates, Vercel Web Analytics is implemented by adding two script tags to the HTML `<head>` section:

```html
<!-- Vercel Web Analytics -->
<script>
    window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
</script>
<script defer src="/_vercel/insights/script.js"></script>
```

**Files modified:**
- `templates/index.html` - Main landing page
- `templates/results.html` - Analysis results page
- `templates/pdf_report.html` - PDF report template (for web viewing)

### How It Works

1. The first script tag initializes the analytics queue
2. The second script tag (loaded with `defer`) loads the Vercel analytics script from `/_vercel/insights/script.js`
3. When deployed on Vercel, the `/_vercel/insights/script.js` endpoint becomes available automatically
4. The script tracks page views and visitor interactions without user intervention

## Deployment Notes

- **Local Development**: The analytics script will attempt to load but will fail gracefully since `/_vercel/insights/script.js` won't be available locally
- **Vercel Deployment**: Once deployed on Vercel, analytics will be automatically collected
- **Data Collection**: Starts immediately after your next deployment to Vercel
- **No Route Support**: This implementation uses plain HTML, so there is no automatic route detection. Each page load is tracked as a separate view

## Viewing Analytics Data

Once your app is deployed and users have visited:

1. Go to the [Vercel Dashboard](/dashboard)
2. Select your project
3. Click the **Analytics** tab
4. After a few days of visitor data, you'll be able to:
   - View page views and visitor counts
   - Filter data by time period
   - Analyze traffic patterns

## Privacy & Data Compliance

Vercel Web Analytics is designed with privacy-first principles:
- **No cookies**: Does not use cookies for tracking
- **No personal data**: Does not collect PII (personally identifiable information)
- **GDPR compliant**: Meets GDPR requirements without requiring consent
- **Privacy-preserving**: Uses server-side analytics to avoid client-side tracking

For more information, see [Vercel's Privacy & Compliance Documentation](/docs/analytics/privacy-policy).

## Features Available

**Free Plan:**
- Page views and visitor metrics
- Traffic overview
- Real-time monitoring

**Pro & Enterprise Plans:**
- Advanced filtering and segmentation
- Custom events tracking (track button clicks, form submissions, purchases, etc.)
- Detailed performance insights
- Priority support

### Adding Custom Events (Pro/Enterprise)

If you upgrade to Pro or Enterprise, you can add custom event tracking:

```javascript
window.va('event', {
  name: 'purchase',
  value: productPrice
});
```

See [Custom Events Documentation](/docs/analytics/custom-events) for more details.

## Troubleshooting

### Analytics Not Showing Up

1. **Check deployment**: Ensure the project is deployed on Vercel
2. **Browser network tab**: Should see a request to `/_vercel/insights/view` when visiting pages
3. **Wait for data**: It may take a few hours for data to appear in the dashboard
4. **Check analytics is enabled**: Verify in the Vercel Dashboard that Web Analytics is enabled for your project

### Script Loading Fails Locally

This is expected - the `/_vercel/insights/script.js` endpoint is only available when deployed on Vercel. Locally, the script gracefully fails and doesn't affect the application.

## Disabling Analytics

To disable analytics:

1. Go to Vercel Dashboard
2. Select your project
3. Go to Analytics tab
4. Click "Disable"

Alternatively, remove the analytics scripts from the HTML templates:

```diff
- <!-- Vercel Web Analytics -->
- <script>
-     window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
- </script>
- <script defer src="/_vercel/insights/script.js"></script>
```

## References

- [Vercel Web Analytics Official Documentation](https://vercel.com/docs/analytics)
- [Vercel Analytics Getting Started](https://vercel.com/docs/analytics/getting-started)
- [Privacy & Compliance Standards](https://vercel.com/docs/analytics/privacy-policy)
- [Limits and Pricing](https://vercel.com/docs/analytics/limits-and-pricing)
- [Troubleshooting Guide](https://vercel.com/docs/analytics/troubleshooting)
