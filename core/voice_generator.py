import os
from google.cloud import texttospeech
# from config import GCP_SERVICE_ACCOUNT_KEY_PATH # 이 import는 주석 처리하거나 삭제 가능
from config import (AUDIO_CLIPS_FOLDER, TTS_LANGUAGE_CODE,
                    TTS_VOICE_NAME_NEURAL, TTS_SPEAKING_RATE)
from utils.file_utils import ensure_folder_exists, clear_folder_contents

# _gcp_credentials_set 변수는 더 이상 필요 없을 수 있습니다.
# 또는 로깅 플래그로 사용할 수 있습니다.
_gcp_auth_logged = False

def check_gcp_authentication():
    """
    Checks if GCP authentication is likely set up (via GOOGLE_APPLICATION_CREDENTIALS)
    and logs information. This function doesn't set the environment variable itself,
    as it's expected to be set by the Codespace's postCreateCommand or a similar mechanism.
    """
    global _gcp_auth_logged
    if not _gcp_auth_logged:
        gcp_auth_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if gcp_auth_env:
            if os.path.exists(gcp_auth_env):
                print(f"GCP Authentication: Using GOOGLE_APPLICATION_CREDENTIALS environment variable pointing to: {gcp_auth_env}")
            else:
                # 이 경우는 postCreateCommand에서 파일 생성에 실패했거나 경로가 잘못된 경우일 수 있습니다.
                print(f"⚠️ GCP Authentication Warning: GOOGLE_APPLICATION_CREDENTIALS is set to '{gcp_auth_env}', but the file does not exist.")
                print("   Please check the postCreateCommand in devcontainer.json and Codespace logs.")
        else:
            print("⚠️ GCP Authentication Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable is NOT set.")
            print("   Google Cloud Text-to-Speech API calls may fail.")
            print("   Ensure 'GCP_CREDENTIALS_SECRET' is set in GitHub Codespaces secrets and devcontainer.json is configured correctly.")
        _gcp_auth_logged = True

def synthesize_text_to_speech(text_to_synthesize, output_filename, scene_number):
    # 함수 호출 시마다 인증 상태를 확인하거나, generate_audio_clips_from_scenario 시작 시 한 번만 호출
    # 여기서는 generate_audio_clips_from_scenario에서 호출한다고 가정하고 생략 가능

    try:
        # TextToSpeechClient는 초기화 시 GOOGLE_APPLICATION_CREDENTIALS를 자동으로 사용합니다.
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
        # 오류 발생 시 인증 문제일 가능성을 로깅에 추가할 수 있습니다.
        gcp_auth_env_val = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        auth_hint = f"(GOOGLE_APPLICATION_CREDENTIALS: {gcp_auth_env_val if gcp_auth_env_val else 'Not set'})"
        print(f"Error during TTS for scene {scene_number} ('{text_to_synthesize[:30]}...'): {e} {auth_hint}")
        return None

def generate_audio_clips_from_scenario(scenario_data, product_name):
    if not scenario_data:
        print("시나리오 데이터가 없어 음성 생성을 건너<0xEB><0x9B><0x84>니다.")
        return scenario_data # 원본 데이터 반환 유지

    # 프로그램 시작 부분 또는 주요 기능 실행 전에 GCP 인증 상태를 한 번 확인합니다.
    check_gcp_authentication()

    # 만약 check_gcp_authentication() 에서 심각한 문제가 감지되면 (예: 환경 변수 없음)
    # 여기서 TTS 시도 없이 바로 리턴하는 로직을 추가할 수도 있습니다.
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("GCP 인증 정보가 없어 음성 클립 생성을 진행할 수 없습니다. 프로세스를 중단합니다.")
        # scene_data에 audio_file_path 등을 None으로 채워서 반환하거나,
        # 오류 플래그를 설정하여 video_editor 등에서 음성 없이 진행하도록 할 수 있습니다.
        # 여기서는 일단 원본 데이터를 반환하고, 로그를 통해 문제를 파악하도록 합니다.
        return scenario_data


    print("\n=== 시나리오 기반 음성 클립 생성 시작 ===")
    if os.path.exists(AUDIO_CLIPS_FOLDER): clear_folder_contents(AUDIO_CLIPS_FOLDER)
    ensure_folder_exists(AUDIO_CLIPS_FOLDER)

    updated_scenario_data = []
    total_audio_duration = 0

    for scene_idx, scene in enumerate(scenario_data): # enumerate 사용 권장
        scene_copy = scene.copy()
        # scene_num = scene_copy.get("scene_number", f"unknown_{scene_idx+1}") # scene_number가 없을 경우 대비
        scene_num = scene_copy.get("scene_number")
        if scene_num is None: # scene_number가 없는 경우를 대비 (JSON 생성 시 scene_number는 필수)
            scene_num = scene_idx + 1
            scene_copy["scene_number"] = scene_num
            print(f"  Warning: Scene {scene_num} (index {scene_idx}) is missing 'scene_number' in input data. Assigning sequential number.")


        narration = scene_copy.get("narration")

        if narration:
            safe_product_name = "".join(c if c.isalnum() else "_" for c in product_name[:20])
            output_filename = f"{safe_product_name}_scene_{str(scene_num).zfill(2)}.mp3"
            audio_path = synthesize_text_to_speech(narration, output_filename, scene_num)
            scene_copy["audio_file_path"] = audio_path
            if audio_path and os.path.exists(audio_path): # audio_path가 None이 아니고, 파일도 실제로 존재하는지 확인
                try:
                    from moviepy.editor import AudioFileClip
                    temp_audio_clip = AudioFileClip(audio_path)
                    scene_copy["actual_audio_duration_seconds"] = temp_audio_clip.duration
                    total_audio_duration += temp_audio_clip.duration
                    temp_audio_clip.close()
                except Exception as e_audio_dur:
                    print(f"  Warning: Scene {scene_num} 오디오 길이 측정 실패 ({audio_path}): {e_audio_dur}")
                    # fallback으로 JSON의 duration_seconds를 사용하거나, 0 또는 다른 기본값을 설정
                    scene_copy["actual_audio_duration_seconds"] = scene_copy.get("duration_seconds", 0)
            else: # audio_path가 None이거나 파일이 없는 경우
                scene_copy["actual_audio_duration_seconds"] = scene_copy.get("duration_seconds", 0)
                if audio_path is None: # synthesize_text_to_speech에서 None이 반환된 경우
                     print(f"  Info: Scene {scene_num} - 음성 파일 생성 실패. 'actual_audio_duration_seconds'는 JSON 값을 따릅니다.")

        else:
            scene_copy["audio_file_path"] = None
            scene_copy["actual_audio_duration_seconds"] = scene_copy.get("duration_seconds", 0)
            print(f"  Scene {scene_num}: 내레이션이 없어 음성 생성을 건너<0xEB><0x9B><0x84>니다.")

        updated_scenario_data.append(scene_copy)

    if total_audio_duration > 0:
        print(f"음성 클립 생성 완료. 생성된 총 오디오 길이 (MoviePy 측정 기준): {total_audio_duration:.2f} 초")
    else:
        print("생성된 음성 클립이 없거나 길이를 측정할 수 없었습니다.")

    return updated_scenario_data