from __future__ import annotations

import asyncio
import os
import re

import streamlit as st
from dotenv import load_dotenv

from bam11_agents import complaints_agent, menu_agent, order_agent, reservation_agent, triage_agent
from core import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
)
from core.guardrails import (
    handle_input_guardrail_tripwire,
    handle_output_guardrail_tripwire,
)
from core.personas import PERSONAS
from core.session import (
    add_debug_log,
    add_message,
    clear_pending_order,
    conversation_as_input,
    get_last_assistant_agent,
    get_current_agent_persona,
    get_pending_order,
    init_session,
    reset_session,
    save_order,
    set_current_agent,
)


st.set_page_config(page_title="밤 열한시", page_icon="🌙", layout="wide")

load_dotenv()


def _bootstrap_api_key() -> str | None:
    for key_name in ("OPENAI_API_KEY", "OPEN_API_KEY"):
        try:
            secret_value = st.secrets[key_name]
        except Exception:
            secret_value = None
        if secret_value:
            os.environ["OPENAI_API_KEY"] = secret_value
            return secret_value

    for key_name in ("OPENAI_API_KEY", "OPEN_API_KEY"):
        env_value = os.getenv(key_name)
        if env_value:
            os.environ["OPENAI_API_KEY"] = env_value
            return env_value

    return None


API_KEY = _bootstrap_api_key()
HAS_API_KEY = bool(API_KEY)

init_session()

AGENT_BY_KEY = {
    "triage": triage_agent,
    "menu": menu_agent,
    "order": order_agent,
    "reservation": reservation_agent,
    "complaints": complaints_agent,
}

LOADING_MESSAGES = {
    "triage": "밤 열한시 식구들이 누가 도와드릴지 보고 있어요...",
    "menu": "주방 이모가 메뉴판이랑 냄비부터 살펴보는 중이여...",
    "order": "홀 막내가 주문 내용을 빠르게 확인하는 중입니다...",
    "reservation": "사장님이 예약 장부를 확인하고 있습니다...",
    "complaints": "사장님이 상황을 차분히 확인하고 있습니다...",
}


def get_loading_message(agent_key: str) -> str:
    return LOADING_MESSAGES.get(agent_key, "밤 열한시 식구들이 답을 준비하는 중이에요...")


def resolve_agent_key(agent_name: str) -> str:
    if agent_name == "11시 삼촌":
        return "triage"
    if agent_name == "주방 이모":
        return "menu"
    if agent_name == "홀 막내":
        return "order"
    return st.session_state.get("current_agent", "triage")


