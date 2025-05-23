import os
from moviepy.editor import (ImageClip, AudioFileClip, TextClip, CompositeVideoClip,
                            concatenate_videoclips, vfx)
from PIL import Image

from config import (VIDEOS_FOLDER, IMAGES_RAW_FOLDER, DEFAULT_FONT_PATH_WIN,
                    DEFAULT_FONT_PATH_MAC, DEFAULT_FONT_PATH_LINUX,
                    VIDEO_RESOLUTION, VIDEO_FPS)
from utils.file_utils import ensure_folder_exists
from core.scenario_generator import recommend_image_for_scene # 수정된 부분

def get_system_font():
    if os.name == 'nt':
        font_path = DEFAULT_FONT_PATH_WIN
        if not os.path.exists(f"C:/Windows/Fonts/{font_path}"):
            print(f"Warning: 기본 폰트 '{font_path}'를 찾을 수 없습니다. 'NanumGothic'으로 대체 시도.")
            return "NanumGothic"
        return font_path
    elif os.uname().sysname == 'Darwin':
        return DEFAULT_FONT_PATH_MAC
    else:
        if os.path.exists(DEFAULT_FONT_PATH_LINUX):
            return DEFAULT_FONT_PATH_LINUX
        else:
            print(f"Warning: 기본 NanumGothic 폰트 '{DEFAULT_FONT_PATH_LINUX}'를 찾을 수 없습니다. 'NanumGothicBold'로 대체 시도.")
            return "NanumGothicBold"

def create_video_from_scenario(scenario_data_with_audio, product_name, downloaded_image_paths):
    if not scenario_data_with_audio:
        print("시나리오 데이터가 없어 영상 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None
    
    font_path = get_system_font()
    print(f"Using font for subtitles: {font_path}")
    print("\n=== MoviePy 영상 조합 시작 ===")
    ensure_folder_exists(VIDEOS_FOLDER)
    
    scene_clips = []
    available_images = [img_path for img_path in downloaded_image_paths if os.path.exists(img_path)]
    
    placeholder_path_temp = os.path.join(IMAGES_RAW_FOLDER, "placeholder_temp.png")
    if not available_images and not os.path.exists(placeholder_path_temp):
        print("사용 가능한 이미지도 없고 임시 플레이스홀더도 없습니다. 플레이스홀더 생성.")
        try:
            Image.new('RGB', VIDEO_RESOLUTION, color = 'lightgrey').save(placeholder_path_temp)
        except Exception as e_placeholder:
            print(f"플레이스홀더 이미지 생성 실패: {e_placeholder}. 영상 생성 중단.")
            return None
            
    for scene_info in scenario_data_with_audio:
        scene_num = scene_info.get("scene_number", "N/A")
        narration = scene_info.get("narration", "")
        subtitle_text = scene_info.get("subtitle", "")
        audio_file_path = scene_info.get("audio_file_path")
        scene_duration = 0
        audio_clip = None

        if audio_file_path and os.path.exists(audio_file_path):
            try:
                audio_clip = AudioFileClip(audio_file_path)
                scene_duration = audio_clip.duration
            except Exception as e:
                print(f"  Warning: Scene {scene_num} 오디오 파일 로드 실패 ({audio_file_path}): {e}.")
                scene_duration = scene_info.get("duration_seconds", 3)
        else:
            scene_duration = scene_info.get("duration_seconds", 3)
        if scene_duration <= 0: scene_duration = 1
        
        scene_image_description = scene_info.get("recommended_image_description", "")
        selected_image_path = recommend_image_for_scene(
            scene_image_description, available_images, product_name
        )

        if not selected_image_path: # 추천 실패 또는 사용 가능 이미지 없음
            print(f"  Scene {scene_num}: 적합한 이미지를 찾지 못해 플레이스홀더 사용.")
            if not os.path.exists(placeholder_path_temp): # 이중 체크
                 Image.new('RGB', VIDEO_RESOLUTION, color = 'grey').save(placeholder_path_temp)
            selected_image_path = placeholder_path_temp
        
        print(f"  Scene {scene_num}: Using image '{os.path.basename(selected_image_path)}' for '{scene_image_description}'")
        
        try:
            img_clip_raw = ImageClip(selected_image_path).set_duration(scene_duration)
            target_height = VIDEO_RESOLUTION[1]
            img_resized = img_clip_raw.resize(height=target_height)
            if img_resized.w >= VIDEO_RESOLUTION[0]:
                img_clip = img_resized.fx(vfx.crop, x_center=img_resized.w/2, width=VIDEO_RESOLUTION[0], height=target_height)
            else:
                scale_factor = VIDEO_RESOLUTION[0] / img_resized.w
                img_clip = img_resized.resize(scale_factor).fx(vfx.crop, x_center=img_resized.w/2, y_center=img_resized.h/2, width=VIDEO_RESOLUTION[0], height=target_height)
        except Exception as e:
            print(f"  Error creating image clip for Scene {scene_num} ({selected_image_path}): {e}. Using placeholder.")
            if not os.path.exists(placeholder_path_temp): Image.new('RGB', VIDEO_RESOLUTION, color = 'grey').save(placeholder_path_temp) # 재확인
            img_clip = ImageClip(placeholder_path_temp).set_duration(scene_duration).resize(VIDEO_RESOLUTION)

        txt_clip = None
        if subtitle_text:
            try:
                txt_clip = TextClip(subtitle_text, fontsize=50, color='white', font=font_path,
                                    stroke_color='black', stroke_width=2, method='caption', size=(VIDEO_RESOLUTION[0]*0.9, None))
                txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(scene_duration)
            except Exception as e:
                print(f"  Error creating text clip for Scene {scene_num} ('{subtitle_text}'): {e}")
        
        compositing_list = [img_clip]
        if txt_clip: compositing_list.append(txt_clip)
        scene_video_clip = CompositeVideoClip(compositing_list, size=VIDEO_RESOLUTION)
        if audio_clip: scene_video_clip = scene_video_clip.set_audio(audio_clip)
        scene_clips.append(scene_video_clip)

    if not scene_clips:
        print("생성된 씬 클립이 없어 영상을 만들 수 없습니다.")
        return None

    final_clip = concatenate_videoclips(scene_clips, method="compose")
    safe_product_name = "".join(c if c.isalnum() else "_" for c in product_name[:30])
    output_video_filename = f"{safe_product_name}_shorts_video.mp4"
    output_video_path = os.path.join(VIDEOS_FOLDER, output_video_filename)
    
    try:
        print(f"\n최종 영상 저장 중... ({output_video_path})")
        final_clip.write_videofile(output_video_path, fps=VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium")
        print(f"🎉 최종 영상 저장 완료: {output_video_path}")
        return output_video_path
    except Exception as e:
        print(f"최종 영상 저장 중 오류 발생: {e}")
        return None
    finally:
        if 'final_clip' in locals(): final_clip.close()
        for sc_idx, sc in enumerate(scene_clips):
            try: sc.close()
            except Exception: pass # 이미 닫혔을 수 있음
        # 명시적으로 audio_clip도 닫아주는 것이 좋을 수 있습니다.
        # if audio_clip and hasattr(audio_clip, 'close'): audio_clip.close()