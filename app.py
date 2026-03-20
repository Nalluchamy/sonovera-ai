import os
import sys

from patch_transformers import patch_transformers
patch_transformers()

import time
import streamlit as st
import json
from dotenv import load_dotenv
from chatbot_engine import ChatbotEngine
from database import ChatDatabase
from audio_recorder_streamlit import audio_recorder
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Load environment variables
load_dotenv()

# MUST be the very first Streamlit command
st.set_page_config(page_title="🎙️ AI Voice Clone Chatbot", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("static/style.css")

# Auto-play Audio JS
def autoplay_audio(audio_path):
    with open(audio_path, "rb") as f:
        data = f.read()
        import base64
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/wav;base64,{b64}" type="audio/wav">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# Ensure directories exist
VOICE_SAMPLES_DIR = os.getenv("VOICE_SAMPLES_DIR", "voice_samples/")
AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "generated_audio/")
os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

# Initialize Database
db = ChatDatabase()

# Load Personas
with open("personas.json", "r") as f:
    personas = json.load(f)

AVATAR_PATH = os.path.join(VOICE_SAMPLES_DIR, "ai_avatar.png")
# Note: I'll assume the generated image is moved/renamed to this path for consistency

# Authentication Setup
config = {
    'credentials': {
        'usernames': {
            'admin': {
                'email': 'admin@example.com',
                'name': 'Administrator',
                'password': 'admin' # In a real app, use hashed passwords
            },
            'user1': {
                'email': 'user1@example.com',
                'name': 'Test User',
                'password': 'password123'
            }
        }
    },
    'cookie': {
        'expiry_days': 30,
        'key': 'voice_clone_auth',
        'name': 'voice_clone_cookie'
    }
}

# In a production app, we would hash these passwords. 
# For this demo, we'll use the plain text for simplicity but ideally:
# authenticator = stauth.Authenticate(config['credentials'], ...)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login Widget
authenticator.login('main')

