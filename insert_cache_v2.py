filepath = "core/engine/llm/litellm.py"
with open(filepath) as f:
    lines = f.readlines()

# Remove any old cache lines
lines = [l for l in lines if "cache_entry" not in l and "self._cache" not in l and "LLMResponseCache" not in l]

def insert_before(lines, pattern, new_lines):
    for i, line in enumerate(lines):
        if pattern in line:
            for j, nl in enumerate(new_lines):
                lines.insert(i + j, nl)
            return True
    return False

def insert_after(lines, pattern, new_lines):
    for i, line in enumerate(lines):
        if pattern in line:
            for j, nl in enumerate(new_lines):
                lines.insert(i + 1 + j, nl)
            return True
    return False

cache_check = [
    "        # --- cache check ---\n",
    "        cache_entry = self._cache.get(\n",
    "            messages=messages, system=system, tools=tools, model=self.model,\n",
    "            max_tokens=max_tokens, response_format=response_format,\n",
    "            json_mode=json_mode, max_retries=max_retries,\n",
    "        )\n",
    "        if cache_entry:\n",
    "            return LLMResponse(\n",
    "                content=cache_entry.response.get('content', ''),\n",
    "                model=cache_entry.model,\n",
    "                input_tokens=cache_entry.input_tokens,\n",
    "                output_tokens=cache_entry.output_tokens,\n",
    "            )\n",
]

cache_store = [
    "        # --- store in cache ---\n",
    "        self._cache.set(\n",
    "            messages=messages, system=system, tools=tools, model=response.model,\n",
    "            response={'content': response.content},\n",
    "            input_tokens=response.input_tokens, output_tokens=response.output_tokens,\n",
    "            max_tokens=max_tokens, response_format=response_format,\n",
    "            json_mode=json_mode, max_retries=max_retries,\n",
    "        )\n",
]

# Import before class definition
insert_before(lines, "class LiteLLMProvider",
    ["from engine.llm.cache import LLMResponseCache\n"])

# Cache init before _completion_with_rate_limit_retry
insert_before(lines, "def _completion_with_rate_limit_retry(",
    ["        self._cache = LLMResponseCache()  # LLM response cache\n"])

# Cache check after docstring of complete()
insert_after(lines, '"""Generate a completion using LiteLLM"""',
    cache_check)

# Cache store after response = self._completion_with_rate_limit_retry(
insert_after(lines, "response = self._completion_with_rate_limit_retry(",
    cache_store)

# Cache check after docstring of acomplete()
insert_after(lines, '"""Async version of complete()',
    cache_check)

# Cache store after response = await self._acompletion_with_rate_limit_retry(
insert_after(lines, "response = await self._acompletion_with_rate_limit_retry(",
    cache_store)

with open(filepath, "w") as f:
    f.writelines(lines)
print("Insertion complete.")
