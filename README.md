---
title: SONOVERA AI Voice Synthesis
emoji: 🎙️
colorFrom: indigo
colorTo: green
sdk: docker
pinned: false
---

# SONOVERA — AI Voice Synthesis
 Chatbot

A premium, interactive AI chatbot featuring personalized voice cloning, real-time web search, and vision support. Built with Streamlit, NVIDIA AI, and Coqui TTS.

## ✨ Features

- **🗣️ Personalized Voice Cloning**: Upload a 5-10 second audio clip to clone any voice (powered by Coqui XTTS v2).
- **📝 Real-time Streaming**: Incremental audio synthesis and playback for ultra-low latency.
- **🔍 Web Search (RAG+)**: Toggle real-time search to ground AI responses in current facts (via DuckDuckGo).
- **📸 Vision Support**: Share images and discuss them with the AI.
- **🌍 Multilingual**: Support for 8+ languages including English, Spanish, French, German, Italian, Portuguese, Chinese, and Japanese.
- **🎭 Diverse Personas**: Switch between characters like "The Scientist", "The Storyteller", or "Shakespearean Actor".
- **📜 Session Management**: Persistent chat history and an audio gallery to browse past conversations.

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or 3.13 (Note: Built using Python 3.13 on Windows)
- FFmpeg (required for audio processing)
- NVIDIA GPU (Optional, but highly recommended for 2x faster synthesis)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd voice_clone_chatbot
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   Create a `.env` file based on `.env.example`:
   ```env
   NVIDIA_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ```

### Running the App

```bash
streamlit run app.py
```

## 🐳 Docker Deployment

The application is fully containerized and optimized for NVIDIA GPUs.

```bash
docker-compose up --build -d
```
Access the app at `http://localhost:8501`.

## 🛠️ Performance Tuning
The engine automatically detects NVIDIA GPUs and enables **FP16 Quantization**, reducing synthesis time by ~50% without loss of quality.

## 📜 License
This project is for educational/demonstration purposes. Refer to Coqui TTS and NVIDIA API licenses for commercial use.
