import os

base_dir = "c:\\Users\\User\\Desktop\\shoppable_ai"
output_file = "all_files_dump.txt"

with open(output_file, "w", encoding="utf-8") as out:
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            out.write(f"\n--- {file_path} ---\n")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    out.write(f.read())
            except Exception as e:
                out.write(f"[읽기 불가: {e}]\n")