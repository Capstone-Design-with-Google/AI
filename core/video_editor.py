import os
from moviepy.editor import (ImageClip, AudioFileClip, TextClip, CompositeVideoClip,
                            concatenate_videoclips, vfx)
from PIL import Image

# config.py에서 변수들을 가져옵니다.
# DEFAULT_FONT_PATH_WIN은 이제 'malgun.ttf'와 같은 파일명을 의미하게 됩니다.
from config import (VIDEOS_FOLDER, IMAGES_RAW_FOLDER, DEFAULT_FONT_PATH_WIN,
                    DEFAULT_FONT_PATH_MAC, DEFAULT_FONT_PATH_LINUX,
                    VIDEO_RESOLUTION, VIDEO_FPS)
from utils.file_utils import ensure_folder_exists
# scenario_generator에서 이미지 추천 함수를 가져옵니다.
from core.scenario_generator import recommend_image_for_scene

# --- ImageMagick 경로 설정 (파일 상단에 위치) ---
imagemagick_binary_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe" # 멘티님 실제 경로로!

if os.path.isfile(imagemagick_binary_path):
    os.environ["IMAGEMAGICK_BINARY"] = imagemagick_binary_path
    print(f"ImageMagick 바이너리 경로 설정됨: {imagemagick_binary_path}")
else:
    print(f"Warning: ImageMagick 바이너리 파일을 찾을 수 없습니다: {imagemagick_binary_path}")
    print("자막 생성에 문제가 발생할 수 있습니다. ImageMagick을 설치하고 경로를 정확히 지정해주세요.")

# --- 수정된 get_system_font 함수 (한글 자막에 집중) ---
def get_system_font():
    if os.name == 'nt': # Windows
        # 1순위: 나눔고딕 (별도 설치 필요, 한글 지원 우수)
        # 시스템에 NanumGothicBold.ttf 또는 NanumGothic.ttf 가 설치되어 있고,
        # 아래 경로가 실제 파일 경로와 일치해야 합니다.
        nanum_gothic_bold_path = r"C:/Windows/Fonts/NanumGothicBold.ttf"
        if os.path.exists(nanum_gothic_bold_path):
            print(f"Using font: {nanum_gothic_bold_path} (NanumGothic Bold)")
            return nanum_gothic_bold_path
        
        nanum_gothic_path = r"C:/Windows/Fonts/NanumGothic.ttf"
        if os.path.exists(nanum_gothic_path):
            print(f"Using font: {nanum_gothic_path} (NanumGothic)")
            return nanum_gothic_path

        # 2순위: 맑은 고딕 (Windows 기본 한글 폰트) - 전체 경로 반환
        # config.py의 DEFAULT_FONT_PATH_WIN에 "malgun.ttf"가 설정되어 있다고 가정
        default_font_filename = DEFAULT_FONT_PATH_WIN
        system_fonts_dir = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts")
        malgun_gothic_full_path = os.path.join(system_fonts_dir, default_font_filename)
        if os.path.exists(malgun_gothic_full_path):
            print(f"Using font: {malgun_gothic_full_path} (Malgun Gothic - System Default)")
            return malgun_gothic_full_path
        
        # 3순위: 폰트 이름으로 시도 (MoviePy/ImageMagick이 시스템에서 찾도록)
        # 이 경우, 시스템에 "Malgun Gothic" 또는 "NanumGothic" 이름으로 폰트가 등록되어 있어야 함.
        # DEFAULT_FONT_PATH_WIN이 "malgun.ttf"라면 "Malgun Gothic"으로 시도
        font_name_to_try = "Malgun Gothic" # 또는 "NanumGothic" 등
        print(f"Warning: 지정된 폰트 파일들을 찾을 수 없습니다. '{font_name_to_try}' 이름으로 시스템 폰트 사용 시도.")
        return font_name_to_try

    elif hasattr(os, 'uname') and os.uname().sysname == 'Darwin': # macOS
        if os.path.exists(DEFAULT_FONT_PATH_MAC):
            print(f"Using font: {DEFAULT_FONT_PATH_MAC} (macOS Default)")
            return DEFAULT_FONT_PATH_MAC
        else:
            print(f"Warning: macOS 기본 폰트 '{DEFAULT_FONT_PATH_MAC}'를 찾을 수 없습니다. 'AppleGothic' 이름으로 시도.")
            return "AppleGothic" # 시스템에 등록된 폰트 이름

    else: # Linux
        if os.path.exists(DEFAULT_FONT_PATH_LINUX):
            print(f"Using font: {DEFAULT_FONT_PATH_LINUX} (Linux Default)")
            return DEFAULT_FONT_PATH_LINUX
        else:
            print(f"Warning: Linux 기본 폰트 '{DEFAULT_FONT_PATH_LINUX}'를 찾을 수 없습니다. 'NanumGothicBold' 이름으로 시도.")
            return "NanumGothicBold" # 시스템에 등록된 폰트 이름


# --- create_video_from_scenario 함수 (font_path 변수명만 font_for_subtitle로 변경) ---
def create_video_from_scenario(scenario_data_with_audio, product_name, downloaded_image_paths):
    if not scenario_data_with_audio:
        print("시나리오 데이터가 없어 영상 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None
    
    font_for_subtitle = get_system_font() # 수정된 함수 호출
    print(f"자막 생성에 사용될 폰트: {font_for_subtitle}") # 최종 사용될 폰트 확인 로그

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

        if not selected_image_path: 
            print(f"  Scene {scene_num}: 적합한 이미지를 찾지 못해 플레이스홀더 사용.")
            if not os.path.exists(placeholder_path_temp): 
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
            if not os.path.exists(placeholder_path_temp): Image.new('RGB', VIDEO_RESOLUTION, color = 'grey').save(placeholder_path_temp)
            img_clip = ImageClip(placeholder_path_temp).set_duration(scene_duration).resize(VIDEO_RESOLUTION)

        txt_clip = None
        if subtitle_text:
            try:
                # TextClip 생성 시 font_for_subtitle 변수 사용
                txt_clip = TextClip(subtitle_text, fontsize=50, color='white', font=font_for_subtitle,
                                    stroke_color='black', stroke_width=2, method='caption', size=(VIDEO_RESOLUTION[0]*0.9, None))
                txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(scene_duration)
            except Exception as e:
                print(f"  Error creating text clip for Scene {scene_num} ('{subtitle_text}') using font '{font_for_subtitle}': {e}")
        
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
        if 'final_clip' in locals() and final_clip: final_clip.close()
        for sc_idx, sc in enumerate(scene_clips):
            try:
                if sc: sc.close()
            except Exception: pass
        if audio_clip and hasattr(audio_clip, 'close'): audio_clip.close()