import streamlit as st

def load_css():
    st.markdown("""
    <style>
    /* Global vars */
    :root {
        --primary: #FF4B4B;
        --accent: #00ADB5;
        --bg-dark: #0E1117;
        --card-bg: #262730;
        --text-light: #FAFAFA;
    }
    
    .stApp {
        background-color: var(--bg-dark);
        color: var(--text-light);
    }
    
    /* Metrics / Cards */
    div[data-testid="stMetric"] {
        background-color: var(--card-bg);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid var(--accent);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }
    
    /* Buttons */
    .stButton>button {
        background-color: var(--primary);
        color: white;
        border-radius: 20px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff6b6b;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.5);
    }
    
    /* Status Container */
    div[data-testid="stStatusWidget"] {
        background-color: var(--card-bg);
        border: 1px solid var(--accent);
        border-radius: 10px;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
        text-shadow: 0 0 5px rgba(255, 255, 255, 0.1);
    }
    
    /* Chat Bubbles (Futuristic) */
    .chat-container {
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .bubble-user {
        background: rgba(0, 173, 181, 0.2);
        border: 1px solid #00ADB5;
        color: #E0E0E0;
        text-align: right;
    }
    
    .bubble-bot-neutral {
        background: rgba(40, 44, 52, 0.8);
        border-left: 4px solid #aaa;
        color: #E0E0E0;
    }
    
    .bubble-bot-happy {
        background: rgba(40, 44, 52, 0.8);
        border-left: 4px solid #FFD700; /* Gold */
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
        color: #FFF;
    }
    
    .bubble-bot-thinking {
        background: rgba(40, 44, 52, 0.8);
        border-left: 4px solid #FF4B4B; /* Red */
        animation: pulse 2s infinite;
        color: #E0E0E0;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.4); }
        70% { box-shadow: 0 0 10px 10px rgba(255, 75, 75, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0); }
    }
    </style>
    """, unsafe_allow_html=True)

def get_sentiment_style(text):
    """Simple heuristic for sentiment style"""
    positive = ['좋아', '멋져', '감사', '성공', 'happy', 'great', 'good', 'success', 'love', '❤️', '😊']
    thinking = ['음...', '잠시만', 'analys', 'thinking', 'comput', 'search', '검색']
    
    if any(k in text.lower() for k in thinking):
        return "bubble-bot-thinking"
    elif any(k in text.lower() for k in positive):
        return "bubble-bot-happy"
    return "bubble-bot-neutral"
