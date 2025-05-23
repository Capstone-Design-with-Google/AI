import os
import re
import json
from PIL import Image
import google.generativeai as genai

from config import GOOGLE_API_KEY_GEMINI, GEMINI_VISION_MODEL_NAME, EXTRACTED_TEXTS_FOLDER, IMAGES_RAW_FOLDER
from utils.file_utils import ensure_folder_exists, save_text_to_file

_gemini_configured = False

def configure_gemini_api():
    global _gemini_configured
    if not GOOGLE_API_KEY_GEMINI:
        raise ValueError("Gemini API 키가 설정되지 않았습니다. config.py 또는 환경변수를 확인하세요.")
    if not _gemini_configured:
        genai.configure(api_key=GOOGLE_API_KEY_GEMINI)
        _gemini_configured = True
        # print("Gemini API 설정 완료 (image_processor).")

def extract_text_from_single_image_ocr(image_path, model):
    extracted_labels = []
    try:
        img = Image.open(image_path)
        prompt_ocr = """
        아래 이미지는 문서 이미지 또는 포스터입니다.
        이미지에 포함된 모든 텍스트를 2차원 박스 좌표와 함께 JSON 형식으로 반환하세요.
        형식은 다음과 같아야 합니다:

        [
          {"box_2d": [x1, y1, x2, y2], "label": "텍스트 내용"},
          ...
        ]

        절대로 설명하지 말고, 감상하지 말고, 영어로 추론하지 말고,
        OCR로 인식한 한글 텍스트와 좌표만 JSON으로 출력하세요.
        """
        print(f"  > '{os.path.basename(image_path)}' OCR 처리 중...")
        response = model.generate_content([prompt_ocr, img])
        
        json_text_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text, re.DOTALL)
        if json_text_match:
            json_text = json_text_match.group(1)
        else:
            json_text = response.text.strip()
            if not (json_text.startswith('[') and json_text.endswith(']')) and \
               not (json_text.startswith('{') and json_text.endswith('}')):
                print(f"  ⚠️ '{os.path.basename(image_path)}' 에서 OCR 응답이 예상된 JSON 형식이 아닙니다. 응답 일부: {json_text[:100]}...")
                return []

        extracted_data = json.loads(json_text)
        for item in extracted_data:
            if "label" in item and item["label"]:
                extracted_labels.append(item["label"].strip())
        print(f"  > '{os.path.basename(image_path)}' 에서 텍스트 {len(extracted_labels)}개 블록 추출 완료.")

    except FileNotFoundError:
        print(f"  ⚠️ 파일을 찾을 수 없습니다: {image_path}")
    except json.JSONDecodeError as e_json:
        print(f"  ⚠️ '{os.path.basename(image_path)}' JSON 파싱 오류: {e_json}")
        print(f"  Gemini OCR 응답 일부: {response.text[:200]}...")
    except Exception as e:
        print(f"  ⚠️ '{os.path.basename(image_path)}' OCR 처리 중 오류 발생: {e}")
    return extracted_labels

def extract_texts_from_images_in_folder(image_folder_path=IMAGES_RAW_FOLDER):
    configure_gemini_api()
    model = genai.GenerativeModel(GEMINI_VISION_MODEL_NAME)
    print(f"Gemini Vision 모델 ({GEMINI_VISION_MODEL_NAME}) 로드 완료 (for OCR).")

    all_extracted_texts = []
    print(f"\n=== '{image_folder_path}' 폴더 내 이미지에서 OCR 텍스트 추출 시작 ===")
    if not os.path.exists(image_folder_path) or not os.listdir(image_folder_path):
        print(f"'{image_folder_path}' 폴더가 비어있거나 존재하지 않습니다. 텍스트 추출을 건너<0xEB><0x9B><0x84>니다.")
        return all_extracted_texts

    image_files = [f for f in os.listdir(image_folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    if not image_files:
        print("OCR을 수행할 유효한 이미지 파일이 없습니다.")
        return all_extracted_texts

    for fname in image_files:
        img_path = os.path.join(image_folder_path, fname)
        texts_from_img = extract_text_from_single_image_ocr(img_path, model)
        all_extracted_texts.extend(texts_from_img)

    print(f"\n총 {len(all_extracted_texts)}개의 텍스트 조각을 모든 이미지에서 OCR로 추출했습니다.")
    if all_extracted_texts:
        ensure_folder_exists(EXTRACTED_TEXTS_FOLDER)
        extracted_texts_file_path = os.path.join(EXTRACTED_TEXTS_FOLDER, "ocr_extracted_texts.txt")
        save_text_to_file("\n".join(all_extracted_texts), extracted_texts_file_path)
    else:
        print("\nOCR로 추출된 텍스트가 없어 파일을 저장하지 않습니다.")
    return all_extracted_texts