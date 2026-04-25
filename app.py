from __future__ import annotations

import asyncio
import os

import streamlit as st

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
    conversation_as_input,
    get_current_agent_persona,
    init_session,
    reset_session,
    set_current_agent,
)


st.set_page_config(page_title="밤 열한시", page_icon="🌙", layout="wide")

try:
    secrets_api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    secrets_api_key = None

if "OPENAI_API_KEY" not in os.environ and secrets_api_key:
    os.environ["OPENAI_API_KEY"] = secrets_api_key

HAS_API_KEY = bool(os.getenv("OPENAI_API_KEY"))

init_session()

AGENT_BY_KEY = {
    "triage": triage_agent,
    "menu": menu_agent,
    "order": order_agent,
    "reservation": reservation_agent,
    "complaints": complaints_agent,
}


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
        st.markdown(
            f"""
            <span style="background-color:{persona['color']}; color:white; padding:2px 8px;
            border-radius:4px; font-size:12px; font-weight:600;">
            {persona['emoji']} {persona['name']}
            </span>
            """,
            unsafe_allow_html=True,
        )
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
        st.write("예약", st.session_state["reservations"] or [])
        st.write("컴플레인", st.session_state["complaints"] or [])

        with st.expander("가드레일 로그", expanded=False):
            st.write(st.session_state["guardrail_violations"] or [])

        with st.expander("디버그 로그", expanded=False):
            for entry in st.session_state["debug_log"]:
                st.write(entry)


async def _run_agents(input_items: list[dict], allow_retry: bool = True) -> tuple[str, str]:
    set_current_agent("triage")
    add_debug_log("[turn] triage start")

    try:
        result = await Runner.run(triage_agent, input_items, context=None)
        response_text = result.final_output if isinstance(result.final_output, str) else str(result.final_output)
        agent_key = st.session_state.get("current_agent", "triage")
        add_debug_log(f"[turn] completed by {agent_key}")
        return response_text, agent_key

    except InputGuardrailTripwireTriggered as exc:
        response_text = handle_input_guardrail_tripwire(exc.guardrail_result.output)
        set_current_agent("triage")
        return response_text, "triage"

    except OutputGuardrailTripwireTriggered as exc:
        reason = handle_output_guardrail_tripwire(exc.guardrail_result.output)
        if not allow_retry:
            set_current_agent("triage")
            return "잠시 문제가 있어유. 다시 시도해주셔유.", "triage"

        add_debug_log("[turn] output guardrail retry once")
        retry_items = input_items + [
            {
                "role": "user",
                "content": (
                    "직전 응답은 내부 검증을 통과하지 못했습니다. 공식 메뉴/가격과 현재 페르소나를 지켜 "
                    "다시 한 번 정확하게 답해주세요."
                ),
            }
        ]
        return await _run_agents(retry_items, allow_retry=False)

    except Exception as exc:
        add_debug_log(f"[error] {type(exc).__name__}: {exc}")
        set_current_agent("triage")
        return "잠시 문제가 있어유. 다시 시도해주셔유.", "triage"


async def handle_user_turn(user_text: str) -> None:
    add_message("user", user_text)
    input_items = conversation_as_input()
    response_text, agent_key = await _run_agents(input_items)
    add_message("assistant", response_text, agent=agent_key)


render_header()
render_current_agent_banner()
render_sidebar()

for msg in st.session_state["conversation"]:
    render_message(msg)

placeholder = "메뉴, 주문, 예약, 불만 말씀해주셔유" if HAS_API_KEY else "OPENAI_API_KEY를 secrets에 넣어주셔야 해유"
user_input = st.chat_input(placeholder, disabled=not HAS_API_KEY)

if user_input:
    asyncio.run(handle_user_turn(user_input))
    st.rerun()
