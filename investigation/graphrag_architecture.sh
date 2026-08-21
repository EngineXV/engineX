#!/usr/bin/env bash

echo "========== TOOL REGISTRATION =========="
rg -n "ToolSpec|tool_registry|register_tool|@tool|Tool\\(" core examples

echo
echo "========== TOOL EXECUTION =========="
rg -n "execute_tool|tool_call|ToolUse|ToolResult|call_tool|invoke_tool" core/engine

echo
echo "========== CONFIGURATION =========="
rg -n "get_engine_config|configuration.json|config" core/engine

echo
echo "========== PROVIDERS =========="
rg -n "LiteLLMProvider|LLMProvider|provider =" core/engine

echo
echo "========== RUNTIME =========="
rg -n "AgentRuntime|NodeContext|ExecutionContext|Runner|ctx\\." core/engine

