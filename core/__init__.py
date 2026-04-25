from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _load_sdk_package():
    project_root = Path(__file__).resolve().parent.parent
    original_sys_path = list(sys.path)

    try:
        sys.path = [
            path
            for path in sys.path
            if Path(path or ".").resolve() != project_root
        ]
        if "agents" in sys.modules:
            del sys.modules["agents"]
        return importlib.import_module("agents")
    finally:
        sys.path = original_sys_path


_sdk = _load_sdk_package()
_handoff_prompt = importlib.import_module("agents.extensions.handoff_prompt")

Agent = _sdk.Agent
GuardrailFunctionOutput = _sdk.GuardrailFunctionOutput
InputGuardrailTripwireTriggered = _sdk.InputGuardrailTripwireTriggered
OutputGuardrailTripwireTriggered = _sdk.OutputGuardrailTripwireTriggered
RunContextWrapper = _sdk.RunContextWrapper
Runner = _sdk.Runner
function_tool = _sdk.function_tool
handoff = _sdk.handoff
input_guardrail = _sdk.input_guardrail
output_guardrail = _sdk.output_guardrail
prompt_with_handoff_instructions = _handoff_prompt.prompt_with_handoff_instructions

__all__ = [
    "Agent",
    "GuardrailFunctionOutput",
    "InputGuardrailTripwireTriggered",
    "OutputGuardrailTripwireTriggered",
    "RunContextWrapper",
    "Runner",
    "function_tool",
    "handoff",
    "input_guardrail",
    "output_guardrail",
    "prompt_with_handoff_instructions",
]
