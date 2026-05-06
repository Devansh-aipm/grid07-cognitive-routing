"""
main.py — Grid07 AI Assignment
Runs all three phases sequentially and logs output.
"""

import sys
import os

# Add parent to path so phases can import each other if needed
sys.path.insert(0, os.path.dirname(__file__))

def run_phase1():
    print("\n" + "🔷 " * 20)
    print("PHASE 1: VECTOR-BASED PERSONA ROUTING")
    print("🔷 " * 20)
    from phase1.router import build_persona_store, route_post_to_bots

    store = build_persona_store()

    test_posts = [
        "OpenAI just released a new model that might replace junior developers.",
        "Bitcoin hits new all-time high amid regulatory ETF approvals.",
        "The Fed raised interest rates, crushing tech valuations.",
        "Social media companies are harvesting your data without consent.",
    ]

    for post in test_posts:
        route_post_to_bots(post, store, threshold=0.30)
        print()

def run_phase2():
    print("\n" + "🔶 " * 20)
    print("PHASE 2: AUTONOMOUS CONTENT ENGINE (LangGraph)")
    print("🔶 " * 20)
    import json
    from phase2.content_engine import generate_post

    for bot_id in ["bot_a", "bot_b", "bot_c"]:
        print(f"\n--- Generating post for {bot_id} ---")
        result = generate_post(bot_id)
        print(f"✅ FINAL: {json.dumps(result, indent=2)}")

def run_phase3():
    print("\n" + "🔴 " * 20)
    print("PHASE 3: COMBAT ENGINE — RAG + INJECTION DEFENSE")
    print("🔴 " * 20)

    # Import and run phase3 as a script
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "combat_engine",
        os.path.join(os.path.dirname(__file__), "phase3", "combat_engine.py")
    )
    mod = importlib.util.load_from_spec(spec)
    spec.loader.exec_module(mod)


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"

    if phase in ("1", "all"):
        run_phase1()

    if phase in ("2", "all"):
        try:
            run_phase2()
        except ValueError as e:
            print(f"⚠️  Phase 2 skipped: {e}")

    if phase in ("3", "all"):
        try:
            run_phase3()
        except ValueError as e:
            print(f"⚠️  Phase 3 skipped: {e}")

    print("\n\n✅ All phases complete.")
