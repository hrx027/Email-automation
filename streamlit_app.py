import streamlit as st
import requests
import time
import json

# Set page config
st.set_page_config(
    page_title="Email Automation Dashboard",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar for configuration
st.sidebar.title("⚙️ Configuration")

# Get API URL and key from user
API_URL = st.sidebar.text_input(
    "Backend API URL",
    value="https://your-service.onrender.com",
    help="Your Render backend URL"
)

API_KEY = st.sidebar.text_input(
    "API Key",
    type="password",
    help="Your API key from Render environment variables"
)

# Headers for API requests
headers = {}
if API_KEY:
    headers["X-API-Key"] = API_KEY

# Main app
st.title("📧 Email Automation Dashboard")

# --- Recipient Management ---
st.header("1. Add Recipients")

st.markdown("""
Paste recipients in the following format (one per line):
```
email@example.com, Hiring Manager Name, Company Name
hr@company.com, Jane Doe, Tech Corp
```
""")

recipient_text = st.text_area(
    "Recipients (one per line)",
    height=200,
    placeholder="hr@example.com, Hiring Manager, Example Company\ncareers@company.com, John Smith, Tech Corp"
)

# Parse recipients
def parse_recipients(text):
    recipients = []
    lines = text.strip().split("\n")
    for line in lines:
        if line.strip():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                recipients.append({
                    "email": parts[0],
                    "name": parts[1],
                    "company": parts[2]
                })
    return recipients

recipients = parse_recipients(recipient_text)

if recipients:
    st.success(f"✅ Found {len(recipients)} recipients")
    with st.expander("View Recipients"):
        for r in recipients:
            st.write(f"- {r['email']} ({r['name']} @ {r['company']})")

# --- Send Configuration ---
st.header("2. Email Settings")

col1, col2 = st.columns(2)

with col1:
    min_delay_minutes = st.number_input(
        "Minimum delay (minutes)",
        min_value=0.1,
        max_value=60.0,
        value=0.5,
        step=0.1,
        help="Minimum wait time between emails"
    )

with col2:
    max_delay_minutes = st.number_input(
        "Maximum delay (minutes)",
        min_value=0.1,
        max_value=60.0,
        value=1.0,
        step=0.1,
        help="Maximum wait time between emails"
    )

# Convert to seconds
min_delay_seconds = int(min_delay_minutes * 60)
max_delay_seconds = int(max_delay_minutes * 60)

# Ensure min <= max
if min_delay_seconds > max_delay_seconds:
    st.warning("Minimum delay is greater than maximum delay - swapping them!")
    min_delay_seconds, max_delay_seconds = max_delay_seconds, min_delay_seconds

st.info(f"Delay range: {min_delay_seconds}s - {max_delay_seconds}s")

# --- Action Buttons ---
st.header("3. Actions")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Start Sending Emails", type="primary", disabled=len(recipients) == 0):
        if not API_URL or not API_KEY:
            st.error("Please set API URL and API Key in the sidebar!")
        else:
            # First add all recipients
            add_success = 0
            add_errors = 0
            
            with st.spinner("Adding recipients..."):
                for r in recipients:
                    try:
                        response = requests.post(
                            f"{API_URL}/recipients",
                            headers=headers,
                            json=r,
                            timeout=10
                        )
                        if response.status_code in [200, 201]:
                            add_success += 1
                        else:
                            add_errors += 1
                    except Exception as e:
                        add_errors += 1
            
            if add_success > 0:
                st.success(f"✅ Added {add_success} recipients")
            if add_errors > 0:
                st.warning(f"⚠️ Failed to add {add_errors} recipients (may already exist)")
            
            # Now trigger sending
            try:
                response = requests.post(
                    f"{API_URL}/send",
                    headers=headers,
                    json={"min_delay": min_delay_seconds, "max_delay": max_delay_seconds},
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    st.success("✅ Email sending started!")
                    st.session_state["is_sending"] = True
                else:
                    st.error(f"❌ Failed to start sending: {response.text}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

with col2:
    if st.button("🛑 Stop Sending", type="secondary"):
        if not API_URL or not API_KEY:
            st.error("Please set API URL and API Key in the sidebar!")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/stop",
                    headers=headers,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    st.success("✅ Stop request sent!")
                else:
                    st.warning(f"⚠️ {response.text}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- Live Status ---
st.header("4. Live Status")

current_status_placeholder = st.empty()
countdown_placeholder = st.empty()
status_placeholder = st.empty()
results_placeholder = st.empty()

# Auto-refresh status
if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True

if "countdown_start" not in st.session_state:
    st.session_state["countdown_start"] = None

if "countdown_total" not in st.session_state:
    st.session_state["countdown_total"] = 0

if "last_delay" not in st.session_state:
    st.session_state["last_delay"] = 0

while st.session_state.get("auto_refresh", True):
    if not API_URL or not API_KEY:
        current_status_placeholder.info("👈 Set API URL and API Key in the sidebar to see status")
        break
    
    try:
        response = requests.get(
            f"{API_URL}/status",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            status = response.json()
            
            # Handle countdown
            current_msg = status.get("current_message", "")
            if "Waiting" in current_msg and "s before next email" in current_msg:
                # Extract delay from message
                import re
                delay_match = re.search(r"Waiting (\d+)s", current_msg)
                if delay_match:
                    current_delay = int(delay_match.group(1))
                    # Reset countdown if we just started waiting OR delay changed
                    if (
                        st.session_state["countdown_start"] is None 
                        or "Waiting" not in st.session_state.get("last_message", "")
                        or current_delay != st.session_state["last_delay"]
                    ):
                        st.session_state["countdown_start"] = time.time()
                        st.session_state["countdown_total"] = current_delay
                        st.session_state["last_delay"] = current_delay
                
                # Calculate time left
                elapsed = time.time() - st.session_state["countdown_start"]
                time_left = max(0, int(st.session_state["countdown_total"] - elapsed))
                
                # Display countdown
                countdown_placeholder.warning(f"⏳ Next email in {time_left}s...")
            else:
                # Clear countdown if not waiting
                countdown_placeholder.empty()
                st.session_state["countdown_start"] = None
                st.session_state["countdown_total"] = 0
                st.session_state["last_delay"] = 0
            
            st.session_state["last_message"] = current_msg
            
            # Display current message
            if current_msg:
                current_status_placeholder.info(f"📢 {current_msg}")
            
            # Display status
            with status_placeholder.container():
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Recipients", status["total_recipients"])
                col2.metric("Sent Successfully", status["sent_success"])
                col3.metric("Failed", status["sent_error"])
                col4.metric("Is Sending?", "✅ Yes" if status["is_sending"] else "❌ No")
            
            # Display results
            if status["results"]:
                with results_placeholder.container():
                    st.subheader("📊 Sending Results")
                    for result in status["results"]:
                        if result["status"] == "success":
                            st.success(f"✅ {result['index']}/{result['total']} - {result['recipient']} ({result['hiring_manager']} @ {result['company']})")
                        else:
                            st.error(f"❌ {result['index']}/{result['total']} - {result['recipient']}: {result['error']}")
            
            # Stop auto-refresh if not sending
            if not status["is_sending"]:
                st.session_state["auto_refresh"] = False
                countdown_placeholder.empty()
                break
        
        else:
            current_status_placeholder.error(f"❌ Failed to get status: {response.text}")
            break
    
    except Exception as e:
        current_status_placeholder.error(f"❌ Error getting status: {e}")
        break
    
    # Wait before refreshing
    time.sleep(0.5)

# Manual refresh button
if st.button("🔄 Refresh Status"):
    st.session_state["auto_refresh"] = True
    st.rerun()
