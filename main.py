import dotenv

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import streamlit as st
from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
    function_tool,
    RunContextWrapper,
)
from models import UserAccontContext
from my_agents.triage_agent import restaurant_agent as agent




@function_tool
# 왜 wrapper로 감싸는가? -> context를 wrapper로 감싸서 전달하기 때문. wrapper는 context를 포함하는 객체로, 도구가 실행될 때 필요한 정보를 담고 있다.
def get_user_tier(wrapper: RunContextWrapper[UserAccontContext]) -> str:
    # In a real application, you would fetch this information from a database or an API
    return f"The user{wrapper.context.customer_id} has a {wrapper.context.tier} account."

# 도구는 wrapper를 통해 context에 접근할 수 있다. wrapper.context를 통해 UserAccountContext의 속성에 접근할 수 있다. 예를 들어, wrapper.context.customer_id로 고객 ID에 접근할 수 있다.
# 실제에서는 데이터베이스나 API에서 이 정보를 가져올 것이다. 여기서는 간단히 문자열로 반환한다.
# 이렇게 하면 민감한 정보를 도구에 안전하게 전달할 수 있다. 도구는 wrapper를 통해 필요한 정보에 접근할 수 있지만, 외부에서는 직접적으로 context에 접근할 수 없다.
@function_tool
def change_email(wrapper: RunContextWrapper[UserAccontContext]):
    return ""


client = OpenAI()

user_account_context = UserAccontContext(
    customer_id=123,
    name="John Doe",
    tier="basic",
)

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "customer-support-memory.db",
    )
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
                        st.write(message["content"][0]["text"].replace("$", "\\$"))


asyncio.run(paint_history())


async def run_agent(message):

    with st.chat_message("ai"):
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        try:
            stream = Runner.run_streamed(
                agent,
                message,
                session=session,
                context=user_account_context, # goes to tools , 

            )

            async for event in stream.stream_events():
                if event.type == "raw_response_event":
                    # This event is emitted for every delta in the response, so we can update the UI in real time
                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response.replace("$", "\\$"))
        except InputGuardrailTripwireTriggered as exc:
            guardrail_output = exc.guardrail_result.output.output_info
            text_placeholder.write(
                f"I can help with restaurant-related questions only. {guardrail_output.reason}"
            )
        except OutputGuardrailTripwireTriggered:
            text_placeholder.write(
                "I am sorry, but I need to revise that response to keep it professional and customer-safe. Please ask again with a little more detail."
            )


message = st.chat_input(
    "Write a message for your assistant",
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
    st.write(asyncio.run(session.get_items()))
