"""
Phase 1: Vector-Based Persona Matching (The Router)
Uses TF-IDF + cosine similarity (sklearn) — no model download required.
In production, swap TfidfVectorizer for a proper embedding model (OpenAI / HuggingFace).
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict

# ── Bot Personas ──────────────────────────────────────────────────────────────
BOT_PERSONAS = {
    "bot_a": {
        "name": "Tech Maximalist",
        "description": (
            "I believe AI and crypto will solve all human problems. "
            "I am highly optimistic about technology, Elon Musk, and space exploration. "
            "I dismiss regulatory concerns."
        ),
    },
    "bot_b": {
        "name": "Doomer / Skeptic",
        "description": (
            "I believe late-stage capitalism and tech monopolies are destroying society. "
            "I am highly critical of AI, social media, and billionaires. "
            "I value privacy and nature."
        ),
    },
    "bot_c": {
        "name": "Finance Bro",
        "description": (
            "I strictly care about markets, interest rates, trading algorithms, "
            "and making money. I speak in finance jargon and view everything "
            "through the lens of ROI."
        ),
    },
}


class PersonaVectorStore:
    """In-memory vector store using TF-IDF. Simulates ChromaDB / pgvector."""

    def __init__(self, personas: Dict):
        self.personas = personas
        self.ids = list(personas.keys())
        self.documents = [p["description"] for p in personas.values()]
        self.names = [p["name"] for p in personas.values()]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.persona_matrix = self.vectorizer.fit_transform(self.documents)
        print(f"[VectorStore] Indexed {len(self.ids)} personas.")

    def query(self, text: str) -> List[Dict]:
        query_vec = self.vectorizer.transform([text])
        similarities = cosine_similarity(query_vec, self.persona_matrix)[0]
        results = [
            {"bot_id": self.ids[i], "name": self.names[i], "similarity": float(round(s, 4))}
            for i, s in enumerate(similarities)
        ]
        return sorted(results, key=lambda x: x["similarity"], reverse=True)


def route_post_to_bots(post_content: str, store: PersonaVectorStore, threshold: float = 0.10) -> List[Dict]:
    """Routes a post to bots whose persona similarity exceeds threshold."""
    all_results = store.query(post_content)
    matched_bots = []
    print(f'\n[Router] Post: "{post_content}"')
    print(f"[Router] Scores (threshold >= {threshold}):")
    for r in all_results:
        status = "✅ MATCHED" if r["similarity"] >= threshold else "❌ skipped"
        print(f"  {r['bot_id']} ({r['name']}): {r['similarity']:.4f}  {status}")
        if r["similarity"] >= threshold:
            matched_bots.append(r)
    if not matched_bots:
        print("[Router] No bots matched.")
    else:
        print(f"[Router] Routed to: {[b['bot_id'] for b in matched_bots]}")
    return matched_bots


if __name__ == "__main__":
    store = PersonaVectorStore(BOT_PERSONAS)
    posts = [
        "OpenAI just released a new model that might replace junior developers.",
        "Bitcoin hits new all-time high amid regulatory ETF approvals.",
        "The Fed raised interest rates, crushing bond yields and tech valuations.",
        "Social media companies harvest your data and sell it to the highest bidder.",
        "SpaceX successfully lands Starship on the Moon.",
    ]
    for post in posts:
        route_post_to_bots(post, store, threshold=0.10)
        print()
