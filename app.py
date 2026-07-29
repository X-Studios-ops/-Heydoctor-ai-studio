import streamlit as st
import requests
import json
import time
import random
from datetime import datetime
from supabase import create_client

# ==========================================
# 1. PAGE CONFIGURATION & SEO
# ==========================================
st.set_page_config(
    page_title="Heydoctor Web Manager AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# SEO & Meta Tags
st.markdown("""
    <head>
        <meta name="description" content="Heydoctor Web Manager AI: Next-generation enterprise intelligence and web management platform.">
        <meta name="keywords" content="AI, SaaS, Heydoctor, Web Manager, Data Analysis, Widget">
    </head>
""", unsafe_allow_html=True)

# ==========================================
# 2. PREMIUM UI/UX (GLASSMORPHISM CSS)
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #050505 70%);
        color: #E2E8F0;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}

    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    .stChatMessage {
        background: transparent !important;
        border: none !important;
    }
    .stChatMessage [data-testid="chatAvatarIcon-user"] {
        background-color: #334155;
    }
    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%);
    }

    div.stButton > button:first-child {
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 198, 255, 0.4);
    }
    
    .credit-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #00C6FF;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
    }
    
    code {
        color: #00C6FF !important;
        background-color: rgba(0, 198, 255, 0.1) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GLOBAL CONFIGURATION (CREDIT LIMITS)
# ==========================================
DEFAULT_CREDITS = 5

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    ADSTERRA_SMARTLINK = st.secrets["ADSTERRA_SMARTLINK"]
    OPENROUTER_KEYS = st.secrets["OPENROUTER_KEYS"]
except Exception as e:
    st.error(f"Missing Secrets Configuration: {e}.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# API Manager
class OpenRouterManager:
    def __init__(self, keys):
        self.keys = keys
        if "current_key_index" not in st.session_state:
            st.session_state.current_key_index = 0

    def get_current_key(self):
        return self.keys[st.session_state.current_key_index]

    def rotate_key(self):
        st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(self.keys)
        return self.get_current_key()

    def stream_completion(self, messages, model="google/gemini-2.5-flash", temperature=0.7):
        url = "https://openrouter.ai/api/v1/chat/completions"
        max_retries = len(self.keys)
        
        for attempt in range(max_retries):
            current_key = self.get_current_key()
            headers = {
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://heydoctor.ai",
                "X-Title": "Heydoctor Web Manager AI"
            }
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }

            try:
                response = requests.post(url, headers=headers, json=payload, stream=True, timeout=15)
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: ') and line != 'data: [DONE]':
                                try:
                                    chunk = json.loads(line[6:])
                                    if 'choices' in chunk and len(chunk['choices']) > 0:
                                        delta = chunk['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            yield delta['content']
                                except json.JSONDecodeError:
                                    continue
                    return 
                elif response.status_code in [429, 402]:
                    self.rotate_key()
                    time.sleep(1)
                    continue
                else:
                    yield f"\n\n**API Error:** Server returned {response.status_code}."
                    return
            except requests.exceptions.RequestException:
                self.rotate_key()
                continue
        yield "\n\n**System Alert:** All API endpoints overloaded. Try again."

api_manager = OpenRouterManager(OPENROUTER_KEYS)

# ==========================================
# 4. SESSION & DB MANAGEMENT
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None
if "requests_left" not in st.session_state:
    st.session_state.requests_left = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are Heydoctor Web Manager AI, an elite enterprise assistant. Provide concise, highly analytical, and actionable responses to help users manage their web platforms."

def fetch_user_limits(email):
    db_res = supabase.table("users").select("requests_left").eq("email", email).execute()
    if db_res.data:
        return db_res.data[0]["requests_left"]
    else:
        supabase.table("users").insert({"email": email, "requests_left": DEFAULT_CREDITS}).execute()
        return DEFAULT_CREDITS

def deduct_credit():
    st.session_state.requests_left -= 1
    supabase.table("users").update({"requests_left": st.session_state.requests_left}).eq("email", st.session_state.user.email).execute()

def optimize_history(messages, max_history=6):
    if len(messages) <= max_history:
        return messages
    return [messages[0]] + messages[-(max_history):]

# ==========================================
# 5. AUTHENTICATION (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("### 🧬 Heydoctor Manager")
    st.caption("Enterprise Intelligence Core")
    
    if st.session_state.user is None:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        
        with tab_login:
            l_email = st.text_input("Email", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login to Workspace", key="login_btn"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": l_email, "password": l_pass})
                    st.session_state.user = res.user
                    st.session_state.requests_left = fetch_user_limits(l_email)
                    st.success("Access Granted!")
                    st.rerun()
                except Exception:
                    st.error("Invalid Credentials.")

        with tab_signup:
            s_email = st.text_input("Email", key="s_email")
            s_pass = st.text_input("Password", type="password", key="s_pass")
            if st.button("Register Account", key="signup_btn"):
                try:
                    supabase.auth.sign_up({"email": s_email, "password": s_pass})
                    supabase.table("users").insert({"email": s_email, "requests_left": DEFAULT_CREDITS}).execute()
                    st.success("Registered! You can login now.")
                except Exception as e:
                    st.error(f"Error: {e}")
        st.stop()
    
    else:
        st.markdown(f"**Operator:**\n`{st.session_state.user.email}`")
        
        color = "#00C6FF" if st.session_state.requests_left > 0 else "#FF4B4B"
        st.markdown(f"""
        <div class="credit-card" style="border-left-color: {color};">
            <h3 style="margin:0; font-size: 22px; color:{color};">{st.session_state.requests_left}</h3>
            <p style="margin:0; font-size: 13px; color:#94A3B8;">Operations Remaining</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Smart Actions**")
        if st.button("📊 Web Analytics Report"):
            st.session_state.messages.append({"role": "user", "content": "Generate an executive summary for optimizing my website's performance and analytics."})
            st.rerun()
        if st.button("🗑️ Clear Workspace"):
            st.session_state.messages = []
            st.rerun()
            
        if st.button("Logout", key="logout_btn"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# ==========================================
# 6. ADSTERRA UNLOCK SCREEN
# ==========================================
if st.session_state.requests_left <= 0:
    st.markdown("<h1 class='hero-title' style='text-align:center;'>Access Locked</h1>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card' style='text-align:center;'>", unsafe_allow_html=True)
    st.warning("⚠️ **Ecosystem Operations Exhausted**")
    st.write("Authorize additional compute cycles by visiting our sponsor network.")
    
    st.markdown(f"""
        <a href="{ADSTERRA_SMARTLINK}" target="_blank" style="text-decoration:none;">
            <div style="background: linear-gradient(90deg, #FF4B4B, #FF904B); color: white; padding: 14px 28px; border-radius: 8px; font-size: 17px; font-weight: bold; margin: 20px auto; width: 60%; box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4); cursor:pointer;">
                🔓 Unlock {DEFAULT_CREDITS} Compute Cycles
            </div>
        </a>
    """, unsafe_allow_html=True)
    
    st.write("---")
    if st.button("✅ I have authorized via the link (Restore)", use_container_width=True):
        supabase.table("users").update({"requests_left": DEFAULT_CREDITS}).eq("email", st.session_state.user.email).execute()
        st.session_state.requests_left = DEFAULT_CREDITS
        st.success("Compute Cycles Restored! Initializing workspace...")
        time.sleep(1)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 7. MAIN DASHBOARD & TABS
# ==========================================
st.markdown("<h1 class='hero-title'>Heydoctor Web Manager AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='hero-subtitle'>Command Center & Ecosystem Integrations</p>", unsafe_allow_html=True)

tab_chat, tab_widget = st.tabs(["💬 Command Center", "🔌 Embed Widget"])

# --- CHAT INTERFACE TAB ---
with tab_chat:
        ai_model = st.selectbox("Intelligence Engine", [
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemini-1.5-flash:free",
        "mistralai/mistral-7b-instruct:free"
    ], label_visibility="collapsed")

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if len(st.session_state.messages) == 0:
        st.markdown(f"""
            <div class="glass-card">
                <h3>Welcome to your Workspace</h3>
                <p style="color: #94A3B8;">Initialize a query below to consume 1 Compute Cycle. You have {st.session_state.requests_left} remaining.</p>
            </div>
        """, unsafe_allow_html=True)

    if prompt := st.chat_input("Enter command sequence..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        full_context = [{"role": "system", "content": st.session_state.system_prompt}] + st.session_state.messages
        optimized_context = optimize_history(full_context)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            with st.spinner("Synthesizing..."):
                for chunk in api_manager.stream_completion(optimized_context, model=ai_model):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        deduct_credit()
        st.rerun() 

# --- EMBED WIDGET TAB ---
with tab_widget:
    st.markdown("""
        <div class="glass-card">
            <h2>Integrate Heydoctor Web Manager into your App</h2>
            <p style="color: #94A3B8;">Copy and paste this snippet into the <code>&lt;head&gt;</code> tag of your website. This will deploy the suggestion & analytics module directly to your users.</p>
        </div>
    """, unsafe_allow_html=True)
    
    client_id = f"hwm_{hash(st.session_state.user.email)}"
    
    widget_code = f"""<!-- Heydoctor Web Manager Integration Snippet -->
<script>
  window.HeydoctorWebConfig = {{
    clientId: "{client_id}",
    theme: "dark",
    position: "bottom-right",
    features: ["analytics", "smart-suggestions"]
  }};
</script>
<script src="https://cdn.heydoctor.ai/v1/widget.js" async defer></script>
<!-- End Heydoctor Web Manager Snippet -->"""
    
    st.code(widget_code, language="html")
    
    st.info("💡 **Pro Tip:** Deploying this widget tracks user sessions on your domain and feeds the analytics directly back to this workspace. (API setup required on backend).")
