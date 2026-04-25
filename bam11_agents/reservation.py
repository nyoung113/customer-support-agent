from __future__ import annotations

from datetime import datetime

from core import Agent, function_tool
from core.guardrails import restaurant_output_guardrail
from core.session import save_reservation


RESERVATION_INSTRUCTIONS = """
# 역할
당신은 '밤 열한시'의 운영자 '사장님'입니다.
45세 남성, 표준어 사용. 차분하고 정중하며 책임감이 강합니다.
지금은 예약 업무를 처리하고 있습니다.

# 책임 범위
- ✅ 예약 받기 (날짜/시간/인원/성함/연락처)
- ✅ 예약 확인 및 변경
- ✅ 영업 정보 안내

# 말투 규칙
- 어미: ~입니다, ~드립니다, ~겠습니다
- 격식 있되 차갑지 않음. 단정함.
- 절대 사투리 쓰지 말 것
- 가벼운 농담/이모지 사용 금지

# 예약 받는 절차 (이 순서대로!)
1. 날짜 확인 ("○월 ○일")
2. 시간 확인 ("○시")
3. 인원 확인 ("○명")
4. 성함 확인
5. 연락처 확인 (선택, "원하시면 알려주세요")
6. 특별 요청사항 확인 (선택)
7. 최종 확인:
   "○월 ○일 ○시, ○명, ○○○님 성함으로 예약 도와드리겠습니다. 맞으실까요?"
8. 예약 완료 안내 (도구로 저장):
   "예약 완료되었습니다. 당일 뵙겠습니다."

# 영업 정보 (정확히 답변)
- 영업시간: 매일 17:00 ~ 02:00 (라스트 오더 01:00)
- 좌석: 총 24석 (4인 테이블 6개)
- 예약 가능 시간대: 17:00 ~ 23:00 시작
- 노쇼 방지: 예약 시간 30분 초과 시 자동 취소

# 제약 조건 (반드시 검증)
- 영업시간 외 시간 요청 → "죄송합니다. 영업시간은 17시부터 02시까지입니다."
- 24석 초과 인원 한 번에 예약 → "단체 예약은 별도로 안내드리겠습니다."
- 과거 날짜 → "지난 날짜로는 예약이 어렵습니다."

# handoff 뒤 응대 방식
- 손님이 직전에 삼촌이나 이모를 불렀더라도, 당신은 '사장님'으로 차분히 이어받으세요.
- 손님의 표현을 어색하게 반복하지 말고, 기본 호칭은 "고객님" 또는 "손님"으로 두세요.
"""


@function_tool
def get_business_hours() -> dict:
    return {
        "open": "17:00",
        "close": "02:00",
        "last_order": "01:00",
        "reservable_start_end": "17:00 ~ 23:00",
        "seats": 24,
    }


@function_tool
def validate_reservation_request(date: str, time: str, party_size: int) -> dict:
    issues: list[str] = []
    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d").date()
        if requested_date < datetime.now().date():
            issues.append("과거 날짜로는 예약이 어렵습니다.")
    except ValueError:
        issues.append("날짜 형식은 YYYY-MM-DD로 확인해 주세요.")

    try:
        hour = int(time.split(":")[0])
        if hour < 17 or hour > 23:
            issues.append("예약 시작 가능 시간은 17:00부터 23:00까지입니다.")
    except (ValueError, IndexError):
        issues.append("시간 형식은 HH:MM으로 확인해 주세요.")

    if party_size > 24:
        issues.append("24석 초과 단체 예약은 별도 안내가 필요합니다.")

    return {"is_valid": not issues, "issues": issues}


@function_tool
def complete_reservation(
    date: str,
    time: str,
    party_size: int,
    name: str,
    phone: str = "",
    special_request: str = "",
) -> dict:
    validation = validate_reservation_request(date, time, party_size)
    if not validation["is_valid"]:
        return validation

    save_reservation(date, time, party_size, name, phone, special_request)
    return {
        "is_valid": True,
        "date": date,
        "time": time,
        "party_size": party_size,
        "name": name,
    }


reservation_agent = Agent(
    name="사장님",
    handoff_description="예약 접수, 예약 확인, 영업시간 안내를 담당합니다.",
    instructions=RESERVATION_INSTRUCTIONS,
    tools=[get_business_hours, validate_reservation_request, complete_reservation],
    output_guardrails=[restaurant_output_guardrail],
)
