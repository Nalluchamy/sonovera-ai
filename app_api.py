import os
import time
import uuid
import shutil
from typing import List, Dict, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from patch_transformers import patch_transformers
patch_transformers()

from chatbot_engine import ChatbotEngine
from voice_clone import VoiceCloneEngine
from speech_to_text import SpeechToTextEngine

# Load environment variables
load_dotenv()

app = FastAPI(title="SONOVERA AI Voice Synthesis")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
VOICE_SAMPLES_DIR = os.getenv("VOICE_SAMPLES_DIR", "voice_samples/")
AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "generated_audio/")
os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

# Initialize engines
chat_engine = ChatbotEngine()
voice_engine: Optional[VoiceCloneEngine] = None
stt_engine: Optional[SpeechToTextEngine] = None

def get_voice_engine():
    global voice_engine
    if voice_engine is None:
        voice_engine = VoiceCloneEngine()
    return voice_engine

def get_stt_engine():
    global stt_engine
    if stt_engine is None:
        stt_engine = SpeechToTextEngine()
    return stt_engine

# Models for request/response
class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]]
    language: str = "en"

class ChatResponse(BaseModel):
    status: str
    reply: str
    audio_url: Optional[str] = None
    message: Optional[str] = None

# API Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # 1. Get LLM response
        print(f"[Chat] User: {request.message[:80]}...")
        reply_text = chat_engine.respond(
            user_message=request.message,
            history=request.history
        )
        print(f"[Chat] AI reply: {reply_text[:80]}...")
        
        audio_url = None
        # 2. Synthesize voice if a speaker is loaded
        if voice_engine is not None and voice_engine.speaker_wav:
            print(f"[Chat] Speaker loaded, synthesizing voice...")
            timestamp = int(time.time())
            filename = f"response_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
            output_path = os.path.join(AUDIO_OUTPUT_DIR, filename)
            
            voice_engine.synthesize(
                text=reply_text,
                output_path=output_path,
                language=request.language
            )
            audio_url = f"/audio/{filename}"
            print(f"[Chat] Audio ready: {audio_url}")
        else:
            print(f"[Chat] No speaker loaded, skipping voice synthesis")
            
        return ChatResponse(status="success", reply=reply_text, audio_url=audio_url)
    except Exception as e:
        print(f"[Chat] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(status="error", reply="", message=str(e))

@app.post("/api/upload_voice")
async def upload_voice(file: UploadFile = File(...)):
    global voice_engine
    try:
        file_path = os.path.join(VOICE_SAMPLES_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[Upload] Saved voice file: {file_path}")
        
        # Create engine if not yet created
        if voice_engine is None:
            print("[Upload] Creating VoiceCloneEngine (loading XTTS v2 model)...")
            voice_engine = VoiceCloneEngine()
        
        voice_engine.load_speaker(file_path)
        print(f"[Upload] Speaker loaded successfully: {file.filename}")
        
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        print(f"[Upload] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        filename = f"input_{int(time.time())}.wav"
        temp_path = os.path.abspath(os.path.join(AUDIO_OUTPUT_DIR, filename))
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        s_engine = get_stt_engine()
        text = s_engine.transcribe(temp_path)
        
        return {"status": "success", "text": text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Serve generated audio files
app.mount("/audio", StaticFiles(directory=AUDIO_OUTPUT_DIR), name="audio")

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
