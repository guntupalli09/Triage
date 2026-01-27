# Stripe Webhook Payment Status Fix

## Bug Analysis

### Issue
Stripe payments succeed, webhooks are delivered with 200 OK, but the frontend UI remains stuck on "Payment pending".

### Root Cause
**Race Condition**: When Stripe redirects the user to the success URL (`/results?token=...`), the webhook may not have arrived yet. The frontend had no automatic polling mechanism to check payment status, requiring manual page refresh.

### Identifier Flow (Verified Correct)
1. **Checkout Creation** (line 380-417):
   - Creates `app_session_id = secrets.token_urlsafe(18)`
   - Creates `token = sign_token(app_session_id)` → `{app_session_id}:{hash}`
   - Sets `client_reference_id=app_session_id` in Stripe checkout
   - Stores in `session_store[app_session_id]` with `paid: False`

2. **Webhook Handler** (line 470-503):
   - Extracts `app_session_id = session.get("client_reference_id")` ✓
   - Updates `session_store[app_session_id]["paid"] = True` ✓
   - Uses same identifier as checkout ✓

3. **Frontend Status Check** (line 489-515):
   - Receives `token` parameter
   - Verifies token: `app_session_id = verify_token(token)` ✓
   - Checks `session_store[app_session_id].get("paid")` ✓
   - Uses same identifier as webhook ✓

**Conclusion**: Identifiers are consistent. The issue is timing, not identifier mismatch.

## Fixes Applied

### 1. Added Payment Status API Endpoint
**Location**: `main.py` line 488-500

```python
@app.get("/api/payment-status")
async def payment_status(request: Request, token: str):
    """
    API endpoint for frontend to poll payment status.
    Returns JSON with paid status.
    """
    cleanup_expired_sessions()

    app_session_id = verify_token(token)
    if not app_session_id:
        return {"paid": False, "error": "Invalid or expired token"}

    if app_session_id not in session_store:
        return {"paid": False, "error": "Session not found or expired"}

    entry = session_store[app_session_id]
    return {
        "paid": entry.get("paid", False),
        "session_id": app_session_id
    }
```

**Purpose**: Provides a lightweight JSON endpoint for frontend polling.

### 2. Enhanced Webhook Handler with Idempotency
**Location**: `main.py` line 470-503

**Changes**:
- Added idempotency check (ignores duplicate events)
- Added `payment_status` verification from Stripe payload
- Improved error logging
- Returns 200 OK immediately after DB update

**Key improvements**:
```python
# Idempotency: Check if already marked as paid
if session_store[app_session_id].get("paid"):
    logger.info(f"Webhook received for already-paid session: {app_session_id} (idempotent)")
    return {"status": "ok", "message": "Already paid"}

# Verify payment status from Stripe
if payment_status != "paid":
    logger.warning(f"Webhook received but payment_status is '{payment_status}', not 'paid'")
    return {"status": "error", "message": f"Payment status is {payment_status}, not paid"}
```

### 3. Auto-Polling Frontend
**Location**: `main.py` line 503-515 (pending page HTML)

**Changes**:
- Replaced static "refresh manually" message with auto-polling JavaScript
- Polls `/api/payment-status` every 1 second
- Automatically reloads page when payment is confirmed
- Shows progress indicator and attempt count
- Falls back to manual refresh message after 30 attempts

**Key features**:
- Starts polling after 500ms delay (gives webhook time to arrive)
- Maximum 30 polls (~30 seconds)
- Graceful error handling
- Visual spinner and status updates

## End-to-End Flow (After Fix)

1. **User uploads contract** → `app_session_id` created → stored with `paid: False`
2. **Stripe checkout created** → `client_reference_id=app_session_id`
3. **User completes payment** → Stripe redirects to `/results?token={app_session_id}:{hash}`
4. **Frontend loads** → Checks `paid` status → If false, shows pending page with auto-polling
5. **Webhook arrives** (may be before or after step 4) → Updates `session_store[app_session_id]["paid"] = True` → Returns 200 OK
6. **Frontend polling** → Calls `/api/payment-status` → Receives `{"paid": true}` → Auto-reloads page
7. **Page reloads** → Checks `paid` status → Shows results

## Safety Improvements

✅ **Idempotent webhook**: Handles duplicate events gracefully  
✅ **Immediate 200 OK**: Returns response immediately after DB update  
✅ **Payment status verification**: Checks Stripe's `payment_status` field  
✅ **Auto-polling**: Frontend automatically checks status without user action  
✅ **Timeout handling**: Falls back to manual refresh after 30 seconds  
✅ **Error logging**: Comprehensive logging for debugging

## Testing

To verify the fix:

1. **Test normal flow**:
   - Upload contract → Complete payment → Should auto-redirect to results

2. **Test race condition**:
   - Upload contract → Complete payment → Immediately check if pending page auto-updates
   - Webhook should arrive within 1-2 seconds

3. **Test duplicate webhook**:
   - Trigger webhook twice → Should handle gracefully (idempotent)

4. **Test webhook delay**:
   - Simulate slow webhook → Frontend should poll and update when webhook arrives

## Files Changed

- `main.py`:
  - Line 470-503: Enhanced webhook handler
  - Line 488-500: Added `/api/payment-status` endpoint
  - Line 503-515: Enhanced pending page with auto-polling
