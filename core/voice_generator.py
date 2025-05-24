import os
from google.cloud import texttospeech

from config import (GCP_SERVICE_ACCOUNT_KEY_PATH, AUDIO_CLIPS_FOLDER, 
                    TTS_LANGUAGE_CODE, TTS_VOICE_NAME_NEURAL, TTS_SPEAKING_RATE) # TTS_SPEAKING_RATE 추가
from utils.file_utils import ensure_folder_exists, clear_folder_contents

_gcp_credentials_set = False

def set_gcp_credentials():
    global _gcp_credentials_set
    if not os.path.exists(GCP_SERVICE_ACCOUNT_KEY_PATH):
        raise FileNotFoundError(f"GCP 서비스 계정 키 파일을 찾을 수 없습니다: {GCP_SERVICE_ACCOUNT_KEY_PATH}")
    if not _gcp_credentials_set:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_SERVICE_ACCOUNT_KEY_PATH
        _gcp_credentials_set = True
        print(f"GCP 서비스 계정 키 로드 완료: {GCP_SERVICE_ACCOUNT_KEY_PATH}")

def synthesize_text_to_speech(text_to_synthesize, output_filename, scene_number):
    try:
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=text_to_synthesize)
        voice = texttospeech.VoiceSelectionParams(
            language_code=TTS_LANGUAGE_CODE, name=TTS_VOICE_NAME_NEURAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=TTS_SPEAKING_RATE  # 말하기 속도 설정
        )
        print(f"  Synthesizing speech for scene {scene_number} (Rate: {TTS_SPEAKING_RATE}): '{text_to_synthesize[:30]}...'")
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        ensure_folder_exists(AUDIO_CLIPS_FOLDER)
        output_filepath = os.path.join(AUDIO_CLIPS_FOLDER, output_filename)
        with open(output_filepath, "wb") as out:
            out.write(response.audio_content)
            print(f"  Audio content written to file: {output_filepath}")
        return output_filepath
    except Exception as e:
        print(f"Error during TTS for scene {scene_number} ('{text_to_synthesize[:30]}...'): {e}")
        return None

def generate_audio_clips_from_scenario(scenario_data, product_name):
    if not scenario_data:
        print("시나리오 데이터가 없어 음성 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None # 또는 scenario_data 반환
    try:
        set_gcp_credentials()
    except FileNotFoundError as e:
        print(f"음성 생성 중단: {e}")
        return scenario_data # 오류 발생 시 원본 데이터 반환

    print("\n=== 시나리오 기반 음성 클립 생성 시작 ===")
    if os.path.exists(AUDIO_CLIPS_FOLDER): clear_folder_contents(AUDIO_CLIPS_FOLDER)
    ensure_folder_exists(AUDIO_CLIPS_FOLDER)
    
    updated_scenario_data = []
    total_audio_duration = 0

    for scene in scenario_data:
        scene_copy = scene.copy() # 원본 수정을 피하기 위해 복사본 사용
        scene_num = scene_copy.get("scene_number", "unknown")
        narration = scene_copy.get("narration")
        
        if narration:
            safe_product_name = "".join(c if c.isalnum() else "_" for c in product_name[:20])
            output_filename = f"{safe_product_name}_scene_{str(scene_num).zfill(2)}.mp3"
            audio_path = synthesize_text_to_speech(narration, output_filename, scene_num)
            scene_copy["audio_file_path"] = audio_path
            if audio_path:
                try:
                    # 생성된 오디오 파일의 길이를 가져와서 scene_info에 업데이트 (선택적)
                    # 이 부분은 video_editor에서 어차피 다시 로드하므로 필수는 아님
                    from moviepy.editor import AudioFileClip
                    temp_audio_clip = AudioFileClip(audio_path)
                    scene_copy["actual_audio_duration_seconds"] = temp_audio_clip.duration
                    total_audio_duration += temp_audio_clip.duration
                    temp_audio_clip.close()
                except Exception as e_audio_dur:
                    print(f"  Warning: Scene {scene_num} 오디오 길이 측정 실패: {e_audio_dur}")
                    scene_copy["actual_audio_duration_seconds"] = scene_copy.get("duration_seconds") # fallback
        else:
            scene_copy["audio_file_path"] = None
            scene_copy["actual_audio_duration_seconds"] = scene_copy.get("duration_seconds", 0)
            print(f"  Scene {scene_num}: 내레이션이 없어 음성 생성을 건너<0xEB><0x9B><0x84>니다.")
        
        updated_scenario_data.append(scene_copy)

    print(f"음성 클립 생성 완료. 예상 총 오디오 길이 (TTS 기준): {total_audio_duration:.2f} 초")
    return updated_scenario_data