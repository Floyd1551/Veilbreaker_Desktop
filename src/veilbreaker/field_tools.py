"""Combined offline calculator catalog and dispatch for the field workbench."""
from . import engineering_tools, rf_tools


TOOLS = rf_tools.TOOLS + engineering_tools.TOOLS
REGISTRY = {tool.key: tool for tool in TOOLS}


def calculate(tool_id, inputs):
    if tool_id in engineering_tools.REGISTRY:
        return engineering_tools.calculate(tool_id, inputs)
    return rf_tools.calculate(tool_id, inputs)


format_snapshot = rf_tools.format_snapshot
