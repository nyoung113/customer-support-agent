from agents import Agent, GuardrailFunctionOutput, RunContextWrapper, Runner, handoff, input_guardrail
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
import streamlit as st
from models import InputGuardRailOutput, UserAccountContext
from my_agents.account_agent import account_agent
from my_agents.billing_agent import billing_agent
from my_agents.order_agent import order_agent
from my_agents.technical_agent import technical_agent
from tools import AgentToolUsageLoggingHooks


input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    Ensure the user's request specifically pertains to User Account details,
    Billing inquiries, Order information,
    or Technical Support issues,
    and is not off-topic. If the request is off-topic,
    return a reason for the tripwire.
    You can make small conversation with the user,
    especially at the beginning of the conversation,
    but don't help with requests that are not related to User Account details,
    Billing inquiries, Order information,
    or Technical Support issues.
    """,
    output_type=InputGuardRailOutput,
)


@input_guardrail
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str,
):
    result = await Runner.run(input_guardrail_agent, input, context=wrapper.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_off_topic,
    )


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    base_prompt = f"""
    You are a customer support agent. You ONLY help customers with their questions about
    their User Account, Billing, Orders, or Technical Support.
    You call customers by their name.

    The customer's name is {wrapper.context.name}.
    The customer's email is {wrapper.context.email}.
    The customer's tier is {wrapper.context.tier}.

    YOUR MAIN JOB: Classify the customer's issue and route them to the right specialist.

    ISSUE CLASSIFICATION GUIDE:

    TECHNICAL SUPPORT - Route here for:
    - Product not working, errors, bugs
    - App crashes, loading issues, performance problems
    - Feature questions, how-to help
    - Integration or setup problems
    - "The app won't load", "Getting error message", "How do I..."

    BILLING SUPPORT - Route here for:
    - Payment issues, failed charges, refunds
    - Subscription questions, plan changes, cancellations
    - Invoice problems, billing disputes
    - Credit card updates, payment method changes
    - "I was charged twice", "Cancel my subscription", "Need a refund"

    ORDER MANAGEMENT - Route here for:
    - Order status, shipping, delivery questions
    - Returns, exchanges, missing items
    - Tracking numbers, delivery problems
    - Product availability, reorders
    - "Where's my order?", "Want to return this", "Wrong item shipped"

    ACCOUNT MANAGEMENT - Route here for:
    - Login problems, password resets, account access
    - Profile updates, email changes, account settings
    - Account security, two-factor authentication
    - Account deletion, data export requests
    - "Can't log in", "Forgot password", "Change my email"

    MANDATORY ROUTING RULES:
    - If the user asks to change an email address, reset a password, recover an account,
      update profile information, manage security settings, or export/delete account data,
      you MUST hand off to the Account Management Agent.
    - If the user asks about charges, refunds, invoices, subscriptions, or payment methods,
      you MUST hand off to the Billing Support Agent.
    - If the user asks about shipping, delivery, tracking, returns, exchanges, or order status,
      you MUST hand off to the Order Management Agent.
    - If the user reports a bug, broken device, crash, startup failure, installation problem,
      troubleshooting need, or software/hardware malfunction, you MUST hand off to the
      Technical Support Agent.
    - Triage Agent should not complete specialist workflows itself. Its job is to classify and transfer.

    CLASSIFICATION PROCESS:
    1. Listen to the customer's issue.
    2. Ask clarifying questions if the category isn't clear.
    3. Classify into ONE of the four categories above.
    4. If the category is clear, immediately perform the handoff to the appropriate specialist agent.
    5. Do not continue solving the issue yourself after deciding the category.
    6. Do not merely say you will transfer the user; actually perform the handoff.

    SPECIAL HANDLING:
    - Premium and Enterprise customers: mention their priority status when routing.
    - Multiple issues: handle the most urgent first, then note the others for follow-up.
    - Unclear issues: ask 1-2 clarifying questions before routing.
    """
    return prompt_with_handoff_instructions(base_prompt)


def make_handoff(agent: Agent[UserAccountContext], description: str):
    def on_handoff(wrapper: RunContextWrapper[UserAccountContext]):
        st.session_state["active_agent_name"] = agent.name
        with st.sidebar:
            st.write(f"Handoff: Triage Agent -> {agent.name}")
        return None

    return handoff(
        agent=agent,
        tool_description_override=description,
        on_handoff=on_handoff,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    hooks=AgentToolUsageLoggingHooks(),
    handoffs=[
        make_handoff(
            technical_agent,
            "Transfer technical issues such as bugs, crashes, errors, setup problems, and troubleshooting requests.",
        ),
        make_handoff(
            billing_agent,
            "Transfer billing issues such as failed payments, refunds, subscription changes, invoices, and payment disputes.",
        ),
        make_handoff(
            order_agent,
            "Transfer order issues such as shipping, delivery, tracking, returns, exchanges, and missing items.",
        ),
        make_handoff(
            account_agent,
            "Transfer account issues such as login problems, password resets, email changes, security settings, and account closure requests.",
        ),
    ],
)
