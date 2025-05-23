import os
import shutil

def clear_folder_contents(folder_path):
    if not os.path.exists(folder_path):
        print(f"'{folder_path}' 폴더가 존재하지 않아 삭제할 내용이 없습니다.")
        return
    try:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        print(f"'{folder_path}' 폴더의 내용물을 모두 삭제했습니다.")
    except Exception as e:
        print(f"'{folder_path}' 폴더 내용물 삭제 중 오류 발생: {e}")

def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        print(f"'{folder_path}' 폴더를 생성했습니다.")

def save_text_to_file(text_content, file_path):
    try:
        ensure_folder_exists(os.path.dirname(file_path))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        print(f"텍스트를 파일로 저장했습니다: {file_path}")
    except Exception as e:
        print(f"텍스트 파일 저장 중 오류 발생 ({file_path}): {e}")