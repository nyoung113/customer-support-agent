# 🌙 밤 열한시 (Bam11) - Restaurant Bot

충청도 삼촌과 전라도 이모가 운영하는 가상 한식 포장마차 챗봇.  
OpenAI Agents SDK + Streamlit 기반 멀티 에이전트 시스템입니다.

## 캐릭터
- 🟡 11시 삼촌 (Triage) - 충청도, 손님 응대 라우터
- 🟠 주방 이모 (Menu) - 전라도, 메뉴 추천
- 🟢 홀 막내 (Order) - 표준어, 주문 처리
- 🔵 사장님 (Reservation) - 예약
- 🔴 사장님 (Complaints) - 불만 처리

## 로컬 실행
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml에 OPENAI_API_KEY 입력
streamlit run app.py
```

## Streamlit Cloud 배포
1. share.streamlit.io 접속
2. GitHub 리포지터리 연결
3. Secrets에 OPENAI_API_KEY 추가
4. Deploy
