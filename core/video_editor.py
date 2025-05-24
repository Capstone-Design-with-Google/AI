import os
import numpy as np # NumPy import 추가
from moviepy.editor import (ImageClip, AudioFileClip, TextClip, CompositeVideoClip,
                            concatenate_videoclips, vfx)
from PIL import Image, ImageOps

from config import (VIDEOS_FOLDER, IMAGES_RAW_FOLDER, DEFAULT_FONT_PATH_WIN,
                    DEFAULT_FONT_PATH_MAC, DEFAULT_FONT_PATH_LINUX,
                    VIDEO_RESOLUTION, VIDEO_FPS)
from utils.file_utils import ensure_folder_exists
from core.scenario_generator import recommend_image_for_scene

# (ImageMagick 경로 설정 및 get_system_font 함수는 이전과 동일하게 유지)
# --- ImageMagick 경로 설정 (파일 상단에 위치) ---
imagemagick_binary_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe" 

if os.path.isfile(imagemagick_binary_path):
    if "IMAGEMAGICK_BINARY" not in os.environ:
         os.environ["IMAGEMAGICK_BINARY"] = imagemagick_binary_path
    print(f"ImageMagick 바이너리 경로 확인/설정됨: {os.environ.get('IMAGEMAGICK_BINARY')}")
else:
    print(f"Warning: ImageMagick 바이너리 파일을 찾을 수 없습니다: {imagemagick_binary_path}")
    print("자막 생성에 문제가 발생할 수 있습니다. ImageMagick을 설치하고 경로를 정확히 지정하거나, 시스템 PATH에 추가해주세요.")

def get_system_font():
    if os.name == 'nt': 
        nanum_gothic_bold_path = r"C:/Windows/Fonts/NanumGothicBold.ttf"
        if os.path.exists(nanum_gothic_bold_path):
            print(f"Using font: {nanum_gothic_bold_path} (NanumGothic Bold)")
            return nanum_gothic_bold_path
        
        nanum_gothic_path = r"C:/Windows/Fonts/NanumGothic.ttf"
        if os.path.exists(nanum_gothic_path):
            print(f"Using font: {nanum_gothic_path} (NanumGothic)")
            return nanum_gothic_path

        default_font_filename = DEFAULT_FONT_PATH_WIN 
        system_fonts_dir = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts")
        
        specific_font_path = os.path.join(system_fonts_dir, default_font_filename)
        if os.path.exists(specific_font_path):
            print(f"Using font: {specific_font_path} (From config: {default_font_filename})")
            return specific_font_path
        
        font_name_to_try = default_font_filename.split('.')[0] 
        if "NanumGothicBold" in font_name_to_try: font_name_to_try = "NanumGothic Bold"
        elif "malgun" in font_name_to_try.lower(): font_name_to_try = "Malgun Gothic"

        print(f"Warning: 지정된 폰트 파일({specific_font_path})을 찾을 수 없습니다. '{font_name_to_try}' 이름으로 시스템 폰트 사용 시도.")
        return font_name_to_try

    elif hasattr(os, 'uname') and os.uname().sysname == 'Darwin': 
        if os.path.exists(DEFAULT_FONT_PATH_MAC):
            print(f"Using font: {DEFAULT_FONT_PATH_MAC} (macOS Default)")
            return DEFAULT_FONT_PATH_MAC
        else:
            print(f"Warning: macOS 기본 폰트 '{DEFAULT_FONT_PATH_MAC}'를 찾을 수 없습니다. 'AppleGothic' 이름으로 시도.")
            return "AppleGothic" 

    else: 
        if os.path.exists(DEFAULT_FONT_PATH_LINUX):
            print(f"Using font: {DEFAULT_FONT_PATH_LINUX} (Linux Default)")
            return DEFAULT_FONT_PATH_LINUX
        else:
            print(f"Warning: Linux 기본 폰트 '{DEFAULT_FONT_PATH_LINUX}'를 찾을 수 없습니다. 'NanumGothic' 이름으로 시도.")
            return "NanumGothic"


