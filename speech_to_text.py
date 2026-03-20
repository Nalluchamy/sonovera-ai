import os
import whisper
from typing import Optional
from dotenv import load_dotenv

import torch
# Load environment variables
load_dotenv()

class SpeechToTextEngine:
    """
    Engine for transcribing audio using OpenAI's Whisper model.
    """
    def __init__(self) -> None:
        """
        Initializes the internal Whisper model.
        Defaults to the 'base' model if not specified in the environment.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = os.getenv("WHISPER_MODEL", "base")
        # Load with FP16 on GPU for speed
        self.model = whisper.load_model(self.model_name, device=self.device)


    def transcribe(self, audio_path: str) -> str:
        """
        Loads and transcribes an audio file.

        Args:
            audio_path (str): The path to the audio file to transcribe.

        Returns:
            str: The transcribed text string.
        """
        if not os.path.exists(audio_path):
            return "Error: Audio file not found."

        try:
            result = self.model.transcribe(audio_path)
            return result.get("text", "").strip() # type: ignore
        except Exception as e:
            return f"Error transcribing audio: {str(e)}"
