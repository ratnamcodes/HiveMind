# HiveMind Launch Video — Storyboard (hero cut, ~100s, 1920×1080@30)

Source: `public/video/demo.mp4` (298.16s, 1440×900@25, no audio).
Layout: dark stage `#0b0d10` + faint amber glow; recording in a rounded, shadowed window; word-pop captions lower-center; amber stat chips as pattern interrupts.

| # | Beat | ~Video time | Source segment | Treatment | VO |
|---|------|------------|----------------|-----------|----|
| 0 | Cold open | 0:00–0:04 | t=5–8 (SEV1 channel appears) | snap-zoom on header `# inc-checkout-r-7bce9b SEV1`; red pulse; alarm tick SFX | "This is a real SEV-1…" |
| 1 | Problem | 0:04–0:12 | t=6–10 (incident brief) | zoom brief card → IMPACT row; 2 cuts | "Normally? A human gets paged…" |
| 2 | Reveal (stopdown) | 0:12–0:18 | — title card | music cuts → riser → HiveMark + "HiveMind" slams on downbeat + braam | "HiveMind puts six AI specialists on the case instead." |
| 3 | Detective | 0:18–0:38 | t=18–45 mixed | zoom Detective msg (P-26065, DQL); pill chain generate→verify→execute as 3 snap cuts; chips: `P-26065`, `2,985 errors` | "Detective taps straight into Dynatrace…" |
| 4 | Swarm + MR | 0:38–0:58 | t=114–162 | 3 thinking pills wide; zoom green IMPACT `7 customers · $18,397/mo`; CodeArch `create_merge_request` pill → **RECEIPT hold #1**: real MR link (t=160), music duck | "Then the swarm fans out… a real GitLab merge request." |
| 5 | Human gate | 0:58–1:10 | t=186–192 | Reviewer verdict "revise" zoom; Approve & ship click; "Human decision: approve" stamp; ding SFX | "An independent Reviewer pushes back… nothing ships without you." |
| 6 | Verify (timelapse → receipt) | 1:10–1:26 | t=192–290 ramped ~12x → snap 1x at t=290 | visible timelapse w/ caption; **stopdown #2** → green "Recovery verified… PASS (2.9ms)" + `1204ms → 2.9ms` counter chip; hold 3s | "Then it proves the fix worked…" |
| 7 | CTA | 1:26–1:40 | — end card | HiveMark nodes link up; "Incidents, fixed end to end."; heyhivemind.com huge; music resolves | "HiveMind. Incidents, fixed end to end." |

Rules: a visual change every ≤3s; VO covers ≤60% of runtime; receipts play with no VO;
never zoom the bottom-left footer; captions = 1–4 words/page, white + amber active word.

## Voiceover script (Brian — deep, resonant; eleven_multilingual_v2, with-timestamps)

0. hook    — "This is a real SEV one. Checkout latency just blew through its SLO. Live, in production."
1. problem — "Normally? A human gets paged. Stares at dashboards. Starts guessing."
2. reveal  — "HiveMind puts six AI specialists on the case instead."
3. detective — "Detective taps straight into Dynatrace. It writes real Grail queries, verifies them, runs them. And finds the root cause: a hidden 1.2 second delay inside payment-service."
4. swarm   — "Then the swarm fans out, in parallel. Liaison names the blast radius: seven customers, eighteen thousand dollars a month at risk. And CodeArch doesn't just find the bug. It opens the fix, as a real GitLab merge request."
5. gate    — "An independent Reviewer audits everything. And pushes back. But nothing ships without you. One click. Approved."
6. proof   — "Then, it proves the fix worked. Twelve hundred milliseconds, down to three. Verified on live telemetry. Not vibes."
7. cta     — "HiveMind. Incidents, fixed end to end."

## Audio
- Music: ElevenLabs Music API, composition plan with sections matching beats
  (tense pulse 0–13s → near-silence 13–16s → driving groove → suspense breakdown → euphoric resolve).
  Ducked to ~0.25 under VO; stopdowns at reveal + receipt.
- SFX: whoosh (transitions), braam (reveal/receipt), riser (pre-reveal), soft ding (approval), alarm tick (cold open).