def render_agent_badge(agent_key: str, target=None) -> None:
    persona = PERSONAS[agent_key]
    target = target or st
    target.markdown(
        f"""
        <span style="background-color:{persona['color']}; color:white; padding:2px 8px;
        border-radius:4px; font-size:12px; font-weight:600;">
        {persona['emoji']} {persona['name']}
        </span>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div style="padding: 1rem 0 0.5rem 0;">
            <h1 style="margin:0;">🌙 밤 열한시</h1>
            <p style="margin:0.2rem 0 0 0;color:#666;">
                충청도 삼촌과 전라도 이모가 운영하는 캐주얼 한식 포장마차
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_current_agent_banner() -> None:
    persona = get_current_agent_persona()
    st.markdown(
        f"""
        <div style="margin: 0.5rem 0 1rem 0; padding: 0.75rem 1rem; border-radius: 12px;
             background: {persona['color']}22; border: 1px solid {persona['color']}55;">
            <strong>{persona['emoji']} {persona['name']}</strong>님과 대화 중
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_message(msg: dict) -> None:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
        return

    if msg["role"] == "handoff":
        st.markdown(
            f"""
            <div style="text-align:center; margin:0.75rem 0; color:#666;">
                {msg['content']}
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    agent_key = msg.get("agent", "triage")
    persona = PERSONAS[agent_key]
    with st.chat_message("assistant", avatar=persona["emoji"]):
        render_agent_badge(agent_key)
        st.markdown(msg["content"])


def render_sidebar() -> None:
    with st.sidebar:
        persona = get_current_agent_persona()
        st.markdown(
            f"### {persona['emoji']} 현재 담당\n**{persona['name']}** ({persona['role']})"
        )
        st.caption(f"Session: {st.session_state['session_id']}")

        if st.button("🔄 새 대화 시작", use_container_width=True):
            reset_session()
            st.rerun()

        st.divider()
        st.markdown("### 세션 요약")
        st.write("주문", st.session_state["orders"] or [])
        if st.session_state.get("pending_order"):
            st.write("임시 주문", st.session_state["pending_order"])
        st.write("예약", st.session_state["reservations"] or [])
        st.write("컴플레인", st.session_state["complaints"] or [])

        with st.expander("가드레일 로그", expanded=False):
            st.write(st.session_state["guardrail_violations"] or [])

        with st.expander("디버그 로그", expanded=False):
            for entry in st.session_state["debug_log"]:
                st.write(entry)


def is_order_confirmation_message(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text.lower())
    confirmations = {
        "네",
        "넹",
        "네에",
        "네네",
        "네넹",
        "맞아요",
        "맞습니다",
        "좋아요",
        "그래요",
        "그려요",
        "오케이",
        "ㅇㅇ",
        "응",
    }
    return normalized in confirmations


def finalize_pending_order() -> tuple[str, str]:
    pending_order = get_pending_order()
    if not pending_order:
        return "잠시 문제가 있어유. 다시 시도해주셔유.", "triage"

    save_order(pending_order["items"], pending_order["total"])
    clear_pending_order()
    set_current_agent("order")
    add_debug_log("[turn] pending order confirmed without rerunning agent")

    item_text = ", ".join(
        f"{item['menu_name']} {item['quantity']}개"
        for item in pending_order["items"]
    )
    return (
        f"주문 접수되었습니다! {item_text} 주문으로 넣어둘게요. 총 {pending_order['total']:,}원입니다. 감사합니다!",
        "order",
    )


async def _run_agents(
    input_items: list[dict],
    badge_placeholder,
    loading_placeholder,
    response_placeholder,
    starting_agent_key: str = "triage",
    allow_retry: bool = True,
) -> tuple[str, str]:
    set_current_agent(starting_agent_key)
    add_debug_log(f"[turn] {starting_agent_key} start")
    active_agent_key = starting_agent_key
    visible_agent_key: str | None = None

    try:
        starting_agent = AGENT_BY_KEY[starting_agent_key]
        result = Runner.run_streamed(starting_agent, input_items, context=None)
        response_text = ""

        async for event in result.stream_events():
            if event.type == "agent_updated_stream_event":
                active_agent_key = resolve_agent_key(event.new_agent.name)
                if active_agent_key != "triage":
                    visible_agent_key = active_agent_key
                    badge_placeholder.empty()
                    render_agent_badge(active_agent_key, target=badge_placeholder)
                    loading_placeholder.info(get_loading_message(active_agent_key))
            elif event.type == "run_item_stream_event" and event.name == "handoff_occured":
                active_agent_key = st.session_state.get("current_agent", active_agent_key)
                if active_agent_key != "triage":
                    visible_agent_key = active_agent_key
                    badge_placeholder.empty()
                    render_agent_badge(active_agent_key, target=badge_placeholder)
                    loading_placeholder.info(get_loading_message(active_agent_key))
            elif (
                event.type == "raw_response_event"
                and getattr(event.data, "type", None) == "response.output_text.delta"
            ):
                if not response_text:
                    loading_placeholder.empty()
                    if visible_agent_key is None:
                        visible_agent_key = active_agent_key
                        badge_placeholder.empty()
                        render_agent_badge(visible_agent_key, target=badge_placeholder)
                response_text += event.data.delta
                response_placeholder.markdown(response_text)

        final_output = getattr(result, "final_output", None)
        if not response_text and final_output is not None:
            loading_placeholder.empty()
            if visible_agent_key is None:
                visible_agent_key = active_agent_key
                badge_placeholder.empty()
                render_agent_badge(visible_agent_key, target=badge_placeholder)
            response_text = final_output if isinstance(final_output, str) else str(final_output)
            response_placeholder.markdown(response_text)

        agent_key = st.session_state.get("current_agent", active_agent_key)
        add_debug_log(f"[turn] completed by {agent_key}")
        return response_text, agent_key

    except InputGuardrailTripwireTriggered as exc:
        response_text = handle_input_guardrail_tripwire(exc.guardrail_result.output)
        set_current_agent("triage")
        return response_text, "triage"

    except OutputGuardrailTripwireTriggered as exc:
        handle_output_guardrail_tripwire(exc.guardrail_result.output)
        response_placeholder.empty()
        if not allow_retry:
            set_current_agent("triage")
            return "잠시 문제가 있어유. 다시 시도해주셔유.", "triage"

        add_debug_log("[turn] output guardrail retry once")
        retry_agent_key = st.session_state.get("current_agent", active_agent_key)
        badge_placeholder.empty()
        if retry_agent_key != "triage":
            render_agent_badge(retry_agent_key, target=badge_placeholder)
        loading_placeholder.info("답을 한 번 더 다듬고 있어요...")
        retry_items = input_items + [
            {
                "role": "assistant",
                "content": (
                    "내부 검증 메모: 공식 메뉴와 가격, 현재 담당자의 말투를 지켜 같은 요청에 대해 다시 답하세요."
                ),
            }
        ]
        return await _run_agents(
            retry_items,
            badge_placeholder,
            loading_placeholder,
            response_placeholder,
            starting_agent_key=retry_agent_key,
            allow_retry=False,
        )

    except Exception as exc:
        add_debug_log(f"[error] {type(exc).__name__}: {exc}")
        set_current_agent("triage")
        return "잠시 문제가 있어유. 다시 시도해주셔유.", "triage"


render_header()
render_current_agent_banner()
render_sidebar()

for msg in st.session_state["conversation"]:
    render_message(msg)

placeholder = (
    "메뉴, 주문, 예약, 불만 말씀해주셔유"
    if HAS_API_KEY
    else "OPENAI_API_KEY를 .env 또는 secrets에 넣어주셔야 해유"
)
user_input = st.chat_input(placeholder, disabled=not HAS_API_KEY)

if user_input:
    add_message("user", user_input)

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🌙"):
        badge_placeholder = st.empty()
        loading_placeholder = st.empty()
        response_placeholder = st.empty()

        pending_order = get_pending_order()
        last_assistant_agent = get_last_assistant_agent()

        if pending_order and last_assistant_agent == "order" and is_order_confirmation_message(user_input):
            render_agent_badge("order", target=badge_placeholder)
            loading_placeholder.info("홀 막내가 주문을 최종 접수하고 있습니다...")
            response_text, agent_key = finalize_pending_order()
        else:
            loading_placeholder.info(get_loading_message("triage"))
            response_text, agent_key = asyncio.run(
                _run_agents(
                    conversation_as_input(),
                    badge_placeholder,
                    loading_placeholder,
                    response_placeholder,
                    starting_agent_key="triage",
                )
            )

        loading_placeholder.empty()
        badge_placeholder.empty()
        render_agent_badge(agent_key, target=badge_placeholder)
        response_placeholder.markdown(response_text)

    add_message("assistant", response_text, agent=agent_key)
    st.rerun()
