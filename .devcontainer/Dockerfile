# Python 3.11.9 버전을 기준으로 합니다. (멘티님 환경과 동일하게)
# mcr.microsoft.com/devcontainers/python 이미지는 다양한 버전을 제공합니다.
# 예: python:0-3.11 또는 특정 패치 버전이 필요하면 찾아서 명시할 수 있습니다.
# 여기서는 3.11을 기반으로 하고, 실제 패치 버전은 이미지에 따라 달라질 수 있으나 호환됩니다.
FROM mcr.microsoft.com/devcontainers/python:0-3.11

# 작업 환경을 vscode 사용자로 설정 (기본값)
USER vscode

# 시스템 패키지 업데이트 및 설치 (root 권한으로 실행)
# sudo 없이 사용하기 위해 USER vscode 로 실행 전에 root로 설치
USER root
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
    # MoviePy 의존성 (특히 TextClip): ImageMagick
    imagemagick \
    # 한글 폰트 (나눔 폰트)
    fonts-nanum \
    # Selenium ChromeDriver 및 Chrome 브라우저 의존성, jq (JSON 파서)
    curl wget gnupg unzip jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome 최신 안정 버전 설치 (root 권한)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver 설치 (root 권한)
# Chrome 버전에 맞는 ChromeDriver 버전을 설치하는 것이 중요합니다.
# 아래는 최신 버전을 가져오는 예시이지만, 특정 버전을 명시하는 것이 더 안정적일 수 있습니다.
# 예: RUN CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f3 | cut -d '.' -f1,2,3)
# RUN CHROME_DRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION})
# RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip \
# 최신 안정 버전의 크롬드라이버를 사용하는 다른 방법 (버전 유동적)
RUN LATEST_CHROMEDRIVER_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && wget -O /tmp/chromedriver.zip ${LATEST_CHROMEDRIVER_VERSION} \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    # chromedriver-linux64 폴더 안에 chromedriver가 있을 수 있음
    && (mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver || echo "chromedriver not found in subfolder, assuming it is in /usr/local/bin/") \
    && (rm -rf /usr/local/bin/chromedriver-linux64 || echo "chromedriver-linux64 subfolder not found") \
    && rm -rf /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# ImageMagick 보안 정책 수정 (Colab 가이드 참고) - 경로 확인 필요
# RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/g' /etc/ImageMagick-6/policy.xml || \
#     sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/g' /etc/ImageMagick/policy.xml || \
#     echo "ImageMagick policy.xml not found or sed command failed. TextClip MIGHT have issues."
# 우선 주석 처리, TextClip 오류 발생 시 경로 확인 후 주석 해제 및 수정

# 다시 vscode 사용자로 전환
USER vscode
COPY requirements.txt /tmp/requirements.txt

# Python 라이브러리 설치 (프로젝트 루트의 requirements.txt 사용)
# Dockerfile 빌드 시점에 requirements.txt가 컨테이너로 복사됨 (devcontainer.json의 context 설정 덕분)
# COPY requirements.txt /tmp/pip-tmp/ # 이 줄은 context가 ".."이면 필요 없을 수 있음
# RUN pip3 install --upgrade pip \
#    && pip3 --disable-pip-version-check --no-cache-dir install -r requirements.txt
RUN pip3 install --upgrade pip \
    && pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/requirements.txt

# (선택 사항) WebDriver Manager 설치 (Dockerfile에서 미리 설치하면 실행 시점 속도 향상)
RUN pip3 install webdriver-manager

# (선택 사항) black, autopep8 등 코드 포맷터 설치 (devcontainer.json의 formatOnSave와 연동)
RUN pip3 install black autopep8

# Python이 출력을 즉시 버퍼링하지 않도록 설정 (로그 확인 용이)
ENV PYTHONUNBUFFERED 1