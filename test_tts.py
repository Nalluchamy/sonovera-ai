import sys
import traceback
try:
    from TTS.api import TTS
    print("Success: TTS module loaded.")
except Exception as e:
    print("Error loading TTS:")
    traceback.print_exc()
    sys.exit(1)
