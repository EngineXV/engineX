filepath = "core/engine/llm/litellm.py"
with open(filepath) as f:
    lines = f.readlines()

# Remove any previously added cache lines (safety)
lines = [l for l in lines if "LLMResponseCache" not in l and "cache_entry" not in l and "self._cache" not in l]

output = []
in_complete = False
in_acomplete = False
seen_init = False
import_inserted = False

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

for line in lines:
    # ---- 1. Import before class ----
    if not import_inserted and line.startswith("class LiteLLMProvider"):
        output.append("from engine.llm.cache import LLMResponseCache\n")
        import_inserted = True

    # ---- 2. Cache init before `_completion_with_rate_limit_retry` ----
    if not seen_init and "def _completion_with_rate_limit_retry(" in line:
        output.append("        self._cache = LLMResponseCache()  # LLM response cache\n")
        seen_init = True

    # Track method boundaries
    if "def complete(self" in line:
        in_complete = True
        in_acomplete = False
    elif "def acomplete(self" in line:
        in_complete = False
        in_acomplete = True
    elif line.strip().startswith("def ") and in_complete:
        in_complete = False
    elif line.strip().startswith("def ") and in_acomplete:
        in_acomplete = False

    # ---- 3. Cache check after docstring of complete() ----
    if in_complete and line.strip().startswith('"""Generate a completion using LiteLLM"""'):
        output.append(line)
        output.extend(cache_check)
        continue

    # ---- 4. Cache store after 'response = self._completion_with_rate_limit_retry(' ----
    if in_complete and "response = self._completion_with_rate_limit_retry(" in line:
        output.append(line)
        output.extend(cache_store)
        continue

    # ---- 5. Cache check after docstring of acomplete() ----
    if in_acomplete and line.strip().startswith('"""Async version of complete()'):
        output.append(line)
        output.extend(cache_check)
        continue

    # ---- 6. Cache store after 'response = await self._completion_with_rate_limit_retry(' ----
    if in_acomplete and "response = await self._completion_with_rate_limit_retry(" in line:
        output.append(line)
        output.extend(cache_store)
        continue

    output.append(line)

with open("core/engine/llm/litellm_cached.py", "w") as f:
    f.writelines(output)
print("Generated core/engine/llm/litellm_cached.py")
