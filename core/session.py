from __future__ import annotations

import uuid
from typing import Any

import streamlit as st

from core.personas import PERSONAS


TRIAGE_GREETING = "어어~ 어서 와유. 오늘은 뭐 도와드릴까유?"


def init_session() -> None:
    defaults = {
        "conversation": [],
        "current_agent": "triage",
        "orders": [],
        "reservations": [],
        "complaints": [],
        "guardrail_violations": [],
        "debug_log": [],
        "session_id": f"bam11-{uuid.uuid4()}",
        "last_rendered_handoff": None,
        "regen_attempts": 0,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state["conversation"]:
        add_message("assistant", TRIAGE_GREETING, agent="triage")


def reset_session() -> None:
    for key in [
        "conversation",
        "current_agent",
        "orders",
        "reservations",
        "complaints",
        "guardrail_violations",
        "debug_log",
        "session_id",
        "last_rendered_handoff",
        "regen_attempts",
    ]:
        st.session_state.pop(key, None)
    init_session()


def add_message(role: str, content: str, agent: str | None = None) -> None:
    message = {"role": role, "content": content}
    if agent is not None:
        message["agent"] = agent
    st.session_state["conversation"].append(message)


def add_handoff(from_agent: str, to_agent: str) -> None:
    st.session_state["conversation"].append(
        {
            "role": "handoff",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "content": f"{PERSONAS[from_agent]['emoji']}→{PERSONAS[to_agent]['emoji']} {PERSONAS[to_agent]['name']}로 연결되었습니다",
        }
    )


def save_order(items: list[dict[str, Any]], total: int) -> None:
    st.session_state["orders"].append({"items": items, "total": total})


def save_reservation(
    date: str,
    time: str,
    party_size: int,
    name: str,
    phone: str | None = None,
    special_request: str | None = None,
) -> None:
    st.session_state["reservations"].append(
        {
            "date": date,
            "time": time,
            "party_size": party_size,
            "name": name,
            "phone": phone or "",
            "special_request": special_request or "",
        }
    )


def save_complaint(issue_type: str, description: str, resolution: str) -> None:
    st.session_state["complaints"].append(
        {
            "issue_type": issue_type,
            "description": description,
            "resolution": resolution,
        }
    )


def set_current_agent(agent_key: str) -> None:
    st.session_state["current_agent"] = agent_key


def get_current_agent_persona() -> dict[str, str]:
    return PERSONAS[st.session_state.get("current_agent", "triage")]


def add_guardrail_violation(kind: str, reason: str) -> None:
    st.session_state["guardrail_violations"].append({"kind": kind, "reason": reason})
    add_debug_log(f"[guardrail:{kind}] {reason}")


def add_debug_log(message: str) -> None:
    st.session_state["debug_log"].append(message)


def conversation_as_input() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in st.session_state["conversation"]:
        if entry["role"] not in {"user", "assistant"}:
            continue
        items.append({"role": entry["role"], "content": entry["content"]})
    return items
