# Credits & licensing

## Twitter V2 (launch cut)
`hivemind-twitter-v2-jessica.mp4` — music: **Justice — "Genesis"** (Cross, 2007; Ed Banger/Because Music).
Fully commercial track: fine for a non-monetized post (expect a YouTube Content ID claim);
would need a license for any monetized/commercial distribution.

## Older picks (voice = Ratnam's cloned voice + a male voice)
The chosen cuts use the two liked beds — both **Tycho** (commercial / Ghostly Intl;
fine for the hackathon submission, license for any public commercial launch):
- `hivemind-ratnam-minimal-tycho-dive.mp4` / `hivemind-male-minimal-tycho-dive.mp4` → **Tycho — "Dive"**
- `hivemind-ratnam-organic-tycho-awake.mp4` / `hivemind-male-organic-tycho-awake.mp4` → **Tycho — "Awake"**
Narration: Ratnam's own ElevenLabs voice clone, and a separate male voice.

## Music — all candidate beds
Each hero version uses a different bed (subtle, premium). Licensing status differs —
fine for a hackathon submission; if you ever distribute commercially, check the notes.

| File | Track | Licensing |
|------|-------|-----------|
| `...-1-cinematic-scottbuckley.mp4` | Scott Buckley — "Shadows and Dust" | **CC-BY 4.0** — credit required (clearable) |
| `...-2-minimal-tycho-dive.mp4` | Tycho — "Dive" | Commercial (Ghostly Intl) — needs license for public commercial use |
| `...-3-lofi-lindecis.mp4` | L'indécis — "Soulful" | Chillhop — free for many uses, check Chillhop terms |
| `...-4-organic-tycho-awake.mp4` | Tycho — "Awake" | Commercial (Ghostly Intl) — needs license for public commercial use |
| `...-5-piano-haniarani.mp4` | Hania Rani — "Eden" | Commercial (Gondwana) — needs license for public commercial use |

Teaser still uses "The Complex" by Kevin MacLeod (CC-BY).

**If you pick the Scott Buckley one** (fully clearable), credit:
> Music: "Shadows and Dust" by Scott Buckley (scottbuckley.com.au) — CC-BY 4.0

**If you pick a commercial track** (Tycho / Hania Rani): fine for the hackathon
submission video; for a public launch you'd license it (or I can swap in a
cleared look-alike — Tycho-style → Rexlambo "space" CC-BY, etc.).

If you'd rather have **zero-attribution** music, swap to a CC0 / Pixabay-License track:
drop the file in `public/audio/`, point `BEDS[0].file` in `src/timeline.ts` at it,
rebuild the bed window, and re-run `scripts/finalize.sh`. Seven other candidate
tracks are in `public/audio/candidates/` (all Kevin MacLeod / CC-BY) if you want a
different vibe — `the-complex` was chosen because its energy curve best matched the
tense→build→triumphant arc of the edit.

## Voiceover & sound design
- Narration: ElevenLabs `eleven_multilingual_v2` — Brian (male) and Laura (female).
- SFX (whoosh / braam / riser / ding / alarm): ElevenLabs sound-generation API.
  These are AI-generated for this project; no third-party rights attach.

## Footage
- Screen recording: HiveMind war-room demo (own product).
- Logo: HiveMind mark (own brand, matches web/app/icon.svg).
