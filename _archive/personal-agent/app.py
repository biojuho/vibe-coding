import streamlit as st
import os
import sys
import psutil
import platform
import datetime
import time
import logging
import html

# Setup Logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

log_filename = os.path.join(log_dir, f"agent_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(module)s: %(message)s',
    encoding='utf-8',
    force=True 
)

logging.info("🚀 System Startup: Personal Agent UI initialized")

from utils.scheduler import scheduler

# 1. Page Config
st.set_page_config(
    page_title="Joolife Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

from config import USER_NAME

# 2. Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 3. System Init
if "scheduler_started" not in st.session_state:
    try:
        scheduler.start()
        st.session_state["scheduler_started"] = True
    except Exception as e:
        print(f"Scheduler Init Error: {e}")

# 4. Sidebar Greeting
with st.sidebar:
    st.title(f"👋 Hello, {USER_NAME}")

# 5. Load UI Modules
from ui.styles import load_css, get_sentiment_style
from ui.components import render_header, render_sidebar, render_dashboard_cards, render_voice_visualizer
from utils.memory import load_memory, save_memory, clear_memory

# Apply Styles
load_css()

# Render Header
render_header()

# Render Voice Visualizer (Top of main area for visibility, or Sidebar?)
# Users often want to see "The Agent is listening" near the top.
# Let's put it in the Sidebar for now as per plan.

# 6. Lazy Load Functions
@st.cache_resource
def load_modules():
    try:
        from briefing.generator import generate_briefing
        from briefing.weather import get_weather_data
        from briefing.news import get_news_data
        from rag.query import query_rag
        from rag.ingest_custom import ingest_documents_custom
        from rag.vector_db import add_documents_to_db
        return generate_briefing, get_weather_data, get_news_data, query_rag, ingest_documents_custom, add_documents_to_db
    except Exception as e:
        logging.error(f"Module Load Error: {e}")
        return None, None, None, None, None, None

# Load modules
with st.spinner("Initializing Jarvis Core Systems..."):
    generate_briefing, get_weather_data, get_news_data, query_rag, ingest_documents_custom, add_documents_to_db = load_modules()

if not generate_briefing:
    st.error("❌ Critical System Failure: AI Modules Offline.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    render_voice_visualizer() # Add Visualizer at top of sidebar
    # --- Scheduler Status ---
    with st.sidebar.expander("🕰️ Scheduled Tasks", expanded=False):
        jobs = scheduler.list_jobs()
        if jobs:
            for job in jobs:
                st.write(f"- {job.next_run} : {job.job_func.__name__}")
        else:
            st.info("No active schedules.")

    # --- System Metrics ---
render_sidebar()

# --- Main Interface ---
tab1, tab2 = st.tabs(["🌤️ Morning Deck", "🧠 Neural Link"])

with tab1:
    st.markdown("### 📡 Operational Dashboard")
    
    # Fetch Data
    with st.spinner("Syncing Environmental Sensors..."):
        weather = get_weather_data("Seoul")
        news_items = get_news_data(limit=10)
    
    # Render Cards
    generate_btn = render_dashboard_cards(weather, news_items)
    
    st.divider()
    
    if generate_btn:
        # Storytelling Loading
        with st.status("Processing Briefing Sequence...", expanded=True) as status:
            st.write("🔍 Analyzing Weather Patterns...")
            time.sleep(1)
            st.write("🌍 Scanning Global News Networks...")
            time.sleep(1)
            st.write("📝 Drafting Intelligence Report...")
            briefing_text = generate_briefing()
            status.update(label="Briefing Generated", state="complete", expanded=True)
            
        col_res1, col_res2 = st.columns([2, 1])
        
        with col_res1:
            with st.container(border=True):
                st.markdown(briefing_text)
                
        with col_res2:
            st.markdown("#### 🔊 Audio Stream")
            # Text-to-Speech
            with st.spinner("Synthesizing Voice..."):
                try:
                    from utils.tts import text_to_speech
                    os.makedirs("data/audio", exist_ok=True)
                    
                    audio_file = text_to_speech(briefing_text, output_dir="data/audio")
                    
                    if audio_file:
                        st.audio(audio_file, format='audio/mp3')
                        st.success("Transmission Active")
                    else:
                        st.warning("Audio Signal Lost")
                except Exception as e:
                    st.error(f"Audio Error: {e}")

with tab2:
    st.markdown("### 🧠 Neural Link")
    
    if "messages" not in st.session_state:
        st.session_state.messages = load_memory()

    # Memory Management Controls
    with st.expander("🧠 Memory Controls"):
        if st.button("🗑️ Forget Everything"):
            clear_memory()
            st.session_state.messages = []
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🤖"):
            safe_content = html.escape(message["content"])
            # Apply Style
            if message["role"] == "assistant":
                style_class = get_sentiment_style(message["content"])
                st.markdown(f'<div class="chat-container {style_class}">{safe_content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-container bubble-user">{safe_content}</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("Command Interface..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        safe_prompt = html.escape(prompt)
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="chat-container bubble-user">{safe_prompt}</div>', unsafe_allow_html=True)

        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            full_response = ""

            # Simple Spinner for Query
            with st.spinner("Computing..."):
                response = query_rag(prompt)

                # Determine final style
                final_style = get_sentiment_style(response)

                for chunk in response.split():
                    full_response += chunk + " "
                    time.sleep(0.02) # Faster typing
                    safe_response = html.escape(full_response)
                    # Render with Dynamic Style
                    message_placeholder.markdown(f'<div class="chat-container {final_style}">{safe_response}▌</div>', unsafe_allow_html=True)

                safe_response = html.escape(full_response)
                message_placeholder.markdown(f'<div class="chat-container {final_style}">{safe_response}</div>', unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_memory(st.session_state.messages) # Auto-save
