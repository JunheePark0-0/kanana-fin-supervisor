#!/bin/bash
set -e  # 중간에 에러 나면 스크립트 즉시 중단

REPO_URL="https://github.com/jhpark0256/Stock_Report_Agent.git"
PROJECT_DIR="app"

echo "1️⃣ 저장소 클론 중..."
git clone "$REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "2️⃣ 가상환경 생성 중..."
python3 -m venv venv
source venv/bin/activate

echo "3️⃣ 패키지 설치 중..."
pip install --upgrade pip
pip install --timeout 1000 --retries 10 -r requirements.txt

echo "4️⃣ .env 파일 확인..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  .env 파일을 만들었습니다. 아래 파일을 직접 채워주세요:"
        echo "    $(pwd)/.env"
        echo ""
        read -p "값을 다 채우셨으면 Enter를 눌러 계속 진행하세요..." 
    else
        echo "❌ .env.example 파일이 없습니다. .env를 직접 만들어주세요."
        exit 1
    fi
else
    echo "✅ .env 파일이 이미 있습니다."
fi

echo "5️⃣ 모델/데이터 준비 중..."
python agent_setup.py

echo "6️⃣ 백엔드/프론트엔드 실행..."
chmod +x run.sh
./run.sh