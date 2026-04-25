import dotenv

dotenv.load_dotenv()
import asyncio
import os
import uuid
import streamlit as st
from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
    function_tool,
    RunContextWrapper,
)
from models import UserAccountContext
from my_agents.account_agent import account_agent
from my_agents.billing_agent import billing_agent
from my_agents.order_agent import order_agent
from my_agents.technical_agent import technical_agent
from my_agents.triage_agent import triage_agent




@function_tool
# 왜 wrapper로 감싸는가? -> context를 wrapper로 감싸서 전달하기 때문. wrapper는 context를 포함하는 객체로, 도구가 실행될 때 필요한 정보를 담고 있다.
def get_user_tier(wrapper: RunContextWrapper[UserAccountContext]) -> str:
    # In a real application, you would fetch this information from a database or an API
    return f"The user{wrapper.context.customer_id} has a {wrapper.context.tier} account."

# 도구는 wrapper를 통해 context에 접근할 수 있다. wrapper.context를 통해 UserAccountContext의 속성에 접근할 수 있다. 예를 들어, wrapper.context.customer_id로 고객 ID에 접근할 수 있다.
# 실제에서는 데이터베이스나 API에서 이 정보를 가져올 것이다. 여기서는 간단히 문자열로 반환한다.
# 이렇게 하면 민감한 정보를 도구에 안전하게 전달할 수 있다. 도구는 wrapper를 통해 필요한 정보에 접근할 수 있지만, 외부에서는 직접적으로 context에 접근할 수 없다.
@function_tool
def change_email(wrapper: RunContextWrapper[UserAccountContext]):
    return ""

has_openai_api_key = bool(os.getenv("OPENAI_API_KEY"))

user_account_context = UserAccountContext(
    customer_id=123,
    name="John Doe",
    email="john.doe@example.com",
    tier="basic",
)

if "active_agent_name" not in st.session_state:
    st.session_state["active_agent_name"] = "Triage Agent"

AGENTS_BY_NAME = {
    "Triage Agent": triage_agent,
    "Technical Support Agent": technical_agent,
    "Billing Support Agent": billing_agent,
    "Order Management Agent": order_agent,
    "Account Management Agent": account_agent,
}

if "session" not in st.session_state:
    session_id = f"chat-history-{uuid.uuid4()}"
    st.session_state["session"] = SQLiteSession(
        session_id,
        "customer-support-memory.db",
    )
    st.session_state["session_id"] = session_id
session = st.session_state["session"]

async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))


asyncio.run(paint_history())

if st.session_state.get("active_agent_name") == "Technical Support Agent":
    st.markdown(
        """
        <style>
        .stApp {
            background: #dbeafe;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

if not has_openai_api_key:
    st.warning("OPENAI_API_KEY is not set. Add it to your .env file before chatting with the assistant.")


async def run_agent(message):
    current_agent = triage_agent

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        try:
            stream = Runner.run_streamed(
                current_agent,
                message,
                session=session,
                context=user_account_context, # goes to tools , 

            )

            async for event in stream.stream_events():
                if event.type != "raw_response_event":
                    with st.sidebar:
                        st.write(f"Event: {event.type}")
                        item = getattr(event, "item", None)
                        if item is not None:
                            st.write(f"Item type: {getattr(item, 'type', type(item).__name__)}")
                if event.type == "raw_response_event":
                    # This event is emitted for every delta in the response, so we can update the UI in real time
                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response.replace("$", "\$"))
        except InputGuardrailTripwireTriggered as exc:
            text_placeholder.write(
                exc.guardrail_result.output.output_info.reason.replace("$", "\$")
            )
        except OutputGuardrailTripwireTriggered as exc:
            reason = getattr(exc.guardrail_result.output.output_info, "reason", "")
            fallback = "I need to revise that response to keep it within technical support boundaries."
            text_placeholder.write((reason or fallback).replace("$", "\$"))

message = st.chat_input(
    "Write a message for your assistant" if has_openai_api_key else "Set OPENAI_API_KEY in .env to enable chat",
    disabled=not has_openai_api_key,
)

if message:

    if "text_placeholder" in st.session_state:
        st.session_state["text_placeholder"].empty()

    if message:
        with st.chat_message("human"):
            st.write(message)
        asyncio.run(run_agent(message))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
        st.session_state["active_agent_name"] = "Triage Agent"
    st.caption(f"Session: {st.session_state.get('session_id', 'unknown')}")
    st.caption(f"Active agent: {st.session_state.get('active_agent_name', 'unknown')}")
