#!/usr/bin/env python3
# Har Har Mahadev
# Flask Web Service for Email Sender — Brevo API Edition

import base64
import time
import random
import os
import logging
import requests
import threading
import json
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Load .env file (local dev) ──────────────────────────────────────────────
def load_env_file():
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.isfile(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value

load_env_file()

# ── Config from environment ─────────────────────────────────────────────────
BREVO_API_KEY    = os.environ.get("BREVO_API_KEY", "")
SENDER_ADDRESS   = os.environ.get("SENDER_ADDRESS", "")          # must be verified in Brevo
SENDER_NAME      = os.environ.get("SENDER_NAME", "Akash Singh")
RESUME_FILE      = os.environ.get("RESUME_FILE", "AKASHSINGH_RESUME_V9.pdf")
API_KEY          = os.environ.get("API_KEY", "")                  # optional auth for endpoints
AUTO_SEND        = os.environ.get("AUTO_SEND", "true").lower() == "true"

BREVO_API_URL    = "https://api.brevo.com/v3/smtp/email"

# ── Recipients ──────────────────────────────────────────────────────────────
RECIPIENTS_FILE = "recipients.json"

def load_recipients():
    """Load recipients from JSON file."""
    if not os.path.exists(RECIPIENTS_FILE):
        return {}
    try:
        with open(RECIPIENTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading recipients: {e}")
        return {}

def save_recipients(recipients_dict):
    """Save recipients to JSON file."""
    try:
        with open(RECIPIENTS_FILE, "w") as f:
            json.dump(recipients_dict, f, indent=2)
        logger.info(f"Saved {len(recipients_dict)} recipients to {RECIPIENTS_FILE}")
    except Exception as e:
        logger.error(f"Error saving recipients: {e}")

# Load recipients on startup
recipients = load_recipients()

# ── Email HTML body ─────────────────────────────────────────────────────────
BODY_TEMPLATE = """
<html>
<body style="font-family:Arial, sans-serif; line-height:1.6; font-size:16px; color:#222; max-width:900px;">

<p>Hi,</p>

<p>
I'm <b>Hrithik Raj</b>, a CSE graduate from <b>Delhi Technological University (2026)</b>
looking for <b>Software Development Engineer (SDE)</b> related opportunities.
</p>

<p>
<b>A quick snapshot:</b><br>

• <b>SDE Intern at Imperier Holdings</b> built fullstack tools for 50+ analysts,
improving data retrieval speed by 35%<br>

• Built <b>AI/LLM projects</b> including a RAG-based PDF Analyzer and a Resume
Matching System with 90%+ accuracy<br>

• <b>LeetCode Knight</b> (1939 rating) | <b>450+</b> DSA problems solved |
<b>JEE 99.45%ile</b> (AIR 4494)<br>

• <b>Tech Stack:</b> MERN, Python, FastAPI, PostgreSQL, LangChain, RAG
</p>

<p>
I'd love to be considered for any open SDE-related roles.
I've attached my resume and portfolio if you'd like a deeper look.
</p>

<p>
<b>Resume:</b>
<a href="https://drive.google.com/file/d/1SfHMIOi_XGKYO_QlLAfAYapB_DJ0UuME/view?usp=drive_link">
View Resume
</a>
<br>

<b>Portfolio:</b>
<a href="https://hrx027.app">
View Portfolio
</a>
</p>

<br>

<p>
Best Regards,<br><br>

<b>Hrithik Raj</b><br>
📞 +91 7029775009<br>
📧 <a href="mailto:hrx027@gmail.com">hrx027@gmail.com</a><br>
🔗 <a href="https://www.linkedin.com/in/hrx027">LinkedIn Profile</a>
</p>

</body>
</html>
"""

# ── Global status ───────────────────────────────────────────────────────────
sending_status = {
    "is_sending": False,
    "last_run":   None,
    "results":    [],
    "stop_flag":  False,
    "delay":      30,
    "current_message": "",
}

# ── Helpers ─────────────────────────────────────────────────────────────────
def keep_alive_during_wait(delay_secs: int, service_url: str):
    """Ping /health every 10 s during inter-email delay to prevent Render spin-down."""
    ping_interval = 10
    elapsed = 0
    while elapsed < delay_secs:
        time.sleep(ping_interval)
        elapsed += ping_interval
        try:
            requests.get(service_url, timeout=5)
            logger.debug(f"🔄 Keep-alive ping sent ({elapsed}s / {delay_secs}s)")
        except Exception as e:
            logger.debug(f"⚠️  Keep-alive ping failed: {e}")


def send_single_email_brevo(
    recipient_email: str,
    hiring_manager: str,
    company: str,
    resume_bytes: bytes,
    resume_filename: str,
):
    """Send one email via the Brevo Transactional Email API."""
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not set.")
    if not SENDER_ADDRESS:
        raise RuntimeError("SENDER_ADDRESS is not set.")

    html_body   = BODY_TEMPLATE.format(hiring_manager=hiring_manager, company=company)
    resume_b64  = base64.b64encode(resume_bytes).decode("utf-8")

    payload = {
        "sender": {
            "name":  SENDER_NAME,
            "email": SENDER_ADDRESS,
        },
        "to": [{"email": recipient_email}],
        "subject": f"Application for SDE Fresher in {company}",
        "htmlContent": html_body,
        "attachment": [
            {
                "name":    resume_filename,
                "content": resume_b64,   # Brevo expects base64
            }
        ],
    }

    headers = {
        "accept":       "application/json",
        "content-type": "application/json",
        "api-key":      BREVO_API_KEY,
    }

    logger.info(f"   → POST {BREVO_API_URL}")
    logger.info(f"   → From: {SENDER_NAME} <{SENDER_ADDRESS}>")
    logger.info(f"   → To:   {recipient_email}")

    resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)

    if resp.status_code in (200, 201):
        return resp.json()

    # Surface clear error messages
    try:
        err_body = resp.json()
        err_msg  = err_body.get("message", resp.text)
        err_code = err_body.get("code", "")
    except Exception:
        err_msg  = resp.text
        err_code = ""

    if resp.status_code == 401:
        raise RuntimeError(f"401 Unauthorized — check your BREVO_API_KEY. Detail: {err_msg}")
    if resp.status_code == 400:
        raise RuntimeError(f"400 Bad Request [{err_code}] — {err_msg}")
    if resp.status_code == 403:
        raise RuntimeError(
            f"403 Forbidden — sender address '{SENDER_ADDRESS}' may not be verified in Brevo. "
            f"Detail: {err_msg}"
        )
    raise RuntimeError(f"Brevo API error {resp.status_code}: {err_msg}")


# ── Background sender ───────────────────────────────────────────────────────
def send_emails_async(min_delay_seconds=30, max_delay_seconds=40):
    global sending_status

    logger.info("🚀 Starting email sending process (Brevo API)…")
    sending_status["is_sending"] = True
    sending_status["results"]    = []
    sending_status["stop_flag"]  = False
    sending_status["current_message"] = "Starting email sending process…"

    # ── Pre-flight checks ────────────────────────────────────────────────────
    if not BREVO_API_KEY:
        _fatal("BREVO_API_KEY environment variable is not set.")
        return
    if not SENDER_ADDRESS:
        _fatal("SENDER_ADDRESS environment variable is not set.")
        return
    if not os.path.isfile(RESUME_FILE):
        _fatal(f"Resume file not found: {RESUME_FILE}")
        return
    if len(recipients) == 0:
        _fatal("No recipients found!")
        return

    sending_status["current_message"] = f"Loading resume: {RESUME_FILE}"
    logger.info(f"📄 Loading resume: {RESUME_FILE}")
    with open(RESUME_FILE, "rb") as fh:
        resume_bytes = fh.read()
    resume_filename = os.path.basename(RESUME_FILE)
    logger.info(f"✅ Resume loaded — {len(resume_bytes):,} bytes")

    # Keep-alive URL (Render sets RENDER_EXTERNAL_URL automatically)
    base_url    = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
    service_url = base_url.rstrip("/") + "/health"

    total = len(recipients)
    logger.info(f"📬 Total recipients: {total}")

    for idx, (email, (hiring_manager, company)) in enumerate(recipients.items(), start=1):
        if sending_status["stop_flag"]:
            sending_status["current_message"] = "Stopping email sending as requested"
            logger.info("🛑 Stopping email sending as requested")
            break

        sending_status["current_message"] = f"Sending to {email} ({idx}/{total})"
        logger.info(f"📨 [{idx}/{total}] Sending to {email} — {hiring_manager} @ {company}")
        try:
            send_single_email_brevo(email, hiring_manager, company, resume_bytes, resume_filename)
            logger.info(f"✅ [{idx}/{total}] Sent → {email}")
            sending_status["results"].append({
                "status":         "success",
                "recipient":      email,
                "hiring_manager": hiring_manager,
                "company":        company,
                "index":          idx,
                "total":          total,
            })
        except Exception as exc:
            logger.error(f"❌ [{idx}/{total}] Failed → {email}: {exc}")
            sending_status["results"].append({
                "status":    "error",
                "recipient": email,
                "error":     str(exc),
                "index":     idx,
                "total":     total,
            })

        if idx < total and not sending_status["stop_flag"]:
            # Generate random delay between min and max
            delay = random.randint(min_delay_seconds, max_delay_seconds)
            sending_status["current_message"] = f"Waiting {delay}s before next email ({idx}/{total} sent)"
            logger.info(
                f"⏳ Waiting {delay}s ({delay // 60}m {delay % 60}s) before next email… "
                f"(keep-alive pings every 10s)"
            )
            keep_alive_during_wait(delay, service_url)

    sending_status["last_run"]   = time.strftime("%Y-%m-%d %H:%M:%S")
    sending_status["is_sending"] = False
    if sending_status["stop_flag"]:
        sending_status["current_message"] = "Email sending stopped by user"
        logger.info("🛑 Email sending stopped by user")
    else:
        sending_status["current_message"] = "All done!"
        logger.info(f"🎉 All done! Finished at {sending_status['last_run']}")


def _fatal(message: str):
    """Log a fatal error and update status."""
    logger.error(f"❌ {message}")
    sending_status["results"].append({"status": "error", "message": message})
    sending_status["is_sending"] = False


# ── Auth helper ─────────────────────────────────────────────────────────────
def check_auth() -> bool:
    if API_KEY:
        provided = request.headers.get("X-API-Key") or request.args.get("api_key")
        return provided == API_KEY
    return True


# ── Flask routes ─────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "service": "Email Sender API (Brevo)",
        "status":  "running",
        "endpoints": {
            "/":                  "This page",
            "/health":            "Health check (GET)",
            "/send":              "Trigger email sending (POST)",
            "/status":            "Check sending status (GET)",
            "/recipients":        "List all recipients (GET)",
            "/recipients":        "Add a recipient (POST)",
            "/recipients/<email>": "Delete a recipient (DELETE)",
        },
    })


