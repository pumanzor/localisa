"""
Localisa Router — decides which tools to use and orchestrates LLM + tools.

Two routing strategies:
1. Fast route: regex/keyword matching for obvious intents (IoT, greetings, time)
2. LLM route: ask the LLM to select tools via function-calling or text-based routing
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any

import httpx

from tool_registry import registry
from config import settings

log = logging.getLogger("localisa.router")


# --- Fast Route (pattern matching, no LLM needed) ---

def fast_route(query: str) -> Optional[List[Dict]]:
    """Detect obvious intents without calling the LLM."""
    q = query.lower().strip()

    # Normalize accents
    for old, new in {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n'}.items():
        q = q.replace(old, new)

    # Greetings → no tool needed
    greetings = ['hola', 'buenos dias', 'buenas tardes', 'buenas noches',
                 'como estas', 'que tal', 'hey', 'hi', 'hello']
    if any(q.startswith(g) or q == g for g in greetings):
        return [{"tool": "NONE", "args": {}}]

    # Time/date → get_datetime
    if any(x in q for x in ['que hora', 'hora actual', 'que dia', 'fecha de hoy', 'what time']):
        return [{"tool": "get_datetime", "args": {}}]

    # Weather
    if any(x in q for x in ['clima', 'tiempo hace', 'temperatura afuera', 'weather',
                              'va a llover', 'pronostico']):
        return [{"tool": "get_weather", "args": {"location": "auto"}}]

    # IoT device control
    action_on = ['enciende', 'prende', 'abre', 'activa', 'turn on']
    action_off = ['apaga', 'cierra', 'desactiva', 'turn off']

    device_words = ['ventilador', 'luz', 'luces', 'calefactor', 'porton',
                    'garage', 'piscina', 'patio', 'light', 'fan']

    has_device = any(d in q for d in device_words)
    has_on = any(a in q for a in action_on)
    has_off = any(a in q for a in action_off)

    if has_device and (has_on or has_off):
        # Extract device name (remove action words)
        device_q = query
        for w in action_on + action_off + ['por favor', 'el', 'la', 'del', 'de la', 'please', 'the']:
            device_q = re.sub(r'(?i)\b' + re.escape(w) + r'\b', '', device_q)
        device_q = ' '.join(device_q.split()).strip()
        action = "on" if has_on else "off"
        return [{"tool": "home_control", "args": {"device": device_q, "action": action}}]

    # Web search triggers
    web_triggers = ['busca en internet', 'busca en la web', 'search the web',
                    'busca online', 'google', 'noticias de']
    if any(t in q for t in web_triggers):
        search_q = query
        for t in web_triggers:
            search_q = search_q.replace(t, '').strip()
        return [{"tool": "web_search", "args": {"query": search_q or query}}]

    # Knowledge/general questions → no tool, let LLM answer directly
    knowledge_starters = [
        'que es', 'quien es', 'como funciona', 'que significa', 'explica',
        'define', 'describe', 'por que', 'cual es', 'calcula', 'cuanto es',
        'traduce', 'como se dice', 'what is', 'who is', 'how does', 'why',
    ]
    if any(q.startswith(p) for p in knowledge_starters):
        return [{"tool": "NONE", "args": {}}]

    return None  # Let LLM decide


# --- LLM-based Routing ---

async def llm_route(query: str) -> List[Dict]:
    """Ask the LLM to decide which tools to use."""
    tools_desc = registry.get_descriptions()

    prompt = f"""You are a tool router. Given the user's query, decide which tool(s) to call.
Available tools:
{tools_desc}

Rules:
- If the query is about documents, files, or knowledge the user uploaded, use search_documents.
- If the query needs current internet information, use web_search.
- If the query is about weather, use get_weather.
- If the query is about date/time, use get_datetime.
- If no tool is needed (general knowledge, conversation), respond with: NONE
- Respond ONLY with a JSON array of tool calls, e.g.: [{{"tool": "web_search", "args": {{"query": "latest news"}}}}]
- Or respond with: NONE

User query: {query}

Tool calls (JSON array or NONE):"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 256,
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()

                if content.upper() == "NONE" or "NONE" in content.upper():
                    return [{"tool": "NONE", "args": {}}]

                # Try to parse JSON
                # Find JSON array in response
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    calls = json.loads(match.group())
                    return calls if isinstance(calls, list) else [calls]

    except Exception as e:
        log.error(f"LLM routing failed: {e}")

    return [{"tool": "NONE", "args": {}}]


# --- Main Router ---

async def route_and_execute(query: str) -> Dict[str, Any]:
    """Route a query to tools and execute them. Returns tool results."""

    # 1. Try fast route
    tool_calls = fast_route(query)
    route_method = "fast"

    # 2. If fast route didn't match, ask LLM
    if tool_calls is None:
        tool_calls = await llm_route(query)
        route_method = "llm"

    log.info(f"Route ({route_method}): {query[:80]} → {[c['tool'] for c in tool_calls]}")

    # 3. Execute tools
    results = []
    for call in tool_calls:
        tool_name = call.get("tool", "NONE")
        args = call.get("args", {})

        if tool_name == "NONE":
            continue

        result = await registry.execute(tool_name, **args)
        results.append({
            "tool": tool_name,
            "args": args,
            "result": result,
        })

    return {
        "route_method": route_method,
        "tool_calls": tool_calls,
        "results": results,
        "has_tool_results": len(results) > 0,
    }
