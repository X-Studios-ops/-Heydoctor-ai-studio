import time
import requests
import streamlit as st
from supabase import create_client

# ================= 1. PAGE CONFIG & CUSTOM CSS =================
st.set_page_config(
    page_title="Heydoctor AI Studio", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium UI
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00C6FF, #0072FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-header {
        text-align: center;
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.02);
        box-shadow: 0px 0px 15px rgba(0, 198, 255, 0.5);
    }
    .credit-card {
        background-color: #1E2127;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #00C6FF;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ================= 2. SECRETS INITIALIZATION =================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
    ADSTERRA_SMARTLINK = st.secrets["ADSTERRA_SMARTLINK"]
except KeyError as e:
    st.error(f"Missing Secret: {e}. Please add it to your Streamlit secrets.")
    st.stop()

BASE_URL = "https://openrouter.ai/api/v1"
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ================= 3. SESSION STATE =================
if "user" not in st.session_state:
    st.session_state.user = None
if "requests_left" not in st.session_state:
    st.session_state.requests_left = 0

def fetch_user_limits(email):
    db_res = supabase.table("users").select("requests_left").eq("email", email).execute()
    if db_res.data:
        return db_res.data[0]["requests_left"]
    else:
        supabase.table("users").insert({"email": email, "requests_left": 2}).execute()
        return 2

# ================= 4. AUTHENTICATION (SIDEBAR) =================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920323.png", width=70)
    st.markdown("## 🧬 Heydoctor Access")
    
    if st.session_state.user is None:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        
        with tab_login:
            l_email = st.text_input("Email", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login to Studio", key="login_btn"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": l_email, "password": l_pass})
                    st.session_state.user = res.user
                    st.session_state.requests_left = fetch_user_limits(l_email)
                    st.success("Access Granted!")
                    st.rerun()
                except Exception:
                    st.error("Invalid Email or Password.")

        with tab_signup:
            s_email = st.text_input("Email", key="s_email")
            s_pass = st.text_input("Password", type="password", key="s_pass")
            if st.button("Register Account", key="signup_btn"):
                try:
                    supabase.auth.sign_up({"email": s_email, "password": s_pass})
                    supabase.table("users").insert({"email": s_email, "requests_left": 2}).execute()
                    st.success("Registered! You can login now.")
                except Exception as e:
                    st.error(f"Error: {e}")
        st.stop()
    
    else:
        st.markdown(f"**Logged in as:**\n`{st.session_state.user.email}`")
        
        color = "#00C6FF" if st.session_state.requests_left > 0 else "#FF4B4B"
        st.markdown(f"""
        <div class="credit-card" style="border-left-color: {color};">
            <h3 style="margin:0; font-size: 22px; color:{color};">{st.session_state.requests_left}</h3>
            <p style="margin:0; font-size: 13px; color:#888;">Generations Remaining</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Logout", key="logout_btn"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# ================= 5. ADSTERRA UNLOCK SCREEN =================
if st.session_state.requests_left <= 0:
    st.markdown("<h1 class='main-header'>Heydoctor AI Studio</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; padding: 40px; background:#1E2127; border-radius:15px; border: 1px solid #333;'>", unsafe_allow_html=True)
    st.warning("⚠️ **Free Generations Exhausted!**")
    st.write("Support our ecosystem by visiting the sponsor link below to unlock **2 Free Requests** instantly.")
    
    st.markdown(f"""
        <a href="{ADSTERRA_SMARTLINK}" target="_blank" style="text-decoration:none;">
            <div style="background: linear-gradient(90deg, #FF4B4B, #FF904B); color: white; padding: 14px 28px; border-radius: 8px; text-align: center; font-size: 17px; font-weight: bold; margin: 20px auto; width: 60%; box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4); cursor:pointer;">
                🔓 Unlock 2 Free Requests
            </div>
        </a>
    """, unsafe_allow_html=True)
    
    st.write("---")
    if st.button("✅ I have visited the link, Restore Limits", use_container_width=True):
        supabase.table("users").update({"requests_left": 2}).eq("email", st.session_state.user.email).execute()
        st.session_state.requests_left = 2
        st.success("Credits Restored! Enjoy creating.")
        time.sleep(1)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ================= 6. MAIN STUDIO DASHBOARD =================
st.markdown("<h1 class='main-header'>Heydoctor AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Next-Gen AI Image & Video Generation Powered by OpenRouter</p>", unsafe_allow_html=True)

tab_img, tab_vid = st.tabs(["🎨 Image Studio", "🎬 Video Studio"])

def deduct_credit():
    st.session_state.requests_left -= 1
    supabase.table("users").update({"requests_left": st.session_state.requests_left}).eq("email", st.session_state.user.email).execute()

# --- IMAGE TAB ---
with tab_img:
    col1, col2 = st.columns([2, 1])
    with col1:
        img_prompt = st.text_area("Image Prompt:", height=140, placeholder="E.g., A cinematic futuristic medical laboratory, neon glowing blue lights, hyper-realistic, 8k...")
    with col2:
        img_model = st.selectbox("Model", ["black-forest-labs/flux-schnell", "stabilityai/stable-diffusion-3", "google/gemini-2.5-flash"])
        img_aspect = st.selectbox("Dimension", ["1:1 (Square)", "16:9 (Landscape)", "9:16 (Portrait)"])
    
    if st.button("✨ Generate Image", key="btn_img"):
        if not img_prompt:
            st.error("Please enter a prompt first.")
        else:
            with st.spinner("Synthesizing image..."):
                payload = {
                    "model": img_model,
                    "prompt": img_prompt,
                    "n": 1,
                    "size": "1024x1024" if "1:1" in img_aspect else "1024x576",
                }
                try:
                    res = requests.post(f"{BASE_URL}/images", headers=headers, json=payload)
                    data = res.json()
                    
                    if res.status_code == 200 and "data" in data:
                        image_url = data["data"][0].get("url")
                        st.image(image_url, caption="Generated by Heydoctor AI Studio", use_column_width=True)
                        deduct_credit()
                        st.success(f"Generated successfully! Credits left: {st.session_state.requests_left}")
                    else:
                        st.error(f"API Error: {data}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

# --- VIDEO TAB ---
with tab_vid:
    v_col1, v_col2 = st.columns([2, 1])
    with v_col1:
        vid_prompt = st.text_area("Video Prompt:", height=140, placeholder="E.g., Drone shot flying through a glowing futuristic portal, cinematic lighting, 4k...")
    with v_col2:
        vid_model = st.selectbox("Video Model", ["google/veo-3.1-lite", "openai/sora"])
        vid_duration = st.slider("Duration (Seconds)", min_value=3, max_value=15, value=5)
        
    if st.button("🎥 Generate Video", key="btn_vid"):
        if not vid_prompt:
            st.error("Please enter a video prompt first.")
        else:
            with st.spinner(f"Rendering {vid_duration}s video via OpenRouter... Please wait."):
                payload = {
                    "model": vid_model,
                    "prompt": vid_prompt,
                    "duration": vid_duration,
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                }
                try:
                    res = requests.post(f"{BASE_URL}/videos", headers=headers, json=payload)
                    job_data = res.json()
                    
                    if res.status_code == 200 and "id" in job_data:
                        job_id = job_data["id"]
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        video_url = None
                        for i in range(40):
                            progress_bar.progress((i + 1) * 25)
                            status_text.text(f"Processing rendering pipeline... Step {i+1}/40")
                            time.sleep(4)
                            
                            status_res = requests.get(f"{BASE_URL}/videos/{job_id}", headers=headers)
                            status_data = status_res.json()
                            status = status_data.get("status")
                            
                            if status == "completed":
                                video_url = status_data.get("content_url")
                                progress_bar.progress(100)
                                status_text.text("Render complete!")
                                break
                            elif status == "failed":
                                status_text.text("Render failed on server side.")
                                break
                        
                        if video_url:
                            st.video(video_url)
                            deduct_credit()
                            st.success(f"Video ready! Credits left: {st.session_state.requests_left}")
                        else:
                            st.error("Video processing timed out or failed.")
                    else:
                        st.error(f"Failed to start video job: {job_data}")
                except Exception as e:
                    st.error(f"Request failed: {e}")

# Footer
st.markdown("<hr><p style='text-align:center; color:#555;'>Heydoctor AI Studio &bull; Built for High-Performance Generation</p>", unsafe_allow_html=True)