@app.route("/health")
def health():
    return jsonify({
        "status":              "healthy",
        "brevo_key_set":       bool(BREVO_API_KEY),
        "sender_address_set":  bool(SENDER_ADDRESS),
        "resume_file_exists":  os.path.isfile(RESUME_FILE),
        "recipients_count":    len(recipients),
        "auto_send":           AUTO_SEND,
    })


@app.route("/send", methods=["POST"])
def trigger_send():
    if not check_auth():
        logger.warning("⚠️  Unauthorized /send attempt")
        return jsonify({"error": "Unauthorized"}), 401

    if sending_status["is_sending"]:
        logger.warning("⚠️  /send called while already sending — rejected")
        return jsonify({"status": "busy", "message": "Email sending is already in progress"}), 409

    # Get min and max delay from request, default to 30-40 seconds
    data = request.get_json() or {}
    min_delay = int(data.get("min_delay", 30))
    max_delay = int(data.get("max_delay", 40))
    
    # Ensure min delay is not greater than max delay
    if min_delay > max_delay:
        min_delay, max_delay = max_delay, min_delay

    logger.info(f"📬 /send triggered via API — {len(recipients)} recipient(s), delay range: {min_delay}-{max_delay}s")
    t = threading.Thread(target=send_emails_async, args=(min_delay, max_delay), daemon=True)
    t.start()

    return jsonify({
        "status":            "started",
        "message":           "Email sending started in background",
        "recipients_count":  len(recipients),
        "min_delay_seconds": min_delay,
        "max_delay_seconds": max_delay,
    })


