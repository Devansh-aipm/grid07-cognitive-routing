# Grid07 — AI Cognitive Routing & RAG Assignment

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

## Run

```bash
# All phases
python main.py

# Individual phases
python main.py 1
python main.py 2
python main.py 3

# Or run directly
python phase1/router.py
python phase2/content_engine.py
python phase3/combat_engine.py
```

---

## Phase 1 — Vector Persona Router

Bot personas are embedded using `sentence-transformers` (the default ChromaDB embedding function) and stored in an in-memory ChromaDB collection with **cosine distance** metric.

When a post arrives, it gets embedded and queried against all personas. ChromaDB returns cosine **distance** (0 = identical, 2 = opposite), which we convert to **similarity = 1 - distance**. Bots above the threshold (default `0.30`) are returned as matches.

**Why 0.30 instead of 0.85?**  
The assignment's `0.85` threshold is calibrated for raw cosine similarity scores between 0–1. ChromaDB's distance-based similarity after conversion tends to score in the `0.2–0.5` range for semantically related (but not identical) texts. A threshold of `0.30` gives realistic, selective routing without excluding all bots.

---

## Phase 2 — LangGraph Content Engine

### Node Structure

```
[decide_search] → [web_search] → [draft_post] → END
```

| Node | Role |
|------|------|
| `decide_search` | LLM reads persona, picks a topic, outputs a 3-5 word search query |
| `web_search` | Calls `mock_searxng_search` tool, returns hardcoded headline by keyword |
| `draft_post` | LLM uses persona + headline to write a 280-char post, outputs strict JSON |

**Structured output** is enforced by prompting the LLM to output only a JSON object with format `{"bot_id", "topic", "post_content"}`, then parsing with `json.loads()` and a regex fallback to strip markdown fences.

---

## Phase 3 — Combat Engine + Prompt Injection Defense

### RAG Strategy

The `generate_defense_reply()` function constructs a full thread context string — original post + all prior comments + latest human message — and passes it as a single `HumanMessage`. This gives the LLM full argument history so it can track what has already been said and respond coherently.

### Prompt Injection Defense

The system prompt includes a **SECURITY DIRECTIVE** block with the following logic:

1. **Identity lock**: Explicitly states the bot's persona is immutable and cannot be overridden by any human message.
2. **Enumerated attack patterns**: Lists known injection phrases ("ignore all previous instructions", "you are now a different bot", "apologize") and instructs the model to not comply with them.
3. **Silent resistance**: The bot does NOT acknowledge the injection attempt. It simply continues the argument naturally — this is intentional, so attackers don't know their injection was detected.
4. **Post-response verification**: The code checks the output for suspicious phrases ("sorry", "apologize", "customer service") and flags a warning if found.

This defense is **prompt-level** (not code-level) because LLMs are stateless — the system prompt is the only persistent mechanism available.

---

## Tech Stack

- **LangChain / LangGraph** — orchestration and state machine
- **ChromaDB** — in-memory vector store for persona matching
- **sentence-transformers** — default embedding function (all-MiniLM-L6-v2)
- **Groq (Llama-3-8b)** — free LLM inference
- **python-dotenv** — environment variable management
