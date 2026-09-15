"""
Ooops content idea generator.

Run this weekly (via Claude Code, manually invoked or on a schedule).
It outputs a queue of post concepts to content_queue/queue.json.

This script does NOT call any paid API. It's meant to be run
*by Claude* (via Claude Code) reading this file's CONTENT_ANGLES
and past performance data, then writing new entries into
content_queue/queue.json itself — no external LLM API key needed.

Usage as a human-in-the-loop tool:
  1. Open this file in Claude Code
  2. Ask Claude: "generate this week's 7 post ideas using
     generate_ideas.py's angles and last week's performance.json"
  3. Claude appends structured entries to content_queue/queue.json
"""

import json
import os
from datetime import datetime, timedelta

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
PERF_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "performance.json")

# Content pillars — Claude should rotate through these, weighting
# toward whatever performance.json shows is working best.
CONTENT_ANGLES = [
    "jar_entry",       # "Things that'd cost him ₹200 in the jar"
    "ldr_pain",        # relatable long-distance specific frustration
    "couple_debate",   # "is X a ₹500 offense or ₹1000 offense" polls
    "origin_story",    # spin-offs of the real notepad -> ₹18K story
    "relatable_text",  # generic relationship text-post, jar-adjacent
]

def load_queue():
    if os.path.exists(QUEUE_PATH):
        with open(QUEUE_PATH) as f:
            return json.load(f)
    return []

def save_queue(queue):
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)

def add_idea(text, angle, scheduled_for=None):
    queue = load_queue()
    queue.append({
        "id": len(queue) + 1,
        "text": text,
        "angle": angle,
        "status": "queued",  # queued -> rendered -> posted
        "scheduled_for": scheduled_for,
        "created_at": datetime.utcnow().isoformat(),
    })
    save_queue(queue)
    return queue[-1]

if __name__ == "__main__":
    # Example seed — Claude will replace/extend this each week
    # with fresh, non-repeating concepts.
    print("Current queue:")
    print(json.dumps(load_queue(), indent=2))
    print(f"\nAngles to rotate through: {CONTENT_ANGLES}")
    print("\nAsk Claude Code: 'generate 7 new post ideas for next week'")
