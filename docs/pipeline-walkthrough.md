# How the pipeline actually works — a plain-language walkthrough

Four automated jobs run in the background (GitHub Actions, on
schedules), plus Claude doing the actual thinking/writing work when
something needs judgment. Nothing posts to Instagram without you
approving it twice — once on the words, once on the actual image.

## A realistic week, step by step

**Monday — Claude drafts a new batch.** Phase 5 kicks off: Claude goes
and reads Reddit/Instagram for real, relevant posts, checks what's
already worked (`content_queue/performance.json`), and writes ~14 new
posts — hook text, caption, hashtags, CTA — following
`docs/voice-guide.md` and the hard content rules in
`docs/ooops-context.md` (no fidelity/abuse topics, no overclaiming the
app exists yet, etc). Every post gets a note on exactly which real post
inspired it (`source_note`). Committed to `content_queue/queue.json` as
`"drafted"`.

**Within ~20 minutes — content review sheet appears.** The automation
(`scripts/review_cycle.py`, on a cron) notices drafted posts sitting
there, writes one row per post into a fresh tab in the Google Sheet
(`content-2026-09-22`, say), and emails a notification with a link.
Each row has the text, caption, hashtags, CTA — no images yet, nothing's
rendered.

**You review the words.** Go through the rows, mark each row's
**Content Status**: Approved / Need Change / Rejected, with a comment
in **Content Comments** wherever something needs to change.

**Each row processes independently, as soon as it's filled in** — you
don't have to finish every row before any of them move:
- **Rejected** rows are dropped from the queue entirely.
- **Need Change** rows pause — Claude reads your comment, fixes the
  actual post, and clears the comment to signal it's done. The
  automation pushes the fix back into that *same row* and clears its
  status so you can look again. Can loop a few times.
- **Approved** rows move to "content approved" — but don't render yet.

**Rendering only starts once the WHOLE batch's content is approved** —
this is deliberate (per your request): no image gets generated until
every post in the batch is either approved or dropped, so no render
effort is wasted on copy that might still change. Once that's true, the
automation renders every approved post's actual Instagram-ready image
and fills in an **Image Link(s)** column on the *same rows, same tab* —
no new tab, just new columns appear. Another email tells you it's ready.

**You review the visuals.** Click the image links, mark **Visual
Status** / **Visual Comments** the same way, on the same rows. Same
loop: Need Change → Claude fixes and re-renders → same row updates;
Rejected → dropped; Approved → that post is now `"queued"`, fully done,
waiting to post.

**Posting happens on its own schedule.** `.github/workflows/daily-post.yml`
looks for `"queued"` posts daily and publishes to Instagram — currently
1/day, no app-promo posts, no carousels, per what you asked for a few
weeks ago (docs/build-plan.md, 2026-09-17). It pulls the caption and the
already-approved image; nothing new gets generated at post time.

**After it's live, a third job tracks performance.**
`.github/workflows/track-engagement.yml` pulls real Instagram Insights
(reach, likes, saves) daily into `content_queue/performance.json`,
which Claude reads the next time it drafts a batch — so research and
writing get better informed by what's actually working over time.

## Where Claude comes in vs. what's fully automatic

| Always needs Claude | Fully automatic |
|---|---|
| Drafting a new weekly batch (Phase 5 research + writing) | Writing the review sheet, emailing notifications |
| Fixing a "Need Change" item (content or visual) | Checking the sheet for filled-in rows |
| Any policy/design decisions (e.g. "no app_promo for a few weeks") | Rendering approved posts |
| | Posting queued items to Instagram |
| | Pulling engagement data |

## The one Google Sheet

One spreadsheet (`GOOGLE_SHEET_ID`), one tab per weekly batch, named by
the date it started (e.g. `content-2026-09-22`). That tab carries the
batch through its *entire* lifecycle — columns:

`Post ID | Content/slide text | Caption | Hashtags | CTA | Post type | Content Status | Content Comments | Image Link(s) | Visual Status | Visual Comments`

The first six columns are written once, when the batch starts. Content
Status/Comments are yours to fill in during content review. Image
Link(s) gets filled in automatically once the whole batch's content is
approved. Visual Status/Comments are yours to fill in during visual
review. A new tab only ever appears for a genuinely new weekly batch —
revision rounds reuse the same tab, same rows.