def create_video_from_scenario(scenario_data_with_audio, product_name, downloaded_image_paths):
    if not scenario_data_with_audio:
        print("시나리오 데이터가 없어 영상 생성을 건너<0xEB><0x9B><0x84>니다.")
        return None
    
    font_for_subtitle = get_system_font()
    print(f"자막 생성에 사용될 폰트: {font_for_subtitle}")

    print("\n=== MoviePy 영상 조합 시작 ===")
    ensure_folder_exists(VIDEOS_FOLDER)
    
    scene_clips = []
    available_images = [img_path for img_path in downloaded_image_paths if os.path.exists(img_path)]
    
    placeholder_path_temp = os.path.join(IMAGES_RAW_FOLDER, "placeholder_temp.png")
    if not available_images:
        print("사용 가능한 이미지가 없습니다. 플레이스홀더 이미지를 사용합니다.")
        if not os.path.exists(placeholder_path_temp):
            try:
                Image.new('RGB', VIDEO_RESOLUTION, color='lightgrey').save(placeholder_path_temp)
            except Exception as e_placeholder:
                print(f"플레이스홀더 이미지 생성 실패: {e_placeholder}.")

    total_video_duration_calculated = 0

    for scene_info in scenario_data_with_audio:
        scene_num = scene_info.get("scene_number", "N/A")
        narration = scene_info.get("narration", "")
        subtitle_text = scene_info.get("subtitle", "")
        audio_file_path = scene_info.get("audio_file_path")
        
        scene_duration = 0
        audio_clip_moviepy = None

        if audio_file_path and os.path.exists(audio_file_path):
            try:
                audio_clip_moviepy = AudioFileClip(audio_file_path)
                scene_duration = audio_clip_moviepy.duration
                if "actual_audio_duration_seconds" in scene_info and scene_info["actual_audio_duration_seconds"] > 0:
                    scene_duration = scene_info["actual_audio_duration_seconds"]
                
                json_duration = scene_info.get("duration_seconds", scene_duration)
                if abs(scene_duration - json_duration) > 1.5 : 
                    print(f"  Warning: Scene {scene_num} - 실제 오디오 길이({scene_duration:.2f}s)와 JSON 명시 길이({json_duration}s) 차이 발생.")

            except Exception as e:
                print(f"  Warning: Scene {scene_num} 오디오 파일 로드 실패 ({audio_file_path}): {e}.")
                scene_duration = scene_info.get("duration_seconds", 3)
        else:
            print(f"  Scene {scene_num}: 오디오 파일 경로가 없거나 파일이 존재하지 않음. JSON의 duration_seconds 사용.")
            scene_duration = scene_info.get("duration_seconds", 3) 
        
        if scene_duration <= 0.1: 
            print(f"  Warning: Scene {scene_num}의 유효한 재생 시간이 너무 짧습니다({scene_duration:.2f}s). 0.5초로 강제 설정.")
            scene_duration = 0.5
        
        total_video_duration_calculated += scene_duration

        scene_image_description = scene_info.get("recommended_image_description", "")
        selected_image_path = recommend_image_for_scene(
            scene_description=scene_image_description,
            scene_narration=narration,
            scene_subtitle=subtitle_text,
            available_image_paths=available_images,
            product_name=product_name,
            scene_number=str(scene_num) 
        )

        if not selected_image_path or not os.path.exists(selected_image_path):
            print(f"  Scene {scene_num}: 적합한 이미지 찾지 못함/경로 유효하지 않음. 플레이스홀더 사용.")
            if not os.path.exists(placeholder_path_temp):
                 Image.new('RGB', VIDEO_RESOLUTION, color='grey').save(placeholder_path_temp)
            selected_image_path = placeholder_path_temp
        
        print(f"  Scene {scene_num}: 최종 선택 이미지 '{os.path.basename(selected_image_path)}', 길이: {scene_duration:.2f}s")
        
        try:
            pil_image = Image.open(selected_image_path)
            pil_image = pil_image.convert("RGB") 

            resized_pil_image = ImageOps.pad(pil_image, VIDEO_RESOLUTION, method=Image.Resampling.LANCZOS, color=(0,0,0))
            
            numpy_image = np.array(resized_pil_image) # PIL 이미지를 NumPy 배열로 변환
            img_clip = ImageClip(numpy_image)        # NumPy 배열을 ImageClip에 전달
            img_clip = img_clip.set_duration(scene_duration)

        except Exception as e:
            print(f"  Error creating image clip for Scene {scene_num} ({selected_image_path}): {e}. Using placeholder.")
            if not os.path.exists(placeholder_path_temp): Image.new('RGB', VIDEO_RESOLUTION, color='darkgrey').save(placeholder_path_temp)
            
            pil_placeholder = Image.open(placeholder_path_temp).convert("RGB")
            resized_placeholder = ImageOps.pad(pil_placeholder, VIDEO_RESOLUTION, method=Image.Resampling.LANCZOS, color=(0,0,0))
            
            numpy_placeholder = np.array(resized_placeholder) # PIL 이미지를 NumPy 배열로 변환
            img_clip = ImageClip(numpy_placeholder).set_duration(scene_duration) # NumPy 배열을 ImageClip에 전달


        txt_clip = None
        if subtitle_text:
            try:
                txt_clip = TextClip(subtitle_text, fontsize=50, color='white', font=font_for_subtitle,
                                    stroke_color='black', stroke_width=2.5, method='caption', 
                                    size=(VIDEO_RESOLUTION[0]*0.9, None), align='South', kerning=-1)
                txt_clip = txt_clip.set_position(('center', VIDEO_RESOLUTION[1] * 0.8)).set_duration(scene_duration)
            except Exception as e:
                print(f"  Error creating text clip for Scene {scene_num} ('{subtitle_text}') using font '{font_for_subtitle}': {e}")
        
        compositing_list = [img_clip]
        if txt_clip: compositing_list.append(txt_clip)
        
        scene_video_clip = CompositeVideoClip(compositing_list, size=VIDEO_RESOLUTION, bg_color=(0,0,0))
        if audio_clip_moviepy: 
            scene_video_clip = scene_video_clip.set_audio(audio_clip_moviepy)
        
        scene_clips.append(scene_video_clip)

    if not scene_clips:
        print("생성된 씬 클립이 없어 영상을 만들 수 없습니다.")
        if os.path.exists(placeholder_path_temp):
            try: os.remove(placeholder_path_temp)
            except: pass
        return None

    final_clip = concatenate_videoclips(scene_clips, method="compose")
    
    print(f"\n조합된 영상의 총 길이 (씬 기반 계산): {total_video_duration_calculated:.2f} 초")
    print(f"MoviePy 최종 클립 길이: {final_clip.duration:.2f} 초")

    MAX_VIDEO_LENGTH = 55 
    if final_clip.duration > MAX_VIDEO_LENGTH:
        print(f"⚠️ 경고: 최종 영상 길이({final_clip.duration:.2f}초)가 목표({MAX_VIDEO_LENGTH}초)를 초과했습니다.")
    
    safe_product_name = "".join(c if c.isalnum() else "_" for c in product_name[:30])
    output_video_filename = f"{safe_product_name}_shorts_video.mp4"
    output_video_path = os.path.join(VIDEOS_FOLDER, output_video_filename)
    
    try:
        print(f"\n최종 영상 저장 중... ({output_video_path})")
        final_clip.write_videofile(output_video_path, 
                                   fps=VIDEO_FPS, 
                                   codec="libx264", 
                                   audio_codec="aac", 
                                   threads=os.cpu_count(), 
                                   preset="medium",
                                   ffmpeg_params=['-crf', '23']
                                  )
        print(f"🎉 최종 영상 저장 완료: {output_video_path}")
        return output_video_path
    except Exception as e:
        print(f"최종 영상 저장 중 오류 발생: {e}")
        return None
    finally:
        # 리소스 해제 (이전과 동일)
        if 'final_clip' in locals() and final_clip: final_clip.close()
        for sc in scene_clips:
            if sc: 
                if hasattr(sc, 'close'): sc.close()
        if os.path.exists(placeholder_path_temp):
            try: os.remove(placeholder_path_temp)
            except: pass