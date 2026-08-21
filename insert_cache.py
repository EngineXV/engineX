# Insert cache lines at known line numbers, bottom-up to preserve indices

filepath = "core/engine/llm/litellm.py"
with open(filepath) as f:
    lines = f.readlines()

# Remove any prior cache lines (safety)
lines = [l for l in lines if "LLMResponseCache" not in l and "cache_entry" not in l and "self._cache" not in l]

# Blocks (with correct indentation)
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

# Insert bottom-up to keep line numbers stable.
# Indices are 0-based line numbers.
inserts = [
    (635, cache_store),          # acomplete store after line 635
    (586, cache_check),          # acomplete check after line 586
    (437, cache_store),          # complete store after line 437
    (376, cache_check),          # complete check after line 376
    (254, ["        self._cache = LLMResponseCache()  # LLM response cache\n"]),  # init before line 254
    (223, ["from engine.llm.cache import LLMResponseCache\n"]),  # import before line 223
]

# Sort by descending line number
inserts.sort(key=lambda x: -x[0])

for line_no, block in inserts:
    idx = line_no - 1  # convert to 0-based index
    for i, bline in enumerate(block):
        lines.insert(idx + i, bline)

with open(filepath, "w") as f:
    f.writelines(lines)
print("Insertion complete.")
