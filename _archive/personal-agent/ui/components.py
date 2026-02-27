import streamlit as st
import datetime
import psutil
from rag.ingest_custom import ingest_documents_custom
from rag.vector_db import add_documents_to_db

def render_header():
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        current_hour = datetime.datetime.now().hour
        greeting = "Good Morning" if 5 <= current_hour < 12 else "Good Afternoon" if 12 <= current_hour < 18 else "Good Evening"
        st.title(f"🤖 {greeting}, Sir.")
        st.caption(f"Jarvis System v2.0 | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with col_h2:
        if st.button("🔄 System Reboot", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    st.divider()

def _get_system_metrics():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return cpu, mem, disk

def render_sidebar():
    with st.sidebar:
        st.image("https://api.dicebear.com/9.x/bottts-neutral/svg?seed=JarvisV2", width=120)
        st.markdown("### 🧬 Status Check")
        
        cpu, mem, disk = _get_system_metrics()
        
        st.markdown("**CPU Core**")
        st.progress(cpu / 100, text=f"{cpu}%")
        st.markdown("**Memory**")
        st.progress(mem / 100, text=f"{mem}%")
        st.markdown("**Storage**")
        st.progress(disk / 100, text=f"{disk}%")
        
        st.divider()
        
        # Legal & Privacy
        with st.expander("⚖️ Legal & Privacy"):
            st.caption("""
            **[Disclaimer]**
            1. This application runs locally.
            2. Text input is sent to Google Gemini API.
            3. Do NOT input sensitive personal information.
            4. The developer is not responsible for any issues.
            """)
            
        st.markdown("### 📚 Knowledge Base")
        with st.expander("Ingest Options"):
            if st.button("📥 Scan 'data/' Folder", use_container_width=True):
                with st.spinner("Processing..."):
                    chunks = ingest_documents_custom("projects/personal-agent/data")
                    add_documents_to_db(chunks)
                st.toast(f"Indexed {len(chunks)} chunks!", icon="✅")

def render_dashboard_cards(weather, news_items):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("#### 🌤️ Weather Link")
        if weather:
            st.metric("Temperature", weather['temp'], weather['humidity'])
            st.caption(f"{weather['condition']} | {weather['wind']}")
        else:
            st.metric("Temperature", "--", "Offline")
    
    with c2:
        st.markdown("#### 📰 Global Feed")
        st.metric("Unread Items", str(len(news_items)), "Tech/Global")
        st.caption("Updated: Just now")
        
    with c3:
        st.markdown("#### ⚙️ Action")
        return st.button("🚀 ACTIVATE BRIEFING", type="primary", use_container_width=True)

def render_voice_visualizer():
    st.markdown("#### 🎙️ Voice Core (Simulation)")
    
    # CSS for Audio Wave Animation
    st.markdown("""
    <style>
    .voice-box {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 60px;
        background: #1e1e1e;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    
    .bar {
        background: #00ADB5;
        width: 6px;
        height: 10px;
        margin: 0 4px;
        border-radius: 5px;
        animation: wave 1s ease-in-out infinite;
    }
    
    .bar:nth-child(1) { animation-delay: 0.0s; }
    .bar:nth-child(2) { animation-delay: 0.1s; }
    .bar:nth-child(3) { animation-delay: 0.2s; }
    .bar:nth-child(4) { animation-delay: 0.3s; }
    .bar:nth-child(5) { animation-delay: 0.4s; }
    
    @keyframes wave {
        0%, 100% { height: 10px; opacity: 0.5; }
        50% { height: 40px; opacity: 1; background: #FF4B4B; }
    }
    </style>
    
    <div class="voice-box">
        <div class="bar"></div>
        <div class="bar"></div>
        <div class="bar"></div>
        <div class="bar"></div>
        <div class="bar"></div>
    </div>
    """, unsafe_allow_html=True)
