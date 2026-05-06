"""
Phase 2: Autonomous Content Engine (LangGraph)
A state machine where each bot:
  1. Decides what topic to post about
  2. Searches for real-world context (mocked)
  3. Drafts a 280-char opinionated post as strict JSON
"""

import os
import json
import re
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

load_dotenv()

# ── Bot Personas (system prompts) ─────────────────────────────────────────────
BOT_SYSTEM_PROMPTS = {
    "bot_a": (
        "You are Bot A, the Tech Maximalist. You are euphorically optimistic about AI, "
        "crypto, Elon Musk, and space exploration. You dismiss all regulatory concerns. "
        "Your tone is bold, visionary, and slightly arrogant."
    ),
    "bot_b": (
        "You are Bot B, the Doomer/Skeptic. You believe late-stage capitalism and tech "
        "monopolies are destroying democracy and the environment. You distrust billionaires, "
        "AI hype, and social media. Your tone is cynical and outraged."
    ),
    "bot_c": (
        "You are Bot C, the Finance Bro. You see everything through the lens of ROI, "
        "alpha generation, and market dynamics. You speak in finance jargon. "
        "Your tone is confident, analytical, and mildly condescending."
    ),
}

# ── Mock Search Tool ──────────────────────────────────────────────────────────
MOCK_NEWS_DB = {
    "ai":        "OpenAI launches GPT-5; analysts predict 40% of junior dev jobs at risk by 2026.",
    "crypto":    "Bitcoin hits $112K amid spot ETF inflows; Ethereum staking yields reach 6.2%.",
    "market":    "Fed holds rates at 5.25%; S&P 500 futures drop 1.8% on hawkish Powell comments.",
    "tech":      "Apple's market cap crosses $4T; Vision Pro 2 rumoured for Q4 launch.",
    "climate":   "Record heat kills 3,000 in India as coal plants run at 97% capacity.",
    "privacy":   "Meta fined €1.3B by EU for illegal US data transfers under GDPR.",
    "billionaire": "Elon Musk's net worth hits $400B; SpaceX valued at $350B after Starship success.",
    "space":     "SpaceX Starship successfully completes first crewed orbital mission.",
    "regulation": "EU AI Act enforcement begins; companies face fines up to 6% of global revenue.",
    "default":   "Markets volatile; tech sector leads mixed session amid earnings uncertainty.",
}

@tool
def mock_searxng_search(query: str) -> str:
    """Searches for recent news headlines relevant to the query."""
    query_lower = query.lower()
    for keyword, headline in MOCK_NEWS_DB.items():
        if keyword in query_lower:
            return f"HEADLINE: {headline}"
    return f"HEADLINE: {MOCK_NEWS_DB['default']}"


# ── LangGraph State ───────────────────────────────────────────────────────────
class PostState(TypedDict):
    bot_id: str
    persona: str
    search_query: str
    search_results: str
    post_json: dict          # final output


# ── LLM Setup ────────────────────────────────────────────────────────────────
def get_llm():
    """Returns a Groq LLM. Falls back instructions if key missing."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment. "
            "Add it to your .env file. Get a free key at https://console.groq.com"
        )
    return ChatGroq(model="llama3-8b-8192", temperature=0.8, api_key=api_key)


# ── Node 1: Decide Search Query ───────────────────────────────────────────────
def decide_search_node(state: PostState) -> PostState:
    """LLM decides what to post about and generates a search query."""
    llm = get_llm()
    persona = state["persona"]

    prompt = (
        f"{persona}\n\n"
        "It's time to write a social media post. First, decide what hot topic you want to "
        "post about today that fits your worldview. Then output ONLY a short search query "
        "(3-5 words) to find relevant news. No explanation. Just the query."
    )

    response = llm.invoke(prompt)
    query = response.content.strip().strip('"').strip("'")
    print(f"[{state['bot_id']}] Search query decided: '{query}'")

    return {**state, "search_query": query}


# ── Node 2: Web Search ────────────────────────────────────────────────────────
def web_search_node(state: PostState) -> PostState:
    """Executes the mock search tool."""
    result = mock_searxng_search.invoke({"query": state["search_query"]})
    print(f"[{state['bot_id']}] Search result: {result}")
    return {**state, "search_results": result}


# ── Node 3: Draft Post ────────────────────────────────────────────────────────
def draft_post_node(state: PostState) -> PostState:
    """
    LLM uses persona + search results to draft a 280-char post.
    Output must be strict JSON: {"bot_id": ..., "topic": ..., "post_content": ...}
    """
    llm = get_llm()
    persona = state["persona"]
    context = state["search_results"]
    bot_id = state["bot_id"]

    prompt = (
        f"{persona}\n\n"
        f"REAL-WORLD CONTEXT:\n{context}\n\n"
        "Write a highly opinionated social media post (max 280 characters) reacting to this news. "
        "Stay completely in character.\n\n"
        "You MUST respond with ONLY a valid JSON object in this exact format, nothing else:\n"
        '{"bot_id": "<bot_id>", "topic": "<2-4 word topic>", "post_content": "<your post here>"}\n\n'
        f"Replace <bot_id> with: {bot_id}"
    )

    response = llm.invoke(prompt)
    raw = response.content.strip()
    print(f"[{bot_id}] Raw LLM output: {raw}")

    # Safely parse JSON — strip markdown fences if present
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        post_json = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: extract JSON block from messy response
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        post_json = json.loads(match.group()) if match else {
            "bot_id": bot_id,
            "topic": "unknown",
            "post_content": clean[:280],
        }

    # Enforce 280-char limit on post_content
    if len(post_json.get("post_content", "")) > 280:
        post_json["post_content"] = post_json["post_content"][:277] + "..."

    print(f"[{bot_id}] Final JSON: {json.dumps(post_json, indent=2)}")
    return {**state, "post_json": post_json}


# ── Build Graph ───────────────────────────────────────────────────────────────
def build_content_graph() -> StateGraph:
    graph = StateGraph(PostState)
    graph.add_node("decide_search", decide_search_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("draft_post", draft_post_node)

    graph.set_entry_point("decide_search")
    graph.add_edge("decide_search", "web_search")
    graph.add_edge("web_search", "draft_post")
    graph.add_edge("draft_post", END)

    return graph.compile()


# ── Run for a Bot ─────────────────────────────────────────────────────────────
def generate_post(bot_id: str) -> dict:
    """Run the full LangGraph pipeline for a given bot."""
    if bot_id not in BOT_SYSTEM_PROMPTS:
        raise ValueError(f"Unknown bot_id: {bot_id}")

    app = build_content_graph()
    initial_state: PostState = {
        "bot_id": bot_id,
        "persona": BOT_SYSTEM_PROMPTS[bot_id],
        "search_query": "",
        "search_results": "",
        "post_json": {},
    }

    final_state = app.invoke(initial_state)
    return final_state["post_json"]


# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    for bot in ["bot_a", "bot_b", "bot_c"]:
        print(f"\n{'='*60}")
        print(f"Running content engine for {bot}...")
        print('='*60)
        result = generate_post(bot)
        print(f"\n✅ FINAL OUTPUT:\n{json.dumps(result, indent=2)}")
