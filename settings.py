import os

DATA_FOLDER = "data"
VECTOR_STORE_PATH = "faiss_index"

WHISPER_MODEL_NAME = "base"
TTS_LANG = "en"
SERVER_RECORD_SECONDS = 7

try:
    import sounddevice
    SOUND_DEVICE_AVAILABLE = True
except Exception:
    SOUND_DEVICE_AVAILABLE = False
