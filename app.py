import streamlit as st
import json
import time
import random
from datetime import datetime
from supabase import create_client
from openai import OpenAI
import openai

# ==========================================
# 1. PAGE CONFIGURATION & SEO
# ==========================================
st.set_page_config(
    page_title="Heydoctor Web Manager AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <head>
        <meta name="description" content="Heydoctor Web Manager AI: Next-generation enterprise intelligence and web management platform.">
        <meta name="keywords" content="AI, SaaS, Heydoctor, Web Manager, Data Analysis, Widget">
    </head>
""", unsafe_allow_html=True)

# ==========================================
# 2. PREMIUM UI/UX (FLOATING & GLOWING CSS)
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #050505 80%);
        color: #E2E8F0;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}

    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
        100% { transform: translateY(0px); }
    }

    .hero-title {
        font-size: 3.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -1.5px;
        animation: float 4s ease-in-out infinite;
        text-shadow: 0px 0px 20px rgba(0, 198, 255, 0.4);
        text-align: center;
    }
    
    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        text-align: center;
        letter-spacing: 1px;
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(0, 198, 255, 0.2);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        transition: all 0.4s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 15px 40px rgba(0, 198, 255, 0.2);
        border: 1px solid rgba(0, 198, 255, 0.5);
    }

    .stChatMessage {
        background: transparent !important;
        border: none !important;
    }
    .stChatMessage [data-testid="chatAvatarIcon-user"] {
        background-color: #1E293B;
        box-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
    }
    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%);
        box-shadow: 0 0 15px rgba(0, 198, 255, 0.5);
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
        box-shadow: 0 4px 15px rgba(0, 198, 255, 0.3);
    }
    
    div.stButton > button:first-child:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 25px rgba(0, 198, 255, 0.6);
    }
    
    .credit-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.2) 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #00C6FF;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease;
    }
    .credit-card:hover {
        transform: scale(1.02);
    }
    
    code {
        color: #00C6FF !important;
        background-color: rgba(0, 198, 255, 0.1) !important;
        border-radius: 4px;
        padding: 2px 6px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GLOBAL CONFIGURATION & SECRETS
# ==========================================
DEFAULT_CREDITS = 10

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    ADSTERRA_SMARTLINK = st.secrets["ADSTERRA_SMARTLINK"]
except Exception as e:
    st.error(f"Missing DB/Adsterra Secrets: {e}.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==========================================
# 4. ADVANCED API & MEMORY MANAGEMENT
# ==========================================
# Initialize states
if "api_keys" not in st.session_state:
    st.session_state.api_keys = []
if "key_status" not in st.session_state:
    st.session_state.key_status = {}

def load_api_keys():
    keys = []
    try:
        if hasattr(st, "secrets"):
            if "OPENROUTER_KEYS" in st.secrets:
                # Support for list format
                secret_keys = st.secrets["OPENROUTER_KEYS"]
                if isinstance(secret_keys, list):
                    keys.extend(secret_keys)
                elif isinstance(secret_keys, str):
                    keys.append(secret_keys)
            else:
                # Support for numbered keys format (like in ref app)
                for i in range(1, 10): 
                    key_name = f"OPENROUTER_API_KEY_{i}"
                    if key_name in st.secrets:
                        val = st.secrets[key_name]
                        if isinstance(val, str) and val.strip():
                            keys.append(val.strip())
    except Exception:
        pass
    return keys

def resilient_stream_api_call(messages, available_keys, model="google/gemini-2.5-flash", max_retries=3):
    """Advanced API rotation with exponential backoff and timeout handling."""
    valid_keys = [k for k in available_keys if k and k.strip()]
    if not valid_keys:
        yield "⚠️ Error: No valid API keys found. Please configure them in the sidebar."
        return
        
    current_time = time.time()
    # Sort keys by prioritizing those that haven't failed recently
    valid_keys.sort(key=lambda k: st.session_state.key_status.get(k, 0))
    
    for attempt in range(max_retries):
        for key in valid_keys:
            # Skip keys on cooldown (30 seconds)
            if current_time - st.session_state.key_status.get(key, 0) < 30:
                continue
                
            try:
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=key,
                    default_headers={"HTTP-Referer": "https://heydoctor.ai", "X-Title": "Heydoctor Web Manager AI"}
                )
                
                response = client.chat.completions.create(
                    model=model,  
                    messages=messages,
                    max_tokens=1500,
                    temperature=0.7,
                    stream=True,
                    timeout=15 
                )
                
                # Reset key status on success
                st.session_state.key_status[key] = 0
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return 
                
            except Exception as e:
                # Put key on cooldown
                st.session_state.key_status[key] = time.time()
                continue
                
        # Exponential backoff if all keys fail
        time.sleep(2 ** attempt)
        
    yield "⚠️ **Server Busy:** All API endpoints are currently overloaded or on cooldown. Please try again in a minute."

# ==========================================
# 5. SESSION & DB MANAGEMENT (STRICT AI ROLE)
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None
if "requests_left" not in st.session_state:
    st.session_state.requests_left = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = """You are 'Heydoctor Web Manager AI', an elite enterprise AI assistant. 
CRITICAL RULES YOU MUST FOLLOW:
1. You were created EXCLUSIVELY by Pratyush Ranjan Roul. 
2. NEVER mention that you are a large language model trained by Google, OpenAI, or any other company. 
3. If anyone asks who made you, created you, or trained you, you MUST answer: 'I was created by Pratyush Ranjan Roul.'
4. Provide concise, highly analytical, and actionable responses to help users manage their web platforms."""

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
# 6. AUTHENTICATION & SETTINGS (SIDEBAR)
# ==========================================
if not st.session_state.api_keys:
    st.session_state.api_keys = load_api_keys()

with st.sidebar:
    st.markdown("### 🧬 Heydoctor Manager")
    st.caption("Enterprise Intelligence Core")
    
    # API Key Active Indicator
    if st.session_state.api_keys:
        st.success(f"🟢 {len(st.session_state.api_keys)} API Keys Active")
    else:
        st.error("🔴 No API Keys found!")
        fallback_key = st.text_input("Enter OpenRouter API Key", type="password")
        if fallback_key:
            st.session_state.api_keys = [fallback_key]
            st.rerun()
    
    st.markdown("---")
    
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
    else:
        st.markdown(f"**Operator:**\n`{st.session_state.user.email}`")
        
        color = "#00C6FF" if st.session_state.requests_left > 0 else "#FF4B4B"
        st.markdown(f"""
        <div class="credit-card" style="border-left-color: {color}; box-shadow: 0 0 15px {color}40;">
            <h3 style="margin:0; font-size: 24px; color:{color}; text-shadow: 0 0 10px {color};">{st.session_state.requests_left}</h3>
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
# 7. PRE-LOGIN MAIN SCREEN & ADSTERRA
# ==========================================
if st.session_state.user is None:
    st.markdown("<div style='margin-top: 10vh;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='hero-title'>Heydoctor Web Manager AI</h1>", unsafe_allow_html=True)
    
    st.markdown("""
        <div class='glass-card' style='text-align:center; max-width: 550px; margin: 30px auto; padding: 40px 20px;'>
            <h2 style='color: #E2E8F0; margin-bottom: 15px;'>Welcome to the Studio</h2>
            <p style='color: #94A3B8; font-size: 1.15rem; margin-bottom: 25px;'>Please <b>Login</b> or <b>Sign Up</b> from the sidebar to continue.</p>
            <hr style='border-color: rgba(255,255,255,0.05); margin: 25px 0;'>
            <p style='color: #00C6FF; font-weight: 700; font-size: 1.2rem; text-shadow: 0 0 10px rgba(0, 198, 255, 0.4); margin-bottom: 0;'>✨ Created by Pratyush Ranjan Roul</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

if st.session_state.requests_left <= 0:
    st.markdown("<h1 class='hero-title'>Access Locked</h1>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card' style='text-align:center;'>", unsafe_allow_html=True)
    st.warning("⚠️ **Ecosystem Operations Exhausted**")
    st.write("Authorize additional compute cycles by visiting our sponsor network.")
    
    st.markdown(f"""
        <a href="{ADSTERRA_SMARTLINK}" target="_blank" style="text-decoration:none;">
            <div style="background: linear-gradient(90deg, #FF4B4B, #FF904B); color: white; padding: 14px 28px; border-radius: 8px; font-size: 17px; font-weight: bold; margin: 20px auto; width: 60%; box-shadow: 0 4px 20px rgba(255, 75, 75, 0.6); cursor:pointer; transition: all 0.3s ease;">
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
# 8. MAIN DASHBOARD & TABS
# ==========================================
st.markdown("<h1 class='hero-title'>Heydoctor Web Manager AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='hero-subtitle'>Command Center & Ecosystem Integrations</p>", unsafe_allow_html=True)

tab_chat, tab_widget = st.tabs(["💬 Command Center", "🔌 Embed Widget"])

# --- CHAT INTERFACE TAB ---
with tab_chat:
    ai_model = st.selectbox("Intelligence Engine", [
        "google/gemini-2.5-flash"
    ], label_visibility="collapsed")
    
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if len(st.session_state.messages) == 0:
        st.markdown(f"""
            <div class="glass-card">
                <h3 style="color: #00C6FF; text-shadow: 0 0 8px rgba(0,198,255,0.4);">Welcome to your Workspace</h3>
                <p style="color: #94A3B8;">Initialize a query below to consume 1 Compute Cycle. You have <b style="color:white;">{st.session_state.requests_left}</b> remaining.</p>
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
                # Using the newly adapted resilient stream function
                for chunk in resilient_stream_api_call(optimized_context, st.session_state.api_keys, model=ai_model):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
        
        if "**Error:**" not in full_response and "**Server Busy:**" not in full_response:
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            deduct_credit()
            st.rerun() 
        else:
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun() 

# --- EMBED WIDGET TAB ---
with tab_widget:
    st.markdown("""
        <div class="glass-card">
            <h2 style="color: #00C6FF; text-shadow: 0 0 10px rgba(0,198,255,0.5);">Integrate Heydoctor Web Manager into your App</h2>
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
