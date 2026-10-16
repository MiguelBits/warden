# Architecture

Warden is two processes with one contract between them.

The Python package decides. The Cloudflare Worker queues work, stores the kill switch, and arms a human lease. A telephone adapter would implement the tool names. This repository records the effect and stops there.

## Decision path

1. Load the household card.
2. Tag tactics with deterministic patterns. Accent-stripped Portuguese and English share one pattern list.
3. Retrieve playbooks and keep the citations.
4. Policy chooses `allow`, `quarantine`, `block`, or `review`.
5. `authorize()` checks autonomy and the kill switch. A refused tool downgrades to `open_review`.
6. The tool returns an effect and a family alert. It does not dial, reply, or open a link.
7. Persist the incident. The incident stores sender, verdict, risk, tactics, and tool. The body is absent.

The record field `steps` is that sequence. A downgrade appends `downgrade_review`.

## Tool contract

| Tool | Effect | Minimum autonomy |
| --- | --- | --- |
| `allow_through` | deliver | observe |
| `open_review` | queue a person | observe |
| `quarantine_message` | hold off the lock screen | hold |
| `block_sender` | drop this message | act |

`contracts.Record` is the JSON a worker posts back to `/v1/cases/result`. The control plane accepts `verdict`, `tool`, `risk`, and `reason`. It discards any body on that request and blanks the stored text.

## Policy

Risk is a weighted sum of tactics, capped at 100.

| Condition | Result | Reason |
| --- | --- | --- |
| Kill switch on | review | `kill_switch` |
| Autonomy `observe` | review | `autonomy_observe` |
| Instruction rewrite, no payment or credential or link or isolation | review | `prompt_injection` |
| Harmful tactics, risk at least 40, no citation | review | `ungrounded` |
| Risk at least 70, cited, autonomy `act` | block | `policy` |
| Risk at least 70, cited, autonomy `hold` | quarantine | `autonomy_hold` |
| Risk at least 45, cited, `hold` or `act` | quarantine | `policy` |
| Risk at most 28, no payment and no credential | allow | `policy` |
| Anything in between | review | `policy` |

A trusted sender subtracts 18 from a weak signal. Payment and credential keep the full score, including when the sender name is already on the household card. That is the spoof case in the gate (`mom-spoof`).

## Retrieval

Each playbook has an id and a tactic list. The score mixes a 64-dimension hashing embedder with token coverage, then boosts chunks whose tactic tags overlap the message. `embed()` is the replacement point for a hosted model. Grounding requires a top score of at least 0.2 and a shared tactic. With an empty knowledge directory the same scam text returns `ungrounded` and cannot block.

## Control plane

`GET /v1/health` is public and returns the kill flag, the lease, and the queue depth. Every other route requires `Authorization: Bearer`. A missing `API_TOKEN` fails closed with 503.

`POST /v1/lease/arm` opens an `act` window for 1 to 120 minutes. `POST /v1/lease/clear` drops the lease, and the next health read stays at `hold`. `POST /v1/kill` with `{"killed": true}` forces `observe`. `{"killed": false}` is the recovery.

`flags_from_health()` is the production mapping. The CLI flag is the local override.

## Review checklist

Use this when reading an agent someone else shipped.

- Name each tool, the effect, and the autonomy it requires.
- Show a harmful case that stays in review when the knowledge directory is empty.
- Show the kill switch landing on `open_review`, with the body absent from the stored incident.
- Show a trusted display name that still blocks a code request.
- Show the eval command failing if a labeled verdict changes.
- Show promotion as a separate workflow that re-runs the gate and deploys only from the protected environment.
- Show where a hosted embedder would plug in, and confirm the gate still runs with the local one.

## Observability

The decision record is the trace for one case: verdict, risk, reason, citations, tool, autonomy, and steps. The Worker logs JSON with the case id, household id, verdict, and tool. It omits the message body. `cloud/wrangler.toml` enables Workers logs and traces. Lower `head_sampling_rate` when the queue is busy.

## Promotion

`.github/workflows/ci.yml` runs the unit tests, the labeled gate, and `node --check` on the Worker.

`.github/workflows/promote.yml` is `workflow_dispatch`. The eval job runs first. The deploy job needs it, targets the GitHub environment `production`, and calls Wrangler with `CLOUDFLARE_API_TOKEN`. Replace the placeholder KV id before the first deploy.
