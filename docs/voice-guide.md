# Ooops Voice Guide

Living document. Every caption/text-generation step (Phase 5 and
onward) must read this file first — **and also [docs/ooops-context.md](ooops-context.md)**,
which owns product facts, positioning language, audience, and the hard
content-safety boundaries (fidelity/abuse/body-image/protected-characteristic
topics are off-limits regardless of how well they'd fit the voice
patterns below). This file is voice/tone only; that one is what's true
about the product and where the lines are. Update this file whenever
new voice-reference material comes in — the user is adding more
screenshots over time, not just the initial batch.

## Source material (as of 2026-09-16)

5 screenshots in `assets/voice-reference/`: other accounts' relatable/
humor text-posts (`mytherapistsays`, `duck.ingdone`, `fallinginsociety`,
`_thesweetoyin`, one unattributed marriage-disagreements post). These
are screenshots of *already-published IG/X posts in the target genre*,
not literal private couple-chat threads — that's the right kind of
reference for this pipeline, since the output is post captions, not raw
chat logs. Supplemented with general research on what reads as
authentic vs. AI-generated in relationship content (sources at bottom).

## Core voice principles

1. **Fragments over full sentences.** The reference posts almost never
   use a complete, grammatically tidy sentence for the punchline.
   "Fight. Fight loudly. Fight hard." not "I fight, and I fight loudly."
2. **A rhetorical opener, then a twist.** Several references open with
   a question or a setup ("What do you do when you have disagreements
   in your marriage?", "Life really said...") and land on something
   sharper or more ironic than the setup implied.
3. **Specific and concrete beats abstract.** "₹18,000 in 2 months" and
   "the same small stupid arguments" work because they're specific.
   "Relationships take work" doesn't work because it's not.
4. **Texting-register spelling, used naturally, not performed.**
   Lowercase starts, "u" / "ppl" / "abt" / "js" / "nd" — but only where
   it would actually show up in a real fast-typed caption. Don't sprinkle
   abbreviations decoratively into content that wouldn't naturally have
   them.
5. **A stray imperfection reads as more real, not less.** One reference
   post has a genuine typo ("resentmet") left uncorrected. Don't
   introduce fake typos on purpose, but don't over-polish either —
   contractions, run-ons, and trailing thoughts ("I don't even know how
   to explain it") are fine and often better than a clean finish.
6. **Self-aware, deadpan captions layered under the image text.** The
   on-image text carries the observation; the caption underneath often
   adds a dry, understated reaction rather than restating or explaining
   it ("Most hated person of my life for sure 😂").
7. **Escalation and repetition as structure**, not just word choice:
   short parallel lines that build ("You'll have... You'll get...
   You'll somehow...") before the twist.

## Ooops-specific angle

The above is genre voice. Layer the Ooops-specific hook on top: the
jar/accountability mechanic, LDR-specific detail (timezones, "good
morning"/"good night" as the same text, phone chargers before calls),
and the real origin story (a notepad, a jar, ₹50-per-"sorry"). Keep
Western/US-relatable once Phase 5 research starts (USD, US scenarios) —
this guide's structural rules carry over regardless of currency/market.

Example phrasings in-voice (illustrative, not to reuse verbatim):
- "you owe the jar. settle at month end."
- "we haven't had a single lingering fight since. the number makes it
  funny. the funny makes it something we talk about, not something that
  sits between us."
- "she was hungry." (a one-line non-answer as the punchline — commit to
  the bit, don't explain the joke)

**Hard rule, added 2026-09-17 after a batch failed this test:** every
post must land as a joke to someone who has never heard of Ooops and
never will click through — the app connection is a bonus for people
who *do* investigate, never a requirement to get the punchline. "jar"
can appear as a light, self-explanatory image (a jar = a mental tally
of pettiness — intuitive on its own, no app knowledge needed), but
never as a capital-J branded feature name the reader is assumed to
already recognize ("jar-worthy," "the Jar," "add it to the jar" as if
it's established shorthand). Test before shipping: read the post with
zero context — if the punchline only parses because you already know
Ooops has a jar feature, cut it or rewrite it as an implicit metaphor.
Use a jar reference **at most once per batch**, not as a recurring
tic — reaching for it repeatedly is what tips a post from "relatable
joke" into "thinly-veiled ad," which is the exact thing `app_promo`
gating exists to keep out of the relatable lane.

**Also check the existing queue before drafting** (`content_queue/
queue.json`) — a new batch repeating a format or angle already used
(e.g. another bullet-list "list of petty offenses" when one already
shipped) reads as reruns to anyone following the account, even if the
specific wording is new.

## CTA — always direct-engagement, always shareable

`cta` is a separate schema field from `caption` — it gets appended
into the final Instagram caption text at post time
(`post_to_instagram.py`'s `build_caption()`: caption → CTA → hashtags),
it is never rendered onto the image itself.

**Every CTA should give the reader something concrete to do that drives
either sharing or comments** (user directive, 2026-09-17) — not a vague
"let us know your thoughts." Favor:
- Tag-your-partner framing ("tag someone who...", "send this to the
  person who...") — this is the primary organic distribution mechanic
  for relatable-post content; a post someone tags their partner in or
  DMs to their partner reaches a second real person for free.
- Direct comment prompts ("comment your [specific thing]", "drop a
  [specific emoji] if...") — specific beats generic; "comment below"
  alone is weaker than "comment your countdown."

Most drafts already do this (see the 2026-09-17 batch — "tag your
co-defendant," "comment your countdown"), keep it that way rather than
defaulting to a flat statement with no ask.

## Cliché / AI-tell avoidance list — hard no

Cross-check every draft against this list. If a line could've been
written without reading a single real reference post, cut it.

- "communication is key"
- "opposites attract"
- "absence makes the heart grow fonder"
- "love at first sight" / "happily ever after"
- "never go to bed angry"
- Generic inspirational-quote cadence (centered, vague, could apply to
  any couple, no specific detail)
- Third-person distant narration ("Couples often find that...") —
  always first-person or direct-address ("you")
- Emoji used as filler/decoration rather than as a genuine beat in the
  line (one purposeful emoji > three decorative ones)
- A tidy, resolved ending where real relationship content usually trails
  off, contradicts itself, or lands on something unresolved/funny
  instead

## What to avoid structurally

- Full, grammatically complete sentences throughout — thins out the
  voice, reads as written-for-you rather than typed-in-the-moment
- Over-explaining the joke or the emotional beat after stating it
- Starting with "In a relationship, ..." or similar throat-clearing
- Perfectly even, "on-brand" polish with no rough edge anywhere

---

Sources for the general authenticity/cliché research behind this guide:
- [Ai Instagram Engagement Trends and Authenticity in 2026](https://en.cryptonomist.ch/2026/08/09/ai-instagram-engagement-authenticity/)
- [Instagram and the AI Content Era: Authenticity, Tools, and Strategy in 2026](https://expressocompany.com/instagram-ai-content-authenticity-2026/)
- [Will AI-Generated Content Hurt Your Reach in 2026?](https://getixgroup.com/blog/does-ai-content-hurt-social-reach-2026)
- [The Top Communications Clichés and How to Avoid Them](https://www.prnewsonline.com/cliches-communications-overused-phrases-writing/)
- [8 pieces of cliché relationship advice, according to psychologists](https://geediting.com/pieces-of-cliche-relationship-advice-that-are-actually-relevant-according-to-psychologists/)
