import os
import re
import json
import google.generativeai as genai
from PIL import Image # 이미지 추천 시 이미지 객체 사용 가능성

from config import (GOOGLE_API_KEY_GEMINI, GEMINI_TEXT_MODEL_NAME,
                    EXTRACTED_TEXTS_FOLDER, GEMINI_VISION_MODEL_NAME)
from utils.file_utils import ensure_folder_exists, save_text_to_file

_gemini_configured_scenario = False

def _ensure_gemini_configured_scenario():
    global _gemini_configured_scenario
    if not GOOGLE_API_KEY_GEMINI:
        raise ValueError("Gemini API 키가 설정되지 않았습니다. config.py 또는 환경변수를 확인하세요.")
    if not _gemini_configured_scenario:
        genai.configure(api_key=GOOGLE_API_KEY_GEMINI)
        _gemini_configured_scenario = True
        # print("Gemini API 설정 완료 (scenario_generator).")

def generate_initial_narration(product_name, ocr_texts):
    _ensure_gemini_configured_scenario()
    model = genai.GenerativeModel(GEMINI_TEXT_MODEL_NAME)
    print(f"Gemini Text 모델 ({GEMINI_TEXT_MODEL_NAME}) 로드 완료 (for initial narration).")

    if not ocr_texts:
        print("OCR 텍스트가 없어 초기 나레이션 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None
    combined_ocr_texts = "\n".join(ocr_texts)
    prompt_for_initial_narration = f"""
    당신은 창의적인 쇼츠 영상 광고 카피라이터입니다.
    다음은 '{product_name}' 상품의 상세 페이지 이미지들에서 추출된 텍스트 정보입니다.
    이 정보를 바탕으로, 사람들이 흥미를 느끼고 구매욕구를 자극할 만한,
    약 30초에서 1분 분량의 쇼츠 영상용 **전체 나레이션 스크립트**를 작성해주세요.

    요청사항:
    - 광고 느낌보다는 실제 사용자가 추천하는 듯한 친근하고 자연스러운 어투를 사용해주세요.
    - 상품의 핵심적인 장점과 특징을 명확하고 간결하게 강조해주세요.
    - 시청자의 궁금증을 유발하고, 다음 내용을 기대하게 만드는 흐름으로 구성해주세요.
    - 만약 추출된 텍스트 정보가 부족하거나 의미가 불분명한 부분이 있다면, 그 부분은 제외하거나 일반적인 긍정적 표현으로 대체해주세요.
    - 결과는 나레이션 텍스트만 응답해주세요. 다른 설명이나 제목은 필요 없습니다.

    추출된 텍스트:
    ---
    {combined_ocr_texts[:3000]} 
    ---
    생성할 전체 나레이션 스크립트:
    """
    print("\n=== Gemini API로 초기 전체 나레이션 생성 요청 ===")
    try:
        response = model.generate_content(prompt_for_initial_narration)
        initial_narration_script = response.text.strip()
        print("--- 생성된 초기 전체 나레이션 ---")
        print(initial_narration_script)
        ensure_folder_exists(EXTRACTED_TEXTS_FOLDER)
        narration_file_path = os.path.join(EXTRACTED_TEXTS_FOLDER, f"{product_name.replace(' ', '_')}_initial_narration.txt")
        save_text_to_file(initial_narration_script, narration_file_path)
        return initial_narration_script
    except Exception as e:
        print(f"초기 나레이션 생성 중 오류 발생: {e}")
        return None

def generate_scene_by_scene_script(product_name, initial_narration):
    if not initial_narration:
        print("초기 나레이션이 없어 씬별 스크립트 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None
    _ensure_gemini_configured_scenario()
    model = genai.GenerativeModel(GEMINI_TEXT_MODEL_NAME)
    print(f"Gemini Text 모델 ({GEMINI_TEXT_MODEL_NAME}) 로드 완료 (for scene script).")
    prompt_for_scene_script = f"""
    당신은 쇼츠 영상 편집 전문가입니다.
    다음은 '{product_name}' 상품의 쇼츠 영상용으로 작성된 **전체 나레이션 스크립트**입니다.
    이 전체 나레이션을 자연스럽게 여러 개의 씬(장면)으로 나누고,
    각 씬에 대한 [추천 이미지 설명, 해당 씬의 나레이션 부분, 화면 자막, 예상 시간(초)] 정보를 포함하는
    JSON 리스트 형식으로 결과를 만들어주세요.

    전체 나레이션 스크립트:
    ---
    {initial_narration}
    ---

    요구 사항:
    - 각 씬의 'narration' 필드에는 위 전체 나레이션 스크립트의 내용을 적절히 분배하거나, 해당 씬의 핵심 내용을 담도록 해주세요. 전체 나레이션의 흐름을 따라야 합니다.
    - 'recommended_image_description' 필드에는 해당 씬의 나레이션과 어울리는 이미지에 대한 간결하고 명확한 설명을 한국어로 작성해주세요. (예: "상품의 로고가 돋보이는 클로즈업 샷", "제품을 사용하는 만족스러운 표정의 사용자")
    - 'subtitle' 필드에는 해당 씬의 나레이션 핵심 내용을 강조하거나 시청자의 흥미를 끄는 짧은 문구(자막용)를 한국어로 작성해주세요.
    - 'duration_seconds' 필드에는 해당 씬의 나레이션 분량과 이미지 전환 속도를 고려하여 적절한 예상 시간(초 단위 숫자)을 지정해주세요. (예: 3, 5, 7 등)
    - 전체 영상 길이는 30초에서 1분 사이가 되도록 씬 구성과 시간 배분을 고려해주세요.
    - 결과는 반드시 아래 명시된 JSON 리스트 형식으로만 응답해주세요. 다른 설명은 일절 추가하지 마세요.

    출력 JSON 형식 예시:
    [
      {{"scene_number": 1, "recommended_image_description": "밝은 배경의 상품 전체 모습", "narration": "(초기 나레이션의 첫 부분 내용)", "subtitle": "✨ 드디어 공개! ✨", "duration_seconds": 5}},
      {{"scene_number": 2, "recommended_image_description": "상품의 특정 기능 사용 모습 클로즈업", "narration": "(초기 나레이션의 중간 부분 내용)", "subtitle": "이 놀라운 기능, 실화? 🤩", "duration_seconds": 7}}
    ]
    위 형식에 맞춰 씬별 스크립트를 생성해주세요.
    """
    print("\n=== Gemini API로 씬별 JSON 스크립트 생성 요청 ===")
    try:
        response = model.generate_content(prompt_for_scene_script)
        raw_response_text = response.text
        json_str = ""
        match = re.search(r'```json\s*([\s\S]*?)\s*```', raw_response_text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = raw_response_text.strip()
            if not (json_str.startswith('[') and json_str.endswith(']')):
                print(f"⚠️ 씬 스크립트 응답이 예상된 JSON 배열 형식이 아닙니다. 응답: {json_str[:200]}...")
                return None
        
        scene_script_data = json.loads(json_str)
        for i, scene in enumerate(scene_script_data):
            if "scene_number" not in scene: scene["scene_number"] = i + 1
        print("--- 생성된 씬별 스크립트 (JSON 파싱 성공) ---")
        ensure_folder_exists(EXTRACTED_TEXTS_FOLDER)
        scenario_file_path = os.path.join(EXTRACTED_TEXTS_FOLDER, f"{product_name.replace(' ', '_')}_scene_script.json")
        save_text_to_file(json.dumps(scene_script_data, indent=2, ensure_ascii=False), scenario_file_path)
        return scene_script_data
    except json.JSONDecodeError as e:
        print(f"🛑 씬 스크립트 JSON 파싱 중 오류 발생: {e}")
        print(f"--- Gemini 로부터 받은 원본 JSON 문자열 (파싱 시도 대상) ---\n{json_str}")
        return None
    except Exception as e_scene:
        print(f"씬별 스크립트 생성 중 오류 발생: {e_scene}")
        return None

def recommend_image_for_scene(image_description, available_image_paths, product_name=""):
    if not available_image_paths:
        print("  이미지 추천: 사용 가능한 이미지가 없습니다.")
        return None
    if not image_description:
        print("  이미지 추천: 이미지 설명이 없습니다. 첫 번째 이미지를 사용합니다.")
        return available_image_paths[0]

    _ensure_gemini_configured_scenario()
    model = genai.GenerativeModel(GEMINI_VISION_MODEL_NAME) # Vision 모델 사용
    print(f"Gemini Vision 모델 ({GEMINI_VISION_MODEL_NAME}) 로드 완료 (for image recommendation).")

    available_image_filenames = [os.path.basename(p) for p in available_image_paths]
    print(f"  이미지 추천 요청: '{image_description}' 에 맞는 이미지를 파일 목록에서 찾습니다...")
    
    # 텍스트 기반 추천 (정확도 한계 있을 수 있음, 실험 필요)
    try:
        prompt_parts = [
            f"'{product_name}' 상품의 쇼츠 영상의 특정 장면에 대한 설명은 다음과 같습니다: \"{image_description}\"",
            "아래는 사용 가능한 이미지 파일들의 목록입니다. 이 목록에서 위 설명에 가장 잘 어울리는 이미지 파일명을 하나만 정확히 골라서 파일명만 응답해주세요.",
            "만약 적합한 이미지가 없다고 판단되면 \"없음\"이라고 응답해주세요.",
            "사용 가능한 이미지 파일명: " + ", ".join(available_image_filenames)
        ]
        
        # Vision 모델에 텍스트 프롬프트만으로 질문 (이미지 파일 자체를 보내는 것이 더 정확할 수 있음)
        response = model.generate_content(prompt_parts)
        recommended_filename_raw = response.text.strip()

        if recommended_filename_raw != "없음" and recommended_filename_raw in available_image_filenames:
            recommended_filename = recommended_filename_raw
            print(f"  Gemini 추천 이미지 (텍스트 기반): {recommended_filename}")
        else:
            if recommended_filename_raw == "없음":
                print(f"  Gemini가 설명을 바탕으로 적합한 이미지를 찾지 못했습니다 (텍스트 기반).")
            else:
                print(f"  Gemini 이미지 추천 응답이 예상과 다릅니다: '{recommended_filename_raw}'.")
            # fallback
            recommended_filename = os.path.basename(available_image_paths[0]) if available_image_paths else None
            print(f"  Fallback으로 이미지 사용: {recommended_filename}")
        
        if recommended_filename:
            for p in available_image_paths:
                if os.path.basename(p) == recommended_filename:
                    return p
        return available_image_paths[0] if available_image_paths else None # 최종 fallback

    except Exception as e:
        print(f"  이미지 추천 중 오류: {e}. Fallback으로 첫 번째 이미지 사용.")
        return available_image_paths[0] if available_image_paths else None