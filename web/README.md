# HiveMind War Room (frontend)

Slack-clone incident war-room for HiveMind's multi-agent backend.
Next.js 16 (App Router) · React 19 · Tailwind v4 · shadcn/ui · zustand.

## Run

```bash
bun install
bun dev
```

Open http://localhost:3000 (redirects to `#ops`).

## Routes

| Route | View |
| --- | --- |
| `/` | redirects to `/c/ops` |
| `/c/[channel_id]` | channel: header + message list + composer |
| `/c/[channel_id]/t/[thread_id]` | thread panel slides in beside the channel |

## The 6 agents → partner colors

`detective` (Dynatrace · indigo), `log_diver` (Elastic · teal),
`code_arch` (GitLab · orange), `customer_liaison` (Fivetran · blue),
`scribe` (Atlas · emerald), `reviewer` (Arize · purple).
Defined in [`lib/agents.ts`](lib/agents.ts).

## Data layer

`lib/api.ts` is a typed REST client: `listChannels`, `getMessages`,
`postMessage`, `getThread`. Client state (current channel, per-channel message
cache, optimistic posts) lives in `lib/store.ts` (zustand).

**Mock backend.** Today the API is served by local **Next route handlers** under
`app/api/*`, backed by `lib/mock/data.ts` — a coherent demo incident
(payment-service retry-timeout → MR → 7 customers impacted → approved). This is
the task's "fallback if the backend isn't available", implemented as route
handlers instead of MSW (more robust in the App Router; same contract).

**Switch to the real backend.** Set `NEXT_PUBLIC_API_BASE` (e.g.
`http://localhost:8000`) and the same `lib/api.ts` calls flow through. The real
HiveMind backend currently exposes only `POST /chat` + `GET /healthz`, so the
channels/messages/threads REST surface (and live agent streaming) is the next
backend chunk (T17). Until then, leave `NEXT_PUBLIC_API_BASE` unset to use mocks.

## Notes

- No streaming yet — static request/response by design (streaming is T17).
- Dark mode is the default (`dark` class on `<html>`).
