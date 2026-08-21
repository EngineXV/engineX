import re

filepath = "core/engine/llm/litellm.py"
with open(filepath) as f:
    content = f.read()

# ---- 1. Add self._cache in __init__ ----
init_match = re.search(r"(def __init__\(self[^)]*\).*?:.*?)(?=\n    def )", content, re.DOTALL)
if init_match:
    init_body = init_match.group(0)
    lines = init_body.splitlines()
    lines.append("        self._cache = LLMResponseCache()  # Added by patch")
    new_init = "\n".join(lines) + "\n"
    content = content.replace(init_body, new_init)
else:
    print("WARNING: Could not find __init__")

# ---- 2. Wrap complete() with cache check ----
complete_pat = r"(def complete\(self[^)]*\).*?->\s*LLMResponse:\s*\"\"\".*?\"\"\"\s*)(.*?)(?=\n    def )"
match_c = re.search(complete_pat, content, re.DOTALL)
if match_c:
    sig, body = match_c.groups()
    # find the return variable name
    ret_var = re.search(r"^\s*return\s+(\w+)", body, re.MULTILINE)
    result = ret_var.group(1) if ret_var else "result"
    wrapped = (
        "        # --- cache check ---\n"
        "        cache_entry = self._cache.get(\n"
        "            messages=messages, system=system, tools=tools, model=self.model,\n"
        "            max_tokens=max_tokens, response_format=response_format,\n"
        "            json_mode=json_mode, max_retries=max_retries,\n"
        "        )\n"
        "        if cache_entry:\n"
        "            return LLMResponse(\n"
        "                content=cache_entry.response.get('content', ''),\n"
        "                model=cache_entry.model,\n"
        "                input_tokens=cache_entry.input_tokens,\n"
        "                output_tokens=cache_entry.output_tokens,\n"
        "            )\n"
        + body +
        f"\n        # --- store in cache ---\n"
        f"        self._cache.set(\n"
        f"            messages=messages, system=system, tools=tools, model={result}.model,\n"
        f"            response={{'content': {result}.content}},\n"
        f"            input_tokens={result}.input_tokens, output_tokens={result}.output_tokens,\n"
        f"            max_tokens=max_tokens, response_format=response_format,\n"
        f"            json_mode=json_mode, max_retries=max_retries,\n"
        f"        )\n"
    )
    content = content.replace(body, wrapped)
else:
    print("WARNING: Could not find complete()")

# ---- 3. Wrap acomplete() similarly ----
acomplete_pat = r"(async def acomplete\(self[^)]*\).*?->\s*\"LLMResponse\":\s*\"\"\".*?\"\"\"\s*)(.*?)(?=\n    async def )"
match_a = re.search(acomplete_pat, content, re.DOTALL)
if match_a:
    sig_a, body_a = match_a.groups()
    ret_var_a = re.search(r"^\s*return\s+(\w+)", body_a, re.MULTILINE)
    result_a = ret_var_a.group(1) if ret_var_a else "result"
    wrapped_a = (
        "        # --- cache check ---\n"
        "        cache_entry = self._cache.get(\n"
        "            messages=messages, system=system, tools=tools, model=self.model,\n"
        "            max_tokens=max_tokens, response_format=response_format,\n"
        "            json_mode=json_mode, max_retries=max_retries,\n"
        "        )\n"
        "        if cache_entry:\n"
        "            return LLMResponse(\n"
        "                content=cache_entry.response.get('content', ''),\n"
        "                model=cache_entry.model,\n"
        "                input_tokens=cache_entry.input_tokens,\n"
        "                output_tokens=cache_entry.output_tokens,\n"
        "            )\n"
        + body_a +
        f"\n        # --- store in cache ---\n"
        f"        self._cache.set(\n"
        f"            messages=messages, system=system, tools=tools, model={result_a}.model,\n"
        f"            response={{'content': {result_a}.content}},\n"
        f"            input_tokens={result_a}.input_tokens, output_tokens={result_a}.output_tokens,\n"
        f"            max_tokens=max_tokens, response_format=response_format,\n"
        f"            json_mode=json_mode, max_retries=max_retries,\n"
        f"        )\n"
    )
    content = content.replace(body_a, wrapped_a)
else:
    print("WARNING: Could not find acomplete()")

with open(filepath, "w") as f:
    f.write(content)
print("Patched successfully.")