@app.route("/stop", methods=["POST"])
def stop_sending():
    if not check_auth():
        logger.warning("⚠️  Unauthorized /stop attempt")
        return jsonify({"error": "Unauthorized"}), 401

    if not sending_status["is_sending"]:
        return jsonify({"status": "not_sending", "message": "No email sending in progress"}), 400

    sending_status["stop_flag"] = True
    logger.info("🛑 Stop request received")
    return jsonify({"status": "stopping", "message": "Stopping email sending…"})


@app.route("/status", methods=["GET"])
def get_status():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    success = sum(1 for r in sending_status["results"] if r.get("status") == "success")
    errors  = sum(1 for r in sending_status["results"] if r.get("status") == "error")

    return jsonify({
        "is_sending":       sending_status["is_sending"],
        "last_run":         sending_status["last_run"],
        "total_recipients": len(recipients),
        "sent_success":     success,
        "sent_error":       errors,
        "results":          sending_status["results"],
        "stop_flag":        sending_status["stop_flag"],
        "current_message":  sending_status["current_message"],
    })


# ── Recipient API Endpoints ──────────────────────────────────────────────────
@app.route("/recipients", methods=["GET"])
def list_recipients():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"recipients": recipients, "count": len(recipients)})


@app.route("/recipients", methods=["POST"])
def add_recipient():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data or "email" not in data or "name" not in data or "company" not in data:
        return jsonify({"error": "Missing required fields: email, name, company"}), 400
    
    email = data["email"].strip()
    name = data["name"].strip()
    company = data["company"].strip()
    
    if email in recipients:
        return jsonify({"error": f"Recipient {email} already exists"}), 409
    
    recipients[email] = [name, company]
    save_recipients(recipients)
    return jsonify({"message": f"Added recipient: {email}", "recipient": {email: [name, company]}}), 201


@app.route("/recipients/<email>", methods=["DELETE"])
def delete_recipient(email):
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    if email not in recipients:
        return jsonify({"error": f"Recipient {email} not found"}), 404
    
    del recipients[email]
    save_recipients(recipients)
    return jsonify({"message": f"Deleted recipient: {email}"})


# ── Auto-send on startup ─────────────────────────────────────────────────────
def _auto_send_trigger():
    time.sleep(5)   # let Flask finish binding

    if not AUTO_SEND:
        logger.info("⏸️  AUTO_SEND=false — skipping auto-send.")
        return
    if sending_status["is_sending"]:
        logger.info("⏭️  Auto-send skipped — already sending.")
        return
    if sending_status["last_run"]:
        logger.info(f"⏭️  Auto-send skipped — already ran at {sending_status['last_run']}.")
        return

    logger.info(f"🤖 Auto-send starting — {len(recipients)} recipient(s)…")
    send_emails_async()     # runs in this daemon thread, so no extra thread needed


if AUTO_SEND:
    t = threading.Thread(target=_auto_send_trigger, daemon=True)
    t.start()
    logger.info("✅ Auto-send thread started")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)