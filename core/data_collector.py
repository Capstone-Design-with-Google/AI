import requests
from bs4 import BeautifulSoup
import os
import shutil
import time
import re
from urllib.parse import urljoin, unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import uuid

from config import IMAGES_RAW_FOLDER, USER_AGENT, SELENIUM_WAIT_TIMEOUT, IMAGE_DOWNLOAD_TIMEOUT
from utils.file_utils import clear_folder_contents, ensure_folder_exists

def setup_image_collection():
    if os.path.exists(IMAGES_RAW_FOLDER):
        print(f"'{IMAGES_RAW_FOLDER}' 폴더 내용 삭제 중...")
        clear_folder_contents(IMAGES_RAW_FOLDER)
    ensure_folder_exists(IMAGES_RAW_FOLDER)
    print(f"이미지 저장 폴더 준비 완료: {IMAGES_RAW_FOLDER}")

def collect_product_details(target_url):
    product_info = {
        "name": "정보 없음",
        "price": "정보 없음",
        "description_summary": "정보 없음",
        "image_urls": [],
        "downloaded_image_paths": []
    }
    driver = None
    user_data_dir = None

    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f"user-agent={USER_AGENT}")
        user_data_dir = f"/tmp/chrome_user_data_{uuid.uuid4()}"
        options.add_argument(f"--user-data-dir={user_data_dir}")

        # 로컬 환경에서는 webdriver_manager 사용 권장
        # from selenium.webdriver.chrome.service import Service as ChromeService
        # from webdriver_manager.chrome import ChromeDriverManager
        # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver = webdriver.Chrome(options=options) # PATH에 ChromeDriver 설정 가정

        print(f"'{target_url}' 페이지 로딩 시도...")
        driver.get(target_url)
        WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("페이지 로딩 완료.")

        try:
            name_selectors = [
                'div.prod_tit_area h2.tit', 'span.title', 'h1.prod_tit',
                'div.top_info h3.tit', 'div.item_detail_tit h2', '.prd_name > span',
                '#prdInfo > .name > span', 'h2.product_title'
            ]
            name_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ', '.join(name_selectors)))
            )
            product_info["name"] = name_element.text.strip()
        except Exception:
            print(f"상품명 찾기 실패 (CSS Selector). 페이지 title 태그에서 추출 시도.")
            title_tag_text = driver.title
            product_info["name"] = title_tag_text.split('|')[0].split('-')[0].strip() if title_tag_text else "정보 없음"
        print(f"상품명: {product_info['name']}")

        image_urls_temp = []
        detail_container_selectors = [
            "div.edibot-product-detail", "div.product-detail-content",
            "div#prdDetail", "div.detail_cont", "div.product_detail_area"
        ]
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        
        detail_div = None
        for selector in detail_container_selectors:
            detail_div = soup.select_one(selector)
            if detail_div:
                print(f"상세 설명 컨테이너 찾음: '{selector}'")
                break
        
        if detail_div:
            for img in detail_div.find_all('img'):
                src = img.get('ec-data-src') or img.get('src') or img.get('data-src')
                if not src or src.strip().startswith('data:'):
                    continue
                full_url = urljoin(target_url, src.strip())
                if full_url not in image_urls_temp:
                    image_urls_temp.append(full_url)
        else:
            print("지정된 상세 설명 컨테이너를 찾지 못했습니다. 페이지 전체에서 이미지 검색 시도.")
            for img_tag in soup.find_all('img'):
                src = img_tag.get('src') or img_tag.get('data-src')
                if src and not src.startswith('data:'):
                    if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        full_url = urljoin(target_url, src.strip())
                        if full_url not in image_urls_temp:
                            image_urls_temp.append(full_url)
        
        product_info["image_urls"] = list(set(image_urls_temp))
        print(f"수집된 이미지 URL 개수: {len(product_info['image_urls'])}")

    except Exception as e:
        print(f"❌ Selenium 처리 중 예기치 않은 오류 발생: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e_quit:
                print(f"WebDriver 종료 중 오류: {e_quit}")
        if user_data_dir and os.path.exists(user_data_dir):
            try:
                shutil.rmtree(user_data_dir)
            except Exception as e_rm:
                print(f"임시 사용자 데이터 디렉토리 삭제 실패: {user_data_dir}, 오류: {e_rm}")
    return product_info

def download_images_from_urls(image_urls, base_url_for_referer):
    downloaded_image_paths = []
    if not image_urls:
        print("수집된 이미지 URL이 없어 다운로드를 진행하지 않습니다.")
        return downloaded_image_paths

    ensure_folder_exists(IMAGES_RAW_FOLDER)
    print(f"\n--- 이미지 다운로드 시작 (총 {len(image_urls)}개) ---")
    headers_for_download = {'User-Agent': USER_AGENT, 'Referer': base_url_for_referer}
    download_count = 0
    for idx, img_url in enumerate(image_urls, start=1):
        try:
            decoded_img_url = unquote(img_url)
            img_resp = requests.get(decoded_img_url, headers=headers_for_download, stream=True, timeout=IMAGE_DOWNLOAD_TIMEOUT)
            img_resp.raise_for_status()
            content_type = img_resp.headers.get('Content-Type', '').lower()
            ext = '.jpg'
            if 'jpeg' in content_type or 'jpg' in content_type: ext = '.jpg'
            elif 'png' in content_type: ext = '.png'
            elif 'gif' in content_type: ext = '.gif'
            elif 'webp' in content_type: ext = '.webp'
            else:
                url_ext_part = os.path.splitext(decoded_img_url.split('?')[0])[1].lower()
                if url_ext_part in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    ext = url_ext_part
            fname = f"product_image_{str(idx).zfill(3)}{ext}"
            save_path = os.path.join(IMAGES_RAW_FOLDER, fname)
            with open(save_path, 'wb') as f:
                for chunk in img_resp.iter_content(8192): f.write(chunk)
            downloaded_image_paths.append(save_path)
            download_count += 1
            time.sleep(0.05)
        except requests.exceptions.Timeout:
            print(f"    ⚠️ 다운로드 시간 초과: {decoded_img_url}")
        except requests.exceptions.RequestException as e_req:
            print(f"    ⚠️ 다운로드 요청 오류 ({e_req}): {decoded_img_url}")
        except Exception as e_img:
            print(f"    ⚠️ 이미지 처리/저장 중 알 수 없는 오류 ({e_img}): {decoded_img_url}")
    if download_count > 0: print(f"총 {download_count}개의 이미지 다운로드 완료.")
    else: print("다운로드된 이미지가 없습니다.")
    return downloaded_image_paths