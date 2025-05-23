import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

GOOGLE_API_KEY_GEMINI = os.getenv("GOOGLE_API_KEY_GEMINI")
GCP_SERVICE_ACCOUNT_KEY_PATH = os.path.join(PROJECT_ROOT_DIR, "credentials", "project-team3-459012-0595dc85efb1.json") # 실제 파일명으로 수정

OUTPUT_DIR = os.path.join(PROJECT_ROOT_DIR, "output")
IMAGES_RAW_FOLDER = os.path.join(OUTPUT_DIR, "images_raw")
EXTRACTED_TEXTS_FOLDER = os.path.join(OUTPUT_DIR, "extracted_texts")
AUDIO_CLIPS_FOLDER = os.path.join(OUTPUT_DIR, "audio_clips")
VIDEOS_FOLDER = os.path.join(OUTPUT_DIR, "videos")

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
SELENIUM_WAIT_TIMEOUT = 20
IMAGE_DOWNLOAD_TIMEOUT = 15

GEMINI_VISION_MODEL_NAME = 'gemini-1.5-flash' # OCR 및 이미지 추천에 사용
GEMINI_TEXT_MODEL_NAME = 'gemini-1.0-pro'   # 나레이션 및 씬 스크립트 생성에 사용

TTS_LANGUAGE_CODE = "ko-KR"
TTS_VOICE_NAME_NEURAL = "ko-KR-Neural2-B"

VIDEO_FPS = 24
VIDEO_RESOLUTION = (720, 1280)
DEFAULT_FONT_PATH_WIN = "malgun.ttf"
DEFAULT_FONT_PATH_MAC = "/Library/Fonts/AppleGothic.ttf"
DEFAULT_FONT_PATH_LINUX = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

def initialize_project_folders():
    folders_to_create = [
        OUTPUT_DIR, IMAGES_RAW_FOLDER, EXTRACTED_TEXTS_FOLDER,
        AUDIO_CLIPS_FOLDER, VIDEOS_FOLDER
    ]
    for folder in folders_to_create:
        os.makedirs(folder, exist_ok=True)
    print("프로젝트 폴더 초기화 완료.")

if __name__ == '__main__':
    initialize_project_folders()
    print(f"Project Root: {PROJECT_ROOT_DIR}")
    if GOOGLE_API_KEY_GEMINI:
        print("Gemini API Key is set.")
    else:
        print("⚠️ Gemini API Key is NOT set.")
    if os.path.exists(GCP_SERVICE_ACCOUNT_KEY_PATH):
        print(f"GCP Service Account Key file found at: {GCP_SERVICE_ACCOUNT_KEY_PATH}")
    else:
        print(f"⚠️ GCP Service Account Key file NOT found at: {GCP_SERVICE_ACCOUNT_KEY_PATH}")