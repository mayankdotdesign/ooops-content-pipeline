# Batch 3 plan: text-exchange reels (draft for review)

Status: **DRAFT. Nothing is rendered or queued.** This plan includes the scripts, captions,
Veo prompts and schedule. Approve or edit it first; I build the templates only after you say go.

## 1. Goal and how we judge it

Batches 1 and 2 reached about 1,500 non-follower views in total, with 0 real shares, saves,
comments or follows. Views are no longer the problem; getting people to act is.

| Metric | Role | Target for this batch |
|---|---|---|
| Real shares per 100 views | **primary** | at least 1 reel with a non-owner share; stretch: 1% share rate |
| Saves, non-owner comments | secondary | any |
| Views | guardrail only | stay within the ~100-200 per reel baseline |
| In-app retention at 1s / 3s | diagnostic | better than batch 2 (~50% / ~20-33%) |

Research behind the format: `docs/research/2026-10-02-text-exchange-format.md`.

## 2. Format and workflow

- **All 10 items are reels.** You upload and schedule them in the Instagram app and add trending audio there.
- **I render the videos silent** (no baked music), so the trending audio you pick is the only sound.
- **Text-exchange reels** (8 of the 10) show the whole conversation from the first frame,
  with no word-by-word reveal. A very slow 100%→103% zoom keeps the frame from being
  completely static. Length is reading time plus a hold (6-10s); exact lengths are below.
- **Veo reels** (2): you generate an 8s clip in Flow using the prompts below and send it to me.
  I add the text and render it, and you upload it.
- **No Ooops branding** anywhere on screen or in captions.
- **Caption style:** a short reaction plus 3-4 hashtags. No questions and no "send this to…",
  since that CTA got 0 shares in batch 2. Nothing claims the texts are real.

### Text-exchange visual spec