if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.write(f'Welcome *{st.session_state["name"]}*')
    
    username = st.session_state["username"]
    name = st.session_state["name"]
    
    if "is_speaking" not in st.session_state:
        st.session_state.is_speaking = False
    
    # Initialize Database and Chatbot
    db = ChatDatabase()
    
    # Initialize Session State — heavy models are loaded LAZILY (not at startup)
    if "messages" not in st.session_state:
        # Load history from DB on startup for the authenticated user
        st.session_state.messages = db.get_all_messages(username)
    if "voice_loaded" not in st.session_state:
        st.session_state.voice_loaded = False
    if "chat_engine" not in st.session_state:
        st.session_state.chat_engine = ChatbotEngine()
    if "voice_engine" not in st.session_state:
        st.session_state.voice_engine = None  # loaded on demand
    if "stt_engine" not in st.session_state:
        st.session_state.stt_engine = None   # loaded on demand

    # ================= SIDEBAR =================
    with st.sidebar:
        st.title("🎙️ Chat Settings")

        # Talking Avatar
        if os.path.exists(AVATAR_PATH):
            pulse_css = """
            <style>
            @keyframes pulse {
                0% { transform: scale(1); filter: brightness(1); border-color: #6366f1; }
                50% { transform: scale(1.02); filter: brightness(1.2); border-color: #818cf8; }
                100% { transform: scale(1); filter: brightness(1); border-color: #6366f1; }
            }
            .speaking-avatar {
                border-radius: 20px;
                border: 4px solid #6366f1;
                animation: pulse 1.5s infinite ease-in-out;
                box-shadow: 0 0 25px rgba(99, 102, 241, 0.6);
            }
            .idle-avatar {
                border-radius: 20px;
                border: 2px solid #333;
                filter: grayscale(0.3);
                opacity: 0.8;
            }
            </style>
            """
            st.markdown(pulse_css, unsafe_allow_html=True)
            img_class = "speaking-avatar" if st.session_state.is_speaking else "idle-avatar"
            # We use a custom div for the animation class
            st.image(AVATAR_PATH, use_container_width=True) # type: ignore
            status_color = "#6366f1" if st.session_state.is_speaking else "#666"
            status_text = "Speaking..." if st.session_state.is_speaking else "Idle"
            
            if st.session_state.is_speaking:
                st.markdown("""
                <div class="waveform-container">
                    <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                    <div class="bar"></div><div class="bar"></div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f'<div style="text-align: center; color: {status_color}; font-weight: bold; margin-top: -10px;">{status_text}</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # Character Persona
        st.markdown("### 🎭 Character Persona")
        persona_name = st.selectbox("Select Persona", list(personas.keys()))
        selected_persona = personas[persona_name]
        st.info(selected_persona["description"])
        st.session_state.chat_engine.set_system_prompt(selected_persona["system_prompt"])
        
        st.markdown("---")
        # AI Provider
        st.markdown("### 🤖 AI Provider")
        llm_provider = st.selectbox("LLM Provider", ["NVIDIA", "OpenAI", "Ollama (Local)"])
        if llm_provider == "Ollama (Local)":
            st.info("Make sure Ollama is running (`ollama serve`). Default model: `llama3`")

        
        st.markdown("---")
        st.markdown("### 🔊 Voice Clone")
        
        # Voice Library
        st.markdown("### 📚 Voice Library")
        existing_voices = [f for f in os.listdir(VOICE_SAMPLES_DIR) if f.endswith(('.wav', '.mp3'))]
        
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_voice = st.selectbox("Select a Voice", ["Upload New..."] + existing_voices, label_visibility="collapsed")
        with col2:
            if selected_voice != "Upload New..." and st.button("🗑️", help="Delete this voice"):
                os.remove(os.path.join(VOICE_SAMPLES_DIR, selected_voice))
                st.rerun()

        if selected_voice == "Upload New...":
            uploaded_file = st.file_uploader("Upload Voice Sample", type=["wav", "mp3"])
            if uploaded_file is not None:
                new_name = st.text_input("Name this voice (optional)", value=uploaded_file.name)
                if st.button("Save to Library"):
                    file_path = os.path.join(VOICE_SAMPLES_DIR, new_name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"Saved {new_name}!")
                    st.rerun()
        
        if selected_voice != "Upload New...":
            file_path = os.path.join(VOICE_SAMPLES_DIR, selected_voice)
            try:
                # Lazy-load the voice engine only when first needed
                if st.session_state.voice_engine is None:
                    with st.spinner("Loading voice cloning model (first time only, ~1.8 GB)..."):
                        from voice_clone import VoiceCloneEngine
                        st.session_state.voice_engine = VoiceCloneEngine()
                st.session_state.voice_engine.load_speaker(file_path)
                st.session_state.voice_loaded = True
                st.success(f"Voice '{selected_voice}' loaded!")
            except Exception as e:
                st.error(f"Error loading voice: {e}")

        language_options = {
            "English": "en", 
            "Spanish": "es", 
            "French": "fr", 
            "German": "de", 
            "Italian": "it", 
            "Portuguese": "pt", 
            "Chinese": "zh", 
            "Japanese": "ja"
        }
        selected_lang_name = st.selectbox("Language", list(language_options.keys()))
        language_code = language_options[selected_lang_name] # type: ignore
        
        whisper_model = st.selectbox("Whisper Model", ["tiny", "base", "small"], index=1)
        
        st.markdown("---")
        # Knowledge Base (RAG)
        st.markdown("### 🧠 Knowledge Base")
        kb_file = st.file_uploader("Upload context (txt/md)", type=["txt", "md"])
        kb_context = ""
        if kb_file:
            kb_context = kb_file.read().decode("utf-8")
            st.success(f"Attached: {kb_file.name}")

        st.markdown("---")
        web_search_enabled = st.toggle("🔍 Enable Web Search (Real-time Facts)", value=False)
        translation_mode = st.toggle("🌍 Multilingual / Translation Mode", value=False)
        use_microphone = st.toggle("Enable Microphone Input (Upload Audio)", value=False)
        
        st.markdown("---")
        # Hardware Status
        st.markdown("### 🖥️ Hardware Status")
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            st.success(f"GPU: {gpu_name}")
        else:
            st.warning("Running on CPU (No GPU found)")

        st.markdown("---")
        if st.button("🗑️ Clear Chat History"):
            db.clear_user_history(username)
            st.session_state.messages = []
            st.rerun()

    # ================= MAIN PAGE =================
    st.title("AI Chatbot with Voice Cloning")

    tab1, tab2 = st.tabs(["💬 Chat", "📚 History & Gallery"])

    with tab1:
        # Display Chat History for current session
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "image" in msg and msg["image"]:
                    st.image(msg["image"], caption="Uploaded Image", width=300)
                if "audio" in msg and msg["audio"]:
                    st.audio(msg["audio"])

        # Input Area
        st.markdown("### 🗣️ Say something...")

        # Image Upload for Vision
        uploaded_image = st.file_uploader("📸 Share an image (optional)", type=["jpg", "jpeg", "png"])
        image_b64 = None
        image_data = None

        if uploaded_image:
            image_data = uploaded_image.read()
            import base64
            image_b64 = base64.b64encode(image_data).decode()
            st.image(image_data, caption="Preview", width=150)

        col_rec, col_input = st.columns([1, 6])
        with col_rec:
            audio_bytes = audio_recorder(text="", icon_size="2x", neutral_color="#6366f1")

        user_text = ""
        if audio_bytes:
            # Save recording to temp file
            temp_audio_path = os.path.join(AUDIO_OUTPUT_DIR, f"rec_{int(time.time())}.wav")
            with open(temp_audio_path, "wb") as f:
                f.write(audio_bytes)
            
            with st.spinner("Transcribing..."):
                if st.session_state.stt_engine is None:
                    from speech_to_text import SpeechToTextEngine
                    st.session_state.stt_engine = SpeechToTextEngine()
                user_text = st.session_state.stt_engine.transcribe(temp_audio_path)
                st.success(f"Captured: {user_text}")

        if not user_text:
            if use_microphone:
                user_audio = st.file_uploader("Upload Speech Input", type=["wav", "mp3"], key="speech_input")
                if user_audio is not None:
                    audio_path = os.path.join(AUDIO_OUTPUT_DIR, f"input_{int(time.time())}.wav")
                    with open(audio_path, "wb") as f:
                        f.write(user_audio.getbuffer())
                    with st.spinner("Transcribing audio..."):
                        # Lazy-load STT engine when first needed
                        if st.session_state.stt_engine is None:
                            from speech_to_text import SpeechToTextEngine
                            st.session_state.stt_engine = SpeechToTextEngine()
                        user_text = st.session_state.stt_engine.transcribe(audio_path)
                        st.success(f"Transcribed: {user_text}")
                    if st.button("Send Speech Message"):
                        # The text is already in user_text
                        pass
                    else:
                        user_text = "" # Wait for send button
            else:
                user_text = st.chat_input("Type your message here...")


        # Process User Input
        if user_text:
            # 1. Add user message to history
            st.session_state.messages.append({
                "role": "user", 
                "content": user_text,
                "image": image_data if image_data else None
            })
            db.add_message(username, "user", user_text) # Note: DB doesn't store blobs yet, just text context
            with st.chat_message("user"):
                st.markdown(user_text)
                if image_data:
                    st.image(image_data, width=300)

            # 2. Call chatbot engine
            with st.chat_message("assistant"):
                # Streaming response
                response_placeholder = st.empty()
                full_response = ""
                
                # history_for_api should exclude the current user message (added above)
                history_for_api = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                
                # We use st.write_stream because it's the modern Streamlit way
                reply_text = st.write_stream(st.session_state.chat_engine.respond_stream(
                    user_message=user_text,
                    history=history_for_api,
                    provider=llm_provider,
                    image_base64=image_b64,
                    translation_enabled=translation_mode,
                    knowledge_context=kb_context,
                    web_search_enabled=web_search_enabled
                ))

            # 3. Voice Clone Synthesize if loaded
            if st.session_state.voice_loaded:
                st.session_state.is_speaking = True
                timestamp = int(time.time())
                output_path = os.path.join(AUDIO_OUTPUT_DIR, f"response_{timestamp}.wav")
                
                # Streaming Synthesis & Playback
                import numpy as np
                import soundfile as sf
                full_wav = []
                
                try:
                    # We synthesize and play chunks incrementally
                    chunk_container = st.container()
                    for chunk, sr in st.session_state.voice_engine.synthesize_stream(reply_text, language_code):
                        full_wav.append(chunk)
                        with chunk_container:
                            # Use autoplay for the first chunk to start immediately
                            if len(full_wav) == 1:
                                temp_chunk_path = os.path.join(AUDIO_OUTPUT_DIR, f"chunk_{timestamp}.wav")
                                sf.write(temp_chunk_path, chunk, sr)
                                autoplay_audio(temp_chunk_path)
                            else:
                                st.audio(chunk, sample_rate=sr)
                    
                    # Save final combined audio for history
                    final_wav = np.concatenate(full_wav)
                    sf.write(output_path, final_wav, 24000)
                    audio_file_path = output_path
                    
                    st.success("Synthesis complete.")
                    with st.expander("Download full response"):
                        with open(audio_file_path, "rb") as f:
                            st.download_button(
                                label="Download Audio",
                                data=f,
                                file_name=f"response_{timestamp}.wav",
                                mime="audio/wav",
                                key=f"dl_{timestamp}"
                            )
                except Exception as e:
                    st.error(f"Failed to synthesize voice: {e}")
                
                st.session_state.is_speaking = False

                # 4. Add assistant reply to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply_text,
                    "audio": audio_file_path
                })
                db.add_message(username, "assistant", reply_text, audio_file_path)
            st.rerun()

    with tab2:
        st.header("📜 Conversation History")
        all_messages = db.get_all_messages(username)
        
        if not all_messages:
            st.info("No messages found in history.")
        else:
            # Group messages by date
            from datetime import datetime
            for msg in reversed(all_messages): # Show newest first in history gallery?
                with st.expander(f"[{msg['timestamp']}] {msg['role'].capitalize()}: {msg['content'][:50]}..."):
                    st.write(f"**Role:** {msg['role']}")
                    st.write(f"**Time:** {msg['timestamp']}")
                    st.write(f"**Content:** {msg['content']}")
                    if msg['audio'] and os.path.exists(msg['audio']):
                        st.audio(msg['audio'])
                        with open(msg['audio'], "rb") as f:
                            st.download_button(
                                label="Download Audio",
                                data=f,
                                file_name=os.path.basename(msg['audio']),
                                mime="audio/wav",
                                key=f"gal_{msg['timestamp']}"
                            )
                    elif msg['audio']:
                        st.warning("Audio file not found or deleted.")

        st.divider()
        st.header("🎵 Audio Gallery")
        # List all files in generated_audio
        audio_files = [f for f in os.listdir(AUDIO_OUTPUT_DIR) if f.endswith(('.wav', '.mp3'))]
        if not audio_files:
            st.info("No generated audio files found.")
        else:
            cols = st.columns(2)
            for i, af in enumerate(reversed(audio_files)):
                with cols[i % 2]:
                    with st.container(border=True):
                        st.write(f"📄 {af}")
                        st.audio(os.path.join(AUDIO_OUTPUT_DIR, af))
                        if st.button(f"🗑️ Delete", key=f"del_{af}"):
                            os.remove(os.path.join(AUDIO_OUTPUT_DIR, af))
                            st.rerun()
elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
