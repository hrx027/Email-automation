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
recipients = {
   
    "ashu.sharma@nagarro.com":           ("Ashu Sharma",            "Nagarro"),
    "jamalur.rahman@nagarro.com":        ("Jamalur Rahman",         "Nagarro"),
    "surbhi.mathur@nagarro.com":         ("Surbhi Mathur",          "Nagarro"),
    "rushikesh.bendre@nagarro.com":      ("Rushikesh Bendre",       "Nagarro"),
    "ankit.wadhera@nagarro.com":         ("Ankit Wadhera",          "Nagarro"),
    "swati.gujral@nagarro.com":          ("Swati Gujral",           "Nagarro"),
    "subrata.dey@nagarro.com":           ("Subrata Dey",            "Nagarro"),
    "ankita.kumari01@nagarro.com":       ("Ankita Kumari",          "Nagarro"),
    "isha.arora@nagarro.com":            ("Isha Arora",             "Nagarro"),
    "khushter.kaifi@nagarro.com":        ("Khushter Kaifi",         "Nagarro"),
    "shikha.pal@nagarro.com":            ("Shikha Pal",             "Nagarro"),
    "manjeet.singh@nagarro.com":         ("Manjeet Singh",          "Nagarro"),
    "saket.gorani@nagarro.com":          ("Saket Gorani",           "Nagarro"),
    "rajesh.kumar13@nagarro.com":        ("Rajesh Kumar",           "Nagarro"),
    "vishal.sahijwani@nagarro.com":      ("Vishal Sahijwani",       "Nagarro"),
    "mannat.pannu@nagarro.com":          ("Mannat Pannu",           "Nagarro"),
    "saloni.bansal@nagarro.com":         ("Saloni Bansal",          "Nagarro"),
    "abhishek.devra@nagarro.com":        ("Abhishek Devra",         "Nagarro"),
    "purnima.arora@nagarro.com":         ("Purnima Arora",          "Nagarro"),
    "akash.barman@nagarro.com":          ("Akash Barman",           "Nagarro"),
    "ravi.sharma09@nagarro.com":         ("Ravi Sharma",            "Nagarro"),
    "moti.kumar@nagarro.com":            ("Moti Kumar",             "Nagarro"),
    "aditya.rathour@nagarro.com":        ("Aditya Rathour",         "Nagarro"),
     "prateek.sharma@daffodilsw.com":       ("Prateek Sharma",         "Daffodil Software"),
    "utkarsh.jain@daffodilsw.com":        ("Utkarsh Jain",          "Daffodil Software"),
    "steve@daffodildb.com":               ("Steve Jones",           "Daffodil Software"),
    "nbisht@linklyhq.com":                ("Nitish Bisht",          "Daffodil Software"),
    "lalit.narayan@daffodilsw.com":       ("Lalit Narayan",         "Daffodil Software"),
    "ankit@daffodildb.com":               ("Ankit Sharma",          "Daffodil Software"),
    "arvind.jha@daffodilsw.com":          ("Arvind Jha",            "Daffodil Software"),
    "shayra.sharma@daffodilsw.com":       ("Shayra Sharma",         "Daffodil Software"),
    "ankush.pandita@daffodilsw.com":      ("Ankush Pandita",        "Daffodil Software"),
    "joy@daffodilsw.com":                 ("Joydeep Bhattacharya",  "Daffodil Software"),
    "jyoti.gupta@daffodilsw.com":         ("Jyoti Gupta",           "Daffodil Software"),
    "jaspal.gulati@daffodilsw.com":       ("Jaspal Gulati",         "Daffodil Software"),
    "shivanshu.verma@daffodilsw.com":     ("Shivanshu Verma",       "Daffodil Software"),
    "anuj@linklyhq.com":                  ("Anuj Tripathi",         "Daffodil Software"),
    "rashi.shukla@daffodilsw.com":        ("Rashi Shukla",          "Daffodil Software"),
    "keshi.yadava@daffodilsw.com":        ("Keshi Yadava",          "Daffodil Software"),
    "ankit.aneja@daffodilsw.com":         ("Ankit Aneja",           "Daffodil Software"),
    "subhash.kumar@daffodilsw.com":       ("Subhash Kumar",         "Daffodil Software"),
    "sunil.thakur@daffodilsw.com":        ("Sunil Kumar",           "Daffodil Software"),
    "amit@daffodilsw.com":                ("Amit Singh",            "Daffodil Software"),
    "rajkumar@daffodilsw.com":            ("Raj Prajapati",         "Daffodil Software"),
    "ashu.garg@daffodilsw.com":           ("Ashu Garg",             "Daffodil Software"),
    "deepika.boora@daffodilsw.com":       ("Deepika Boora",         "Daffodil Software"),
    "monu@daffodilsw.com":                ("Monu Kumar",            "Daffodil Software"),
    "akash.jain@daffodilsw.com":          ("Akash Jain",            "Daffodil Software"),
    "sangeeta.rajput@daffodilsw.com":     ("Sangeeta Rajput",       "Daffodil Software"),
    "shivanshu@daffodilsw.com":           ("Shivanshu Singh",       "Daffodil Software"),
    "rakesh.kumar@daffodilsw.com":        ("Rakesh Singh",          "Daffodil Software"),
}

