import sys

filepath = 'core/engine/llm/litellm.py'
with open(filepath) as f:
    lines = f.readlines()

output = []
in_complete = False
in_acomplete = False
seen_init_cache = False
seen_import = False

# Blocks to insert (indentation matches the methods)
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
    # 1. Insert import before the class definition
    if not seen_import and line.startswith('class LiteLLMProvider'):
        output.append('from engine.llm.cache import LLMResponseCache\n')
        seen_import = True

    # 2. Insert cache init just before 'def _completion_with_rate_limit_retry('
    if not seen_init_cache and 'def _completion_with_rate_limit_retry(' in line:
        output.append('        self._cache = LLMResponseCache()  # LLM response cache\n')
        seen_init_cache = True

    # Detect method boundaries
    if 'def complete(self' in line:
        in_complete = True
    elif 'def acomplete(self' in line:
        in_acomplete = True
    elif in_complete and ('def ' in line or 'class ' in line):
        in_complete = False
    elif in_acomplete and ('def ' in line or 'class ' in line):
        in_acomplete = False

    # 3. Insert cache check after the docstring of complete()
    if in_complete and line.strip().startswith('"""Generate a completion using LiteLLM"""'):
        output.append(line)
        output.extend(cache_check)
        continue

    # 4. Insert cache store after 'response = self._completion_with_rate_limit_retry(' in complete()
    if in_complete and 'response = self._completion_with_rate_limit_retry(' in line:
        output.append(line)
        output.extend(cache_store)
        continue

    # 5. Insert cache check after the docstring of acomplete()
    if in_acomplete and line.strip().startswith('"""Async version of complete()'):
        output.append(line)
        output.extend(cache_check)
        continue

    # 6. Insert cache store after 'response = await self._completion_with_rate_limit_retry(' in acomplete()
    if in_acomplete and 'response = await self._completion_with_rate_limit_retry(' in line:
        output.append(line)
        output.extend(cache_store)
        continue

    output.append(line)

with open(filepath, 'w') as f:
    f.writelines(output)
print('Patched successfully.')
