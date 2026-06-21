# Twilio WhatsApp Sandbox Setup Guide

Step-by-step instructions to get your Twilio WhatsApp sandbox working with Krid AI.

---

## Step 1: Create a Twilio Account

1. Go to [twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up for a free account (no credit card required for sandbox)
3. Verify your phone number when prompted

---

## Step 2: Get Your Twilio Credentials

1. Log in to the [Twilio Console](https://console.twilio.com/)
2. On the dashboard, you'll see:
   - **Account SID** — starts with `AC...`
   - **Auth Token** — click "Show" to reveal it
3. Copy both values into your `.env` file:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

---

## Step 3: Activate the WhatsApp Sandbox

1. In the Twilio Console, go to **Messaging → Try it out → Send a WhatsApp message**
   - Or navigate directly to: [console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. You'll see a sandbox phone number (usually `+1 415 523 8886`) and a join code like `join <your-code>`
3. **Send a WhatsApp message** from your phone to `+1 415 523 8886` with the join code:
   ```
   join <your-code>
   ```
4. You should receive a confirmation reply

> **Note:** Each user who wants to test must send the join code. The sandbox only replies to opted-in numbers.

---

## Step 4: Configure the Webhook URL

1. In the Twilio Console, go to **Messaging → Try it out → Send a WhatsApp message**
2. Scroll down to **Sandbox Configuration** (or go to **Messaging → Settings → WhatsApp sandbox settings**)
3. Set the **"When a message comes in"** webhook URL to your server:
   - **Local dev (with ngrok):**
     ```
     https://<your-ngrok-id>.ngrok-free.app/api/webhooks/whatsapp
     ```
   - **Deployed on Render:**
     ```
     https://<your-app>.onrender.com/api/webhooks/whatsapp
     ```
4. Set the HTTP method to **POST**
5. Click **Save**

---

## Step 5: Expose Your Local Server (for development)

If running locally, you need a public URL. Use [ngrok](https://ngrok.com/):

```bash
# Install ngrok (if not already installed)
# See https://ngrok.com/download

# Start your FastAPI server
uvicorn app.main:app --reload --port 8080

# In another terminal, expose port 8080
ngrok http 8080
```

Copy the `https://xxxx.ngrok-free.app` URL and paste it into Twilio's webhook configuration (Step 4).

---

## Step 6: Test End-to-End

1. Make sure Ollama is running: `ollama serve`
2. Make sure FastAPI is running: `uvicorn app.main:app --reload --port 8080`
3. Make sure ngrok is running and the webhook URL is set in Twilio
4. Send a WhatsApp message from your phone to the sandbox number
5. Watch the server logs — you should see all 4 LangGraph nodes execute:
   ```
   [Webhook] Inbound from +919876543210: 'Hello!' | SID=SMxxxxxxx
   [Acknowledge] session=tenant_a_919876543210 | msg_id=SMxxxxxxx
   [Context] tenant=tenant_a | history_len=0 | media_library_keys=[...]
   [LLM] Reply preview: Welcome to our luxury furniture store...
   [Dispatcher] Done for session=tenant_a_919876543210 | media=False
   ```
6. You should receive the bot's reply on your phone
7. Open `http://localhost:8080` — the conversation should appear on the dashboard

---

## Sandbox Limitations

- **24-hour window:** You can only send free-form messages within 24 hours of the customer's last message. After that, you must use approved templates.
- **Opt-in required:** Each test user must send the `join <code>` message to opt in.
- **Single number:** The sandbox uses a shared number (`+14155238886`). For production, you'll need an approved WhatsApp Business number.
- **Rate limits:** The sandbox has lower rate limits than production accounts.

---

## Upgrading to Production

To use Twilio WhatsApp in production:

1. Apply for a WhatsApp Business Profile via Twilio Console
2. Get a dedicated WhatsApp-enabled phone number
3. Submit message templates for approval
4. Update `TWILIO_WHATSAPP_NUMBER` in your `.env` to your production number
