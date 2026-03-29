"""Built-in tools for Localisa MVP."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx

from tool_registry import registry
from config import settings

log = logging.getLogger("localisa.router.tools")


# === RAG Search ===

async def search_documents(query: str, collection: str = None, top_k: int = 5) -> Dict[str, Any]:
    """Search your documents for relevant information."""
    try:
        payload = {"query": query, "top_k": top_k}
        if collection:
            payload["collection"] = collection
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{settings.rag_url}/search", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    formatted = []
                    for r in results[:top_k]:
                        source = r.get("metadata", {}).get("source", "unknown")
                        score = r.get("score", 0)
                        text = r.get("text", r.get("document", ""))[:500]
                        formatted.append(f"[{source}] (score: {score:.2f}): {text}")
                    return {"found": len(formatted), "results": "\n\n".join(formatted)}
                return {"found": 0, "results": "No relevant documents found."}
    except Exception as e:
        return {"error": str(e)}


# === Web Search ===

async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if results:
                formatted = []
                for r in results:
                    formatted.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
                return {"found": len(formatted), "results": "\n\n".join(formatted)}
            return {"found": 0, "results": "No results found."}
    except ImportError:
        return {"error": "duckduckgo_search not installed. pip install duckduckgo-search"}
    except Exception as e:
        return {"error": str(e)}


# === Time & Date ===

def get_datetime() -> Dict[str, Any]:
    """Get the current date and time."""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "formatted": now.strftime("%A %d de %B de %Y, %H:%M"),
    }


# === Weather ===

async def get_weather(location: str = "Santiago, Chile") -> Dict[str, Any]:
    """Get current weather for a location using Open-Meteo (free, no API key)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Geocode
            geo = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": location, "count": 1},
            )
            geo_data = geo.json()
            if not geo_data.get("results"):
                return {"error": f"Location not found: {location}"}

            lat = geo_data["results"][0]["latitude"]
            lon = geo_data["results"][0]["longitude"]
            name = geo_data["results"][0].get("name", location)

            # Weather
            weather = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                    "timezone": "auto",
                },
            )
            w = weather.json().get("current", {})

            weather_codes = {
                0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado",
                3: "Nublado", 45: "Niebla", 51: "Llovizna ligera", 53: "Llovizna",
                61: "Lluvia ligera", 63: "Lluvia", 65: "Lluvia fuerte",
                71: "Nieve ligera", 73: "Nieve", 80: "Chubascos", 95: "Tormenta",
            }

            return {
                "location": name,
                "temperature_c": w.get("temperature_2m"),
                "humidity_pct": w.get("relative_humidity_2m"),
                "wind_kmh": w.get("wind_speed_10m"),
                "condition": weather_codes.get(w.get("weather_code", 0), "Desconocido"),
            }
    except Exception as e:
        return {"error": str(e)}


# === Register all built-in tools ===

def register_builtin_tools():
    """Register all MVP tools."""

    registry.register(
        "search_documents",
        "Search uploaded documents and knowledge base for relevant information",
        search_documents,
        {
            "query": {"type": "string", "description": "What to search for"},
            "collection": {"type": "string", "description": "Specific collection to search (optional)"},
        },
    )

    registry.register(
        "web_search",
        "Search the internet for current information",
        web_search,
        {
            "query": {"type": "string", "description": "Search query"},
        },
    )

    registry.register(
        "get_datetime",
        "Get the current date and time",
        get_datetime,
        {},
    )

    registry.register(
        "get_weather",
        "Get current weather for a location",
        get_weather,
        {
            "location": {"type": "string", "description": "City or location name"},
        },
    )
