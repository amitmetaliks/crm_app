# Hands-free WhatsApp (Meta Cloud API) — Setup

The app already supports **free tap-to-send** WhatsApp (opens WhatsApp pre-filled).
This guide enables **automatic server-side sending** (e.g. one-tap payment reminders)
via Meta's official WhatsApp Business Cloud API.

> Note: Meta requires **pre-approved message templates** for *proactive* messages
> (messages to a dealer who hasn't messaged you in the last 24h). Plain text only
> works inside that 24h reply window.

## One-time account setup (you do this on Meta)

1. Create a **Meta Business account** → https://business.facebook.com
2. Go to **developers.facebook.com** → Create App → type **Business** → add the
   **WhatsApp** product.
3. Add a **dedicated WhatsApp number** (it must NOT already be active on the normal
   WhatsApp app). Note the **Phone Number ID** and the **WhatsApp Business Account ID**.
4. Generate a **permanent access token** (System User token with `whatsapp_business_messaging`).
5. Create + submit a **message template** for payment reminders, e.g. name
   `payment_reminder`, language `en`, body:
   `Dear {{1}}, a reminder from TRIAM A+: ₹{{2}} is outstanding on your account. Kindly arrange payment. Thank you.`
   Wait for Meta to **approve** it (usually minutes–hours).

## Configure the site (Dexciss runs these, or us on dev)

```bash
bench --site <site> set-config crm_whatsapp_token "<permanent-access-token>"
bench --site <site> set-config crm_whatsapp_phone_id "<phone-number-id>"
bench --site <site> set-config crm_whatsapp_reminder_template "payment_reminder"
bench --site <site> clear-cache
```

That's it. Once these are set:
- **Collections → Remind** sends the approved template automatically (no tapping).
- If the token/template isn't set, the app silently falls back to the free
  tap-to-send link — so nothing breaks.

## Cost
Meta gives a free tier of business-initiated conversations per month; beyond that it's
pay-per-conversation (varies by country). Service/utility templates (like payment
reminders) are low-cost in India. Check current Meta WhatsApp pricing.

## Endpoints (already built in `crm_app/whatsapp.py`)
- `is_configured`, `send_text`, `send_template`, `send_payment_reminder`
