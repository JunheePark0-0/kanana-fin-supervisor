# 백엔드를 백그라운드로 실행
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 프론트엔드를 실행 (브라우저)
streamlit run app.py

# streamlit이 꺼지면 백엔드도 같이 꺼지도록 설정
kill $BACKEND_PID