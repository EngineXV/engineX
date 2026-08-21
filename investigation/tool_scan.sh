#!/usr/bin/env bash

echo "========== TOOL DECORATORS =========="
rg -n "@tool|ToolSpec|Tool|register_tool|tool_registry" core examples

echo
echo "========== SUPERVISOR TOOLS =========="
sed -n '1,260p' core/engine/tools/supervisor_runtime.py

echo
echo "========== TOOL REGISTRY =========="
sed -n '1,260p' core/engine/runner/tool_registry.py

echo
echo "========== RUNTIME TOOLS =========="
sed -n '1,260p' core/engine/skills/runtime_tools.py

