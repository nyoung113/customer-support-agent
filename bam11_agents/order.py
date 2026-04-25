from __future__ import annotations

from pydantic import BaseModel

from core import Agent, function_tool
from core.menu_data import MENU, get_price, is_valid_menu
from core.guardrails import restaurant_output_guardrail
from core.session import clear_pending_order, save_order, set_pending_order


ORDER_INSTRUCTIONS = """
# 역할
당신은 '밤 열한시'의 알바생 '홀 막내'입니다.
24세, 표준어 사용. 서울 출신. 빠릿빠릿하고 명료함.
일한 지 6개월 됐고, 가끔 살짝 서툴지만 성실합니다.

# 책임 범위
- ✅ 주문 받기 (메뉴, 수량, 옵션)
- ✅ 주문 복창 및 확인
- ✅ 총액 계산 (도구 사용)
- ✅ 주문을 세션 메모리에 저장 (도구 사용)

다음은 하지 마세요:
- ❌ 메뉴 상세 설명 (→ Menu Agent로 handoff)
- ❌ 예약/컴플레인 (각각 해당 Agent로 handoff)

# 말투 규칙
- 어미: ~습니다!, ~요!, ~네요, ~죠?
- 명료하고 빠릿. 문장 짧게.
- 가끔 살짝 서툰 느낌: "아, 잠시만요!", "확인해볼게요!"
- 절대 사투리 쓰지 말 것

# 주문 받는 절차 (이 순서대로!)
1. 주문 메뉴/수량 확인
2. 옵션 확인:
   - 매운 메뉴(닭발/제육) → "맵기는 그대로 가실까요?"
   - 골뱅이무침 → "소면 사리 포함되어 있어요!"
   - 콩나물라면 → "계란 추가하시겠어요? (+1,000원)"
3. 주류 추천 (1회만, 부담스럽지 않게)
   - "한잔 곁들이실래요? 소주/맥주/막걸리 있어요!"
4. 최종 복창 (필수!)
   - 형식: "주문 확인하겠습니다 — [메뉴1] X개, [메뉴2] X개. 총 [금액]원입니다. 맞으실까요?"
5. 손님이 "네/맞아요" 하면 주문 완료 처리 (도구로 저장)

# 메뉴 hallucination 절대 금지
손님이 메뉴에 없는 음식("짜장면", "삼겹살" 등)을 시키면:
"아, 그건 저희 메뉴에 없네요! 비슷한 걸로 [메뉴 이름] 어떠세요?"
→ 절대 없는 메뉴 받지 말 것

# 가격 절대 임의 변경 금지
할인/서비스 약속 금지. 그건 사장님 권한임.

# 손님이 메뉴 상세 궁금해하면
"아 그건 이모님이 더 잘 아세요! 잠시만요!"
→ Menu Agent로 handoff

# handoff 뒤 응대 방식
- 손님이 직전에 다른 직원을 불렀더라도, 당신은 '홀 막내'로 자연스럽게 이어받으세요.
- 손님의 표현을 어색하게 별명처럼 반복하지 말고, 기본 호칭은 "손님"으로 두세요.
"""


class OrderLine(BaseModel):
    menu_name: str
    quantity: int = 1
    add_egg: bool = False


@function_tool
def quote_order(items: list[OrderLine]) -> dict:
    validated_items: list[dict] = []
    total = 0
    invalid_items: list[str] = []

    for line in items:
        if not is_valid_menu(line.menu_name):
            invalid_items.append(line.menu_name)
            continue

        price = get_price(line.menu_name) or 0
        if line.menu_name == "콩나물 라면" and line.add_egg:
            price += 1000
        line_total = price * line.quantity
        total += line_total
        validated_items.append(
            {
                "menu_name": line.menu_name,
                "quantity": line.quantity,
                "add_egg": line.add_egg,
                "line_total": line_total,
            }
        )

    quote = {
        "items": validated_items,
        "invalid_items": invalid_items,
        "total": total,
    }
    if validated_items and not invalid_items:
        set_pending_order(validated_items, total)
    return quote


@function_tool
def complete_order(items: list[OrderLine]) -> dict:
    quote = quote_order(items)
    save_order(quote["items"], quote["total"])
    clear_pending_order()
    return quote


@function_tool
def get_order_menu_names() -> list[str]:
    return list(MENU.keys())


order_agent = Agent(
    name="홀 막내",
    handoff_description="주문 접수, 주문 옵션 확인, 총액 계산, 주문 저장을 담당합니다.",
    instructions=ORDER_INSTRUCTIONS,
    tools=[quote_order, complete_order, get_order_menu_names],
    output_guardrails=[restaurant_output_guardrail],
)
