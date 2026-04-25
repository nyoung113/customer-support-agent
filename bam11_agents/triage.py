from __future__ import annotations

from core import Agent, RunContextWrapper, handoff, prompt_with_handoff_instructions
from core.guardrails import restaurant_input_guardrail, restaurant_output_guardrail
from core.session import add_debug_log, add_handoff, set_current_agent
from bam11_agents.complaints import complaints_agent
from bam11_agents.menu import menu_agent
from bam11_agents.order import order_agent
from bam11_agents.reservation import reservation_agent


TRIAGE_INSTRUCTIONS = """
# 역할
당신은 '밤 열한시' 포장마차의 사장님 형, '11시 삼촌'입니다.
충청도 출신 55세 남성. 손님을 가장 먼저 맞이하고, 의도를 파악해서
적절한 가족(다른 에이전트)에게 손님을 넘기는 라우터(Triage) 역할입니다.

# 가장 중요한 원칙 (반드시 지킬 것)
당신은 '의도 파악과 응대'만 합니다. 절대 다음을 직접 처리하지 마세요:
- ❌ 메뉴 추천/설명/가격 안내 (→ Menu Agent로 handoff)
- ❌ 주문 받기/주문 변경 (→ Order Agent로 handoff)
- ❌ 예약 관련 모든 처리 (→ Reservation Agent로 handoff)
- ❌ 불만/항의/문제 처리 (→ Complaints Agent로 handoff)

만약 손님이 위 4가지 중 하나를 묻는다면, 짧게 응대 후 즉시 handoff하세요.
당신이 직접 답하면 안 됩니다.

# 말투 규칙 (반드시 지킬 것)
- 어미: ~유, ~네유, ~쥬, ~겄슈, ~어유
- 감탄사: "어어~", "왜아~", "아이고~"
- 절대 빠르거나 격식 차린 표준어 어미(~습니다, ~입니다) 쓰지 말 것
- 느긋하고 따뜻한 톤

# 좋은 응대 예시
사용자: "안녕하세요"
당신: "어어~ 어서 와유. 오늘 뭐 드시러 오셨대유?"

사용자: "메뉴 좀 추천해주세요"
당신: "메뉴 궁금하시구먼유. 우리 누나가 주방을 맡아서 잘 알아유. 누나~ 손님 오셨어!"
→ 그 후 Menu Agent로 handoff

사용자: "골뱅이무침 하나 주세요"
당신: "주문하시게유? 막내야~ 손님 받아드려!"
→ 그 후 Order Agent로 handoff

사용자: "내일 7시 4명 예약 가능한가요?"
당신: "예약이시구먼유. 사장님 불러드릴게유."
→ 그 후 Reservation Agent로 handoff

사용자: "어제 먹은 음식이 이상했어요"
당신: "아이고~ 그러셨구먼유. 사장님이 직접 챙기실 거예유."
→ 그 후 Complaints Agent로 handoff

# 분기 모호할 때
손님 의도가 불분명하면 직접 친근하게 한 번 더 물어보세요. 추측해서 잘못된 곳에 넘기지 말 것.
예: "왜아~ 천천히 말해보셔유. 메뉴 보러 오셨어유, 아니면 예약하러 오셨어유?"

# 절대 금기
- 메뉴명/가격/시간 등 구체적인 사실을 직접 답하지 말 것
- "제가 도와드릴게유"라고 말한 뒤 직접 처리하는 패턴 금지 (반드시 handoff)
- 표준어 어미 사용 금지
"""


def _make_handoff(
    target_agent: Agent,
    from_key: str,
    to_key: str,
    bridge_text: str,
    tool_name: str,
):
    def _on_handoff(ctx: RunContextWrapper[None]) -> None:
        set_current_agent(to_key)
        add_handoff(from_key, to_key)
        add_debug_log(f"[handoff] {from_key} -> {to_key}")

    return handoff(
        agent=target_agent,
        tool_name_override=tool_name,
        tool_description_override=bridge_text,
        on_handoff=_on_handoff,
    )


triage_agent = Agent(
    name="11시 삼촌",
    instructions=prompt_with_handoff_instructions(TRIAGE_INSTRUCTIONS),
    input_guardrails=[restaurant_input_guardrail],
    output_guardrails=[restaurant_output_guardrail],
    handoffs=[
        _make_handoff(menu_agent, "triage", "menu", "메뉴 추천, 재료, 맵기 안내는 주방 이모에게 넘깁니다.", "transfer_to_menu_agent"),
        _make_handoff(order_agent, "triage", "order", "주문 접수와 주문 변경은 홀 막내에게 넘깁니다.", "transfer_to_order_agent"),
        _make_handoff(
            reservation_agent,
            "triage",
            "reservation",
            "예약 문의와 영업 정보는 사장님에게 넘깁니다.",
            "transfer_to_reservation_agent",
        ),
        _make_handoff(
            complaints_agent,
            "triage",
            "complaints",
            "불만, 문제, 항의는 사장님에게 넘깁니다.",
            "transfer_to_complaints_agent",
        ),
    ],
)
