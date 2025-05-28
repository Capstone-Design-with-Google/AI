# Python 3.11.9 버전을 기준으로 합니다.
FROM mcr.microsoft.com/devcontainers/python:0-3.11

# 시스템 패키지 업데이트 및 설치 (root 권한으로 실행)
USER root
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
    imagemagick \
    fonts-nanum \
    curl wget gnupg unzip jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome 최신 안정 버전 설치
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver 설치
RUN LATEST_CHROMEDRIVER_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && wget -O /tmp/chromedriver.zip ${LATEST_CHROMEDRIVER_VERSION} \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && (mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver || echo "chromedriver not found in subfolder, assuming it is in /usr/local/bin/") \
    && (rm -rf /usr/local/bin/chromedriver-linux64 || echo "chromedriver-linux64 subfolder not found") \
    && rm -rf /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# ImageMagick 보안 정책 수정 (주석 처리 유지)
# RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/g' /etc/ImageMagick-6/policy.xml || \
#     sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/g' /etc/ImageMagick/policy.xml || \
#     echo "ImageMagick policy.xml not found or sed command failed. TextClip MIGHT have issues."

# Python 라이브러리 설치 (root 권한으로 실행하여 시스템 전체에 설치)
# 프로젝트 루트의 requirements.txt를 컨테이너의 /tmp 디렉토리로 복사
COPY requirements.txt /tmp/requirements.txt

RUN pip3 install --upgrade pip \
    && pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/requirements.txt

# WebDriver Manager 및 코드 포맷터 설치 (root 권한)
RUN pip3 install webdriver-manager black autopep8

# 작업 환경을 vscode 사용자로 다시 설정 (컨테이너 실행 시 기본 사용자)
USER vscode

# Python이 출력을 즉시 버퍼링하지 않도록 설정
ENV PYTHONUNBUFFERED 1