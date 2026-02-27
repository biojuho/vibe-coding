# 🤖 Personal Agent (Jarvis) by Joolife

> **Your AI-powered daily assistant.**
> © 2026 Joolife (쥬라프). All rights reserved.

The Personal Agent is an advanced AI assistant designed to automate daily tasks, provide information via RAG/Web Search, and interact naturally through voice.

## ✨ Key Features
*   **🗣️ Voice Interface**: Real-time Speech-to-Text (STT) and Text-to-Speech (TTS) with a visualizer.
*   **🧠 Intelligence**:
    *   **RAG**: Retrieval-Augmented Generation for local knowledge.
    *   **Deep Search**: Connected to the web for real-time information (`duckduckgo-search`).
    *   **Reflective Fallback**: Automatically searches the web if local data is insufficient.
*   **🕰️ Scheduler**: Background task execution (e.g., Morning Briefings).
*   **💾 Memory**: Long-term conversation history.
*   **🛠️ Automation**: Smart File Organizer (`Downloads` folder), System Monitoring, Desktop Control.

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   Google Gemini API Key (in `.env`)

### Installation
```bash
pip install -r requirements.txt
```

### Usage
```bash
..\..\venv\Scripts\python.exe -m streamlit run app.py
```
*   **Voice**: Click the microphone icon to speak.
*   **Chat**: Type your query in the chat box.
*   **Dashboard**: View system stats and scheduled tasks in the sidebar.

### Readiness Check
```bash
..\..\venv\Scripts\python.exe ..\..\scripts\doctor.py
```

## 📄 License
This project is licensed under the terms of the Joolife Proprietary License. See `LICENSE` for details.