- iMessage-style conversation, 1080×1920, kept inside the Reels safe zone (x 80-900, y 260-1740).
- Header: contact name (and an emoji) as in the scripts below. No avatar photo and no real names.
- Bubbles: blue (#0A84FF) on the right for "me" (the phone owner), grey on the left for the other person.
  System font look (SF-style), about 44px text.
- The mode alternates light/dark as listed per item.
- Small grey timestamp above the first bubble (e.g. "Today 9:41 PM") for realism.
- No typing indicator, no animations, no read receipts.

### Who does what

| Step | Who |
|---|---|
| Approve this plan (scripts, captions, prompts, schedule) | you |
| Generate Veo A and Veo B in Flow and send me the mp4s | you |
| Build the text-exchange and Veo-overlay templates, then render all 10 (silent) | me |
| Review all 10 rendered mp4s | you |
| Upload, add trending audio, and schedule in the IG app at the times below | you |
| Tell me which audio you used for each reel (so we can log it) | you |
| Link the posted reels to our tracker and report the results | me |

### Pipeline changes (built only after you say go)

1. New Remotion compositions: `TextExchangeReel` and `VeoOverlayReel` (silent output).
2. Renders go to `content_queue/manual/<id>.mp4`, **not** `content_queue/rendered/`, so the
   23:00/03:00 auto-poster can never pick them up.
3. Queue entries with `stage: "manual"` so the batch is logged next to the others.
4. `scripts/link_manual_posts.py`: after you post, it matches your reels by post time
   (via `/me/media`) and fills in `ig_media_id`. The daily tracker then collects their
   insights like any other post.

## 3. Schedule

Since we're now targeting both markets, I'd change the slots:

| Slot | UTC | India (IST) | US East (ET) | Why |
|---|---|---|---|---|
| **S-IN** | 14:30 | 20:00 | 10:30 | India evening; 53-66% of our viewers are there |
| **S-US** | 23:00 | 04:30 (next day) | 19:00 | US evening (our usual 23:00 slot) |

The slot made no measurable difference in batch 2, so moving one slot to India's evening costs us nothing.
Each pair that shares a joke (Veo vs text exchange) is split across the two slots so neither format gets the better slot.

Day 1 is the day after you approve the rendered files.

| Day | S-IN 14:30 UTC | S-US 23:00 UTC |
|---|---|---|
| 1 | #29 fries | #38 Veo A "leaving now" |
| 2 | #31 anywhere | #32 blanket |
| 3 | #30 on my way | #34 one episode |
| 4 | #37 Veo B "blanket" | #33 getting ahead of it |
| 5 | #35 first one | #36 last dumpling |

## 4. The 8 text-exchange reels

"me" is the phone owner, shown in blue. Most are from her phone, since 62-81% of our viewers are women.

### #29 "fries": light mode, her phone, contact **him 🍟**, 7s
```
me:  did you eat my fries
him: no
me:  there were 11. there are 4.
him: i was protecting you
me:  from what
him: fries
```
Caption: `the math isn't mathing 🍟`
Hashtags: `#couplememes #relationshipmemes #boyfriend #relatable`

### #30 "on my way": dark mode, her phone, contact **him**, 7s (paired with Veo A #38)
```
me:  are you leaving?
him: leaving now
me:  you said that 40 minutes ago
him: and i meant it emotionally
```
Caption: `"leaving now" is a state of mind`
Hashtags: `#couplememes #relationshipmemes #boyfriend #relatable`

### #31 "anywhere": light mode, his phone, contact **her ❤️**, 10s
```
me:  where do you want to eat
her: anywhere idc
me:  pizza?
her: no
me:  sushi?
her: hmm no
me:  ok i booked the thai place you mentioned once in march
her: i'm going to cry in the thai place
```
Caption: `he was listening in march 😭`
Hashtags: `#couplememes #relationshipgoals #girlfriend #relatable`

### #32 "blanket": dark mode, her phone, contact **him**, 8s (paired with Veo B #37)
```
me:  are you awake
him: yes why
me:  you have all the blanket
him: we're in the same bed
me:  i'm not saying it out loud. that's how you know it's serious
```
Caption: `this is a formal complaint`
Hashtags: `#couplememes #relationshipmemes #boyfriend #relatable`

### #33 "getting ahead of it": light mode, his phone, contact **her**, 9s
```
me:  i'm sorry
her: for what?
me:  no idea. you went quiet at dinner and i'm getting ahead of it
her: i was quiet because the waiter was rude
her: but i accept. keep going.
```
Caption: `pre-emptive apologies are a love language`
Hashtags: `#couplememes #relationshipmemes #girlfriend #relatable`

### #34 "one episode": dark mode, his phone, contact **her 📺**, 8s
```
me:  watched one episode without you
her: …
her: which one
me:  the next one
her: so you've chosen violence
me:  i also watched the one after
```
Caption: `he chose violence`
Hashtags: `#couplememes #relationshipmemes #girlfriend #relatable`

### #35 "first one": light mode, her phone, contact **him 🌙**, 9s (long-distance)
```
him: good morning ☀️
me:  it's 11pm here
him: i know. i set an alarm so i'd be the first one to say it tomorrow
me:  that's the most annoying romantic thing anyone's ever done
```
Caption: `long distance is a time zone math problem`
Hashtags: `#longdistancerelationship #ldr #couplememes #relatable`

### #36 "last dumpling": dark mode, his phone, contact **her 🥟**, 8s
```
her: do you want the last dumpling
me:  no you have it
her: are you sure
me:  yes
her: ok i ate it
me:  i was going to say yes the third time
```
Caption: `the third ask is the real ask`
Hashtags: `#couplememes #relationshipmemes #foodie #relatable`

## 5. The 2 Veo reels (8s each)

Every Veo prompt follows the same realism rules: a phone-camera look (not "cinematic"), a tidy real
home, explicit grooming and clothing, and an "Avoid" list. Generate with ambient sound only; you'll add
trending audio at upload. If the first take looks off, send me a screenshot and I'll adjust the prompt.

### #38 Veo A, "leaving now" (S-US, Day 1; same joke as #30)

**Text overlay** (top safe zone, two iMessage bubbles over the video, visible from frame 0):
```
her: are you leaving?
him: leaving now 🙂
```

**Prompt:**
> Vertical 9:16 smartphone video, handheld by a roommate standing in a doorway, slight natural hand movement, eye-level framing. A well-groomed man around 28 sits relaxed on a clean light-grey sofa in a tidy, modern apartment living room. He is clearly dressed for a dinner date: a crisp, well-fitted navy button-down shirt tucked into dark chinos, a brown leather belt, a silver watch, freshly styled short hair, a neatly trimmed short beard, clean-shaven neck. A navy blazer and car keys rest neatly on the sofa armrest beside him. His left foot wears a black dress sock and a polished brown shoe sits on the floor next to it; his right foot is bare and he is holding the second black sock loosely in his right hand. He is watching TV off-screen with a calm, amused expression, the TV glow subtly lighting his face. His phone buzzes on the sofa; he glances at it, types a two-word reply with his thumb while half-smiling, sets the phone down screen-down, and keeps watching TV, still holding the sock. Warm evening light from a floor lamp, a potted plant and a framed print in the background, the room tidy and real, like an actual rented apartment. Natural skin texture, realistic phone-camera colour, slight sensor noise, auto-exposure. Ambient room sound and faint TV audio only, no music, no dialogue.
>
> Avoid: messy or dirty room, torn or stained furniture, clutter, unkempt hair, heavy stubble, tired or sad expression, pyjamas, t-shirt, sweatpants, cinematic lighting, film look, shallow depth of field.

Caption: `"leaving now" (one sock in)`
Hashtags: `#couplememes #relationshipmemes #boyfriend #relatable`

### #37 Veo B, "blanket" (S-IN, Day 4; same joke as #32)

**Text overlay** (top safe zone, plain text on a soft dark band, visible from frame 0):
```
he has 90% of the blanket
and i'm the one who "moves too much"
```

**Prompt:**
> Vertical 9:16 smartphone video, handheld, filmed by a woman around 27 lying on her side of a bed at night, phone held at arm's length so we see her and the bed. A clean, cosy bedroom: matching sage-green linen bedding, two neat pillows on her side, a bedside lamp with warm low light, a book and a glass of water on the bedside table. She wears a soft oversized cotton t-shirt, hair in a neat loose bun, natural fresh-faced look. Next to her, a man is asleep on his side, wrapped tightly in nearly the entire duvet like a burrito; only a thin corner of the duvet covers her legs. She gives the duvet one small tug; it doesn't move. She turns to the camera with a tired, deadpan, unimpressed expression and holds the look for two seconds. Realistic low-light phone footage, slight grain, natural skin texture, real-home feel. Ambient room sound and faint breathing only, no music, no dialogue.
>
> Avoid: messy or dirty room, stained bedding, clutter, dishevelled hair, heavy makeup, cinematic lighting, film look, shallow depth of field.

Caption: `filing a formal complaint`
Hashtags: `#couplememes #relationshipmemes #boyfriend #relatable`

**AI label:** Meta's rules ask creators to label realistic AI video. Ticking "AI info" at upload
for #37 and #38 is your call; I'd tick it.

## 6. What this batch can and can't tell us

- **Can:** whether text exchanges with trending audio get any real shares at all, how they compare to
  the batch 2 baseline, and whether a real-looking scene (Veo) gets more shares than the same joke as a text exchange.
- **Can't:** the effect of trending audio vs our music on its own, because every reel in this batch uses trending audio.
  That's an accepted trade-off of posting all 10 manually.
- **Reading the results:** n=10, so a single share is a signal, not proof. I'll report each reel's numbers next to its
  in-app retention (1s and 3s); screenshots of the Overview tab after 48h are enough.

## 7. Open decisions

1. Approve or edit the 8 scripts and 2 Veo concepts.
2. Slots: switch to S-IN 14:30 UTC + S-US 23:00 UTC (recommended), or keep 23:00 + 03:00?
3. Go for me to build the templates and the manual-post pipeline changes in section 2.