# ── Email HTML body ─────────────────────────────────────────────────────────
BODY_TEMPLATE = """
<html>
<body style="font-family:Arial, sans-serif; line-height:1.8; font-size:16px; color:#222; max-width:900px;">

<p>Hello <b>{hiring_manager}</b>,</p>

<p>
I'm a <b>final-year Software Engineering student at Delhi Technological University (DTU)</b>
competent in backend development using
<b>Node.js, REST APIs, PostgreSQL, and MongoDB</b>
and frontend development using
<b>React, React Native, and Tailwind CSS</b>
along with solid fundamentals in
<b>Data Structures & Algorithms</b> and
<b>Object-Oriented Programming</b>,
along with internship experience as a
<b>Software Developer at Employwise</b>
and Quant work at
<b>Futures First</b>.
</p>

<p>
I'm highly committed towards software engineering and believe my skills align well with this role.
I'd be really grateful if <b>you can help me secure a position available in the company</b> in any way.
Please find my resume attached.
</p>

<br>

<p>
Best regards,<br><br>

<b>Akash Singh</b><br>
📧 <a href="mailto:akashhhhs.r@gmail.com">akashhhhs.r@gmail.com</a><br>
📞 +91-8235377886<br>
<a href="https://www.linkedin.com/in/akash-singh-a36386264">
LinkedIn Profile
</a>
</p>

</body>
</html>
"""

# ── Global status ───────────────────────────────────────────────────────────
sending_status = {
    "is_sending": False,
    "last_run":   None,
    "results":    [],
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
        "subject": f"Application for SDE/Backend/Full Stack Fresher Roles - Akash Singh, DTU at {company}",
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
def send_emails_async():
    global sending_status

    logger.info("🚀 Starting email sending process (Brevo API)…")
    sending_status["is_sending"] = True
    sending_status["results"]    = []

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

        if idx < total:
            delay = random.randint(600, 800)
            logger.info(
                f"⏳ Waiting {delay}s ({delay // 60}m {delay % 60}s) before next email… "
                f"(keep-alive pings every 10s)"
            )
            keep_alive_during_wait(delay, service_url)

    sending_status["last_run"]   = time.strftime("%Y-%m-%d %H:%M:%S")
    sending_status["is_sending"] = False
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
            "/":       "This page",
            "/health": "Health check (GET)",
            "/send":   "Trigger email sending (POST)",
            "/status": "Check sending status (GET)",
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

    logger.info(f"📬 /send triggered via API — {len(recipients)} recipient(s)")
    t = threading.Thread(target=send_emails_async, daemon=True)
    t.start()

    return jsonify({
        "status":            "started",
        "message":           "Email sending started in background",
        "recipients_count":  len(recipients),
    })


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
    })


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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)