import os
import re
import json
import google.generativeai as genai
from PIL import Image

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

def generate_initial_narration(product_name, ocr_texts):
    # (이전과 동일)
    _ensure_gemini_configured_scenario()
    model = genai.GenerativeModel(GEMINI_TEXT_MODEL_NAME)
    print(f"Gemini Text 모델 ({GEMINI_TEXT_MODEL_NAME}) 로드 완료 (for initial narration).")

    if not ocr_texts:
        print("OCR 텍스트가 없어 초기 나레이션 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None
    
    # OCR 텍스트에서 광고성/불필요 정보 일부 필터링 시도 (정교한 필터링은 어려움)
    filtered_ocr_texts = []
    ignore_keywords = ["배송", "택배", "반품", "교환", "고객센터", "주문내역", "결제", "영업일", "주의사항"]
    for text_block in ocr_texts:
        if not any(keyword in text_block for keyword in ignore_keywords):
            # 추가적으로, 너무 긴 숫자 시퀀스 (예: 사업자번호, 전화번호 패턴 등)도 제외 고려 가능
            if not re.search(r'\d{5,}', text_block): # 5자리 이상 연속된 숫자 제외 (간단한 예시)
                 filtered_ocr_texts.append(text_block)
    
    combined_ocr_texts = "\n".join(filtered_ocr_texts if filtered_ocr_texts else ocr_texts) # 필터링된게 없으면 원본 사용

    prompt_for_initial_narration = f"""
    당신은 창의적인 쇼츠 영상 광고 카피라이터입니다.
    다음은 '{product_name}' 상품의 상세 페이지 이미지들에서 추출된 텍스트 정보입니다.
    이 정보를 바탕으로, 사람들이 흥미를 느끼고 구매욕구를 자극할 만한,
    쇼츠 영상용 **전체 나레이션 스크립트**를 작성해주세요.
    **영상 총 길이는 40초에서 50초 사이를 목표로 합니다.** 이 길이에 맞춰 나레이션 분량을 조절해주세요.

    요청사항:
    - 광고 느낌보다는 실제 사용자가 추천하는 듯한 친근하고 자연스러운 어투를 사용해주세요.
    - 상품의 핵심적인 장점과 특징(예: 맛, 사용법, 특별한 재료)을 명확하고 간결하게 강조해주세요.
    - 배송 정보, 반품 규정, 회사 연락처, 결제 방법 등과 같은 부가적인 정보는 제외하고, 상품 자체의 매력에 집중해주세요.
    - 시청자의 궁금증을 유발하고, 다음 내용을 기대하게 만드는 흐름으로 구성해주세요.
    - 만약 추출된 텍스트 정보가 부족하거나 의미가 불분명한 부분이 있다면, 그 부분은 제외하거나 일반적인 긍정적 표현으로 대체해주세요.
    - 결과는 나레이션 텍스트만 응답해주세요. 다른 설명이나 제목은 필요 없습니다.

    추출된 텍스트 (일부 필터링됨):
    ---
    {combined_ocr_texts[:2500]} 
    ---
    생성할 전체 나레이션 스크립트 (40-50초 분량 목표):
    """
    print("\n=== Gemini API로 초기 전체 나레이션 생성 요청 (40-50초 목표) ===")
    # (이하 동일)
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
    **최종 영상의 총 길이는 반드시 40초에서 50초 사이가 되도록 각 씬의 'duration_seconds' 합계를 조절해주세요.**

    전체 나레이션 스크립트:
    ---
    {initial_narration}
    ---

    요구 사항:
    - 각 씬의 'narration' 필드에는 위 전체 나레이션 스크립트의 내용을 적절히 분배하거나, 해당 씬의 핵심 내용을 담도록 해주세요. 전체 나레이션의 흐름을 따라야 합니다.
    - 'recommended_image_description' 필드에는 해당 씬의 나레이션과 어울리는 이미지에 대한 간결하고 명확한 설명을 한국어로 작성해주세요.
        - 예: "맛있게 조리된 상품 클로즈업", "제품을 사용하는 만족스러운 표정의 사용자", "신선한 재료들이 보기 좋게 놓여있는 모습"
        - 상품의 매력을 보여주는 시각적인 장면에 대한 설명을 부탁합니다.
    - 'subtitle' 필드에는 해당 씬의 나레이션 핵심 내용을 강조하거나 시청자의 흥미를 끄는 짧은 문구(자막용)를 한국어로 작성해주세요.
    - 'duration_seconds' 필드에는 해당 씬의 나레이션 분량과 이미지 전환 속도를 고려하여 적절한 예상 시간(초 단위 숫자)을 지정해주세요. **모든 씬의 duration_seconds 합계가 40초에서 50초 사이가 되도록 신중하게 배분해주세요.**
    - 결과는 반드시 아래 명시된 JSON 리스트 형식으로만 응답해주세요. 다른 설명은 일절 추가하지 마세요.

    출력 JSON 형식 예시:
    [
      {{"scene_number": 1, "recommended_image_description": "밝은 배경의 상품 전체 모습", "narration": "(초기 나레이션의 첫 부분 내용)", "subtitle": "✨ 드디어 공개! ✨", "duration_seconds": 5}},
      {{"scene_number": 2, "recommended_image_description": "상품의 특정 기능 사용 모습 클로즈업", "narration": "(초기 나레이션의 중간 부분 내용)", "subtitle": "이 놀라운 기능, 실화? 🤩", "duration_seconds": 7}}
    ]
    위 형식에 맞춰 씬별 스크립트를 생성해주세요. (총 길이 40-50초 엄수)
    """
    print("\n=== Gemini API로 씬별 JSON 스크립트 생성 요청 (총 40-50초 목표) ===")
    # (이하 JSON 파싱 로직 동일)
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
        
        total_duration_from_json = 0
        for i, scene in enumerate(scene_script_data):
            if "scene_number" not in scene: scene["scene_number"] = i + 1
            total_duration_from_json += scene.get("duration_seconds", 0)
        
        print(f"--- 생성된 씬별 스크립트 (JSON 파싱 성공) ---")
        print(f"JSON에 명시된 총 예상 길이: {total_duration_from_json} 초")
        if not (40 <= total_duration_from_json <= 55): # 50초 살짝 넘는 것까진 허용
             print(f"⚠️ 경고: JSON 스크립트의 총 길이가 목표(40-50초)를 벗어났습니다: {total_duration_from_json}초. 프롬프트 조정 또는 후처리 필요 가능성.")

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


def recommend_image_for_scene(scene_description, scene_narration, scene_subtitle, available_image_paths, product_name="", scene_number="N/A"):
    if not available_image_paths:
        print(f"  [Scene {scene_number} Image Recommender] 사용 가능한 이미지가 없습니다.")
        return None
    if not scene_description and not scene_narration and not scene_subtitle:
        print(f"  [Scene {scene_number} Image Recommender] 씬 정보(설명, 나레이션, 자막)가 없어 첫 번째 이미지를 사용합니다.")
        return available_image_paths[0]

    _ensure_gemini_configured_scenario()
    model = genai.GenerativeModel(GEMINI_VISION_MODEL_NAME)
    print(f"  [Scene {scene_number} Image Recommender] Gemini Vision 모델 ({GEMINI_VISION_MODEL_NAME}) 로드 완료.")

    prompt_parts = [
        f"'{product_name}' 상품의 쇼츠 영상의 한 장면(Scene {scene_number})에 사용할 이미지를 추천해야 합니다.\n",
        "이 장면에 대한 정보는 다음과 같습니다:\n"
        f"- 추천 이미지 설명: \"{scene_description}\"\n"
        f"- 장면 나레이션: \"{scene_narration}\"\n"
        f"- 장면 자막: \"{scene_subtitle}\"\n\n",
        "아래에 여러 장의 이미지가 파일명과 함께 제공됩니다. 이 이미지들의 내용을 주의 깊게 살펴보고, ",
        "위에 제공된 장면 정보와 가장 잘 어울린다고 생각되는 이미지 **단 하나**의 **정확한 파일명(예: product_image_001.jpg)**만 응답으로 작성해주세요.\n",
        "**중요 지침:**\n",
        "1. 이미지 내에 글자가 너무 많거나, 복잡한 표, 상세 스펙 설명 위주의 이미지는 피해주세요.\n",
        "2. 상품 자체의 모습, 사용 예시, 먹음직스러운 음식 사진, 제품의 특징을 잘 보여주는 시각적 이미지를 선호합니다.\n",
        "3. 배송 정보, 반품 정책, 회사 연락처, 고객센터 안내, 결제창 스크린샷 등 광고의 부가 정보 이미지는 선택하지 마세요.\n",
        "4. 단순히 글자만 많은 이미지보다는, 장면의 내용과 시각적으로 가장 관련성이 높은 이미지를 선택해야 합니다.\n\n",
        "다른 부연 설명이나 문장은 절대 추가하지 마세요. 오직 파일명만 응답해야 합니다.\n",
        "만약 어떤 이미지도 위 지침에 따라 적합하지 않다고 판단되면 \"없음\"이라고 정확히 응답해주세요.\n\n",
        "--- 사용 가능한 이미지 목록 시작 ---"
    ]
    # (이하 이미지 로드 및 프롬프트 구성, API 호출 로직은 이전과 유사하게 유지)
    loaded_images_info = []
    for img_path in available_image_paths:
        try:
            img = Image.open(img_path)
            filename = os.path.basename(img_path)
            loaded_images_info.append((img, filename))
        except Exception as e:
            print(f"    ⚠️ [Scene {scene_number} Image Recommender] 이미지 로드 실패: {img_path}, 오류: {e}")
            continue
    
    if not loaded_images_info:
        print(f"  [Scene {scene_number} Image Recommender] 로드 가능한 이미지가 없습니다.")
        return available_image_paths[0] if available_image_paths else None

    MAX_IMAGES_PER_REQUEST = 10 
    current_images_to_send_info = loaded_images_info[:MAX_IMAGES_PER_REQUEST]

    for i, (img, filename) in enumerate(current_images_to_send_info):
        prompt_parts.append(f"\n이미지 {i+1} 파일명: {filename}")
        prompt_parts.append(img) 
    
    prompt_parts.append("\n--- 사용 가능한 이미지 목록 끝 ---")
    prompt_parts.append("\n\n가장 적합한 이미지의 파일명 (위 지침을 반드시 따르세요): ")

    print(f"  [Scene {scene_number} Image Recommender] Gemini Vision API로 이미지 추천 요청 중 ({len(current_images_to_send_info)}개 이미지 분석)...")
    
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.2 # 좀 더 결정적인 답변 유도
        )
        response = model.generate_content(prompt_parts, generation_config=generation_config)
        
        recommended_filename_raw = response.text.strip()
        print(f"  [Scene {scene_number} Image Recommender] Gemini 응답: '{recommended_filename_raw}'")

        if recommended_filename_raw == "없음":
            print(f"  [Scene {scene_number} Image Recommender] Gemini가 적합한 이미지를 찾지 못했습니다 (응답: '없음').")
            return available_image_paths[0] if available_image_paths else None
        
        found_image_path = None
        for img_path in available_image_paths:
            if os.path.basename(img_path) == recommended_filename_raw:
                found_image_path = img_path
                break
        
        if found_image_path:
            print(f"  [Scene {scene_number} Image Recommender] Gemini 추천 이미지: {os.path.basename(found_image_path)}")
            return found_image_path
        else:
            print(f"  ⚠️ [Scene {scene_number} Image Recommender] Gemini가 추천한 파일명 '{recommended_filename_raw}'이(가) 사용 가능한 이미지 목록에 없습니다. Fallback 사용.")
            return available_image_paths[0] if available_image_paths else None

    except Exception as e:
        print(f"  🛑 [Scene {scene_number} Image Recommender] 이미지 추천 중 오류 발생: {e}")
        # 프롬프트에서 이미지 객체 제외하고 출력 (디버깅용)
        text_prompt_for_debug = [str(p) for p in prompt_parts if not isinstance(p, Image.Image)]
        print(f"     Gemini 요청 프롬프트 일부 (이미지 제외): {' '.join(text_prompt_for_debug)[:500]}")
        return available_image_paths[0] if available_image_paths else None