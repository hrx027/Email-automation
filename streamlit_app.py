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

delay_seconds = st.slider(
    "Time delay between emails (seconds)",
    min_value=5,
    max_value=120,
    value=30,
    help="Wait time between sending each email"
)

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
                    json={"delay": delay_seconds},
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
status_placeholder = st.empty()
results_placeholder = st.empty()

# Auto-refresh status
if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True

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
            
            # Display current message
            if status.get("current_message"):
                current_status_placeholder.info(f"📢 {status['current_message']}")
            
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
                break
        
        else:
            current_status_placeholder.error(f"❌ Failed to get status: {response.text}")
            break
    
    except Exception as e:
        current_status_placeholder.error(f"❌ Error getting status: {e}")
        break
    
    # Wait before refreshing
    time.sleep(1)

# Manual refresh button
if st.button("🔄 Refresh Status"):
    st.session_state["auto_refresh"] = True
    st.rerun()
