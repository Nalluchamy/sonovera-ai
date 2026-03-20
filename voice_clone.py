import os
os.environ["COQUI_TOS_AGREED"] = "1"
import torch
from TTS.api import TTS

class VoiceCloneEngine:
    """
    Engine for voice cloning and text-to-speech generation using Coqui XTTS v2.
    Model loads eagerly at init for reliability.
    """
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[VoiceClone] Loading XTTS v2 model on {self.device}...")
        self.tts = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2"
        ).to(self.device)
        print("[VoiceClone] Model loaded successfully!")
        self.speaker_wav = None

    def load_speaker(self, audio_path: str):
        """Load a speaker voice sample for cloning."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        self.speaker_wav = audio_path
        print(f"[VoiceClone] Speaker loaded: {audio_path}")
        return True

    def synthesize(self, text: str, output_path: str, language: str = "en") -> str:
        """Convert text to speech in the cloned voice."""
        if self.speaker_wav is None:
            raise RuntimeError("No speaker loaded! Call load_speaker() first.")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        print(f"[VoiceClone] Synthesizing {len(text)} chars -> {output_path}")
        self.tts.tts_to_file(
            text=text,
            speaker_wav=self.speaker_wav,
            language=language,
            file_path=output_path
        )
        print(f"[VoiceClone] Audio saved: {output_path}")
        return output_path
