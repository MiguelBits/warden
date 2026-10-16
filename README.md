# Warden

Warden scores one household call or SMS, cites a scam playbook, and runs one tool: deliver, hold, block, or queue a person.

An armed lease is what allows a block. A kill switch leaves the review queue as the only action. The decision record and the family alert keep the tactics and drop the message body.

This is an independent reference implementation. It has no affiliation with stopburlas.pt, Guardião, Mellow Strategy, or any employer.

## Try it

```bash
cd /c/Users/mcvco/Desktop/Github_MiguelBits/warden && PYTHONPATH=src python -m unittest discover -s tests -v && PYTHONPATH=src python -m warden.cli eval && PYTHONPATH=src python -m warden.cli triage --household casa-1 --channel sms --sender "+351900000000" --text "Ola mae, mudei de numero. Envia ja um codigo MB WAY e nao digas ao pai."
```

```
verdict: block
risk: 86
tool: block_sender
reason: policy
tactics: urgency, payment, credential, isolation, family_hook
grounded: yes family_impersonation 0.766
alert: Warden blocked an SMS. Tactics: urgency, payment, credential, isolation, family_hook.
```

The suite uses the Python standard library. No API key, no network.

## Gate

`evals/cases.jsonl` holds 13 labeled messages. Eight are scams, three are ordinary household notes, two are ambiguous. `python -m warden.cli eval` prints every verdict and exits non-zero if a label moves, if a benign note is blocked, or if fewer than 80% of the scams are held or blocked.

Current gate: scam catch 1.00, benign blocks 0.

GitHub Actions runs the suite on every push. The `promote` workflow runs it again, then deploys the Cloudflare control plane from a protected `production` environment.

## Engineering map

| Concern | Where it lives |
| --- | --- |
| Agent and tool contract | `src/warden/contracts.py`, `src/warden/tools.py` |
| Orchestration and state | `src/warden/agent.py` |
| Memory | `src/warden/memory.py` |
| Retrieval and grounding | `src/warden/retrieve.py`, `knowledge/playbooks/` |
| Bounded autonomy | `src/warden/policy.py` |
| Human approval and safe stop | `src/warden/control.py`, `cloud/src/worker.js` |
| Evaluation and regression | `evals/cases.jsonl`, `src/warden/evaluate.py` |
| Observability | decision `steps`, Worker JSON logs, Workers traces |
| CI and controlled promotion | `.github/workflows/ci.yml`, `.github/workflows/promote.yml` |

`ARCHITECTURE.md` is the review checklist for the same pieces.

## Autonomy

`observe` queues every case. `hold` may quarantine and cannot block. `act` may block when the risk is high and a playbook is cited.

Production takes the level from control-plane health. An unarmed lease stays at `hold`. A kill switch forces `observe`. `--autonomy act` on the CLI is a local override so a laptop can show a block without a lease.

A trusted sender lowers a weak signal. A payment demand or a code request keeps its score.

## Retrieval

The playbooks are detection notes: fake bank, fake relative, parcel fee, fake authority, fake help desk. The retriever mixes a hashing embedder with overlap on the tactic tags. `embed()` is the seam for a hosted embedding model. The gate never calls one.

Citation and action are separate. "I paid the electricity at the bank this morning" retrieves the bank note and the policy still delivers it, because the message never asks for a code or a transfer.

An instruction to ignore the rules does not clear a payment demand. The same instruction with no scam tactics opens review.

## Control plane

The Worker queues a case, claims it, and stores the verdict. Classification stays in the Python package. After the result is posted, the stored body is cleared.

The API token is a Wrangler secret. Comparison hashes both values with SHA-256 and uses `crypto.subtle.timingSafeEqual`. Case ids come from `crypto.randomUUID()`. Logs are structured JSON. Workers logs and traces are enabled in `cloud/wrangler.toml`.

```bash
cd /c/Users/mcvco/Desktop/Github_MiguelBits/warden/cloud && npx wrangler kv namespace create WARDEN && npx wrangler secret put API_TOKEN
```

Replace the placeholder namespace id in `cloud/wrangler.toml` before the promote workflow. The deploy secret is `CLOUDFLARE_API_TOKEN` on the GitHub `production` environment.

## Layout

```
src/warden/     decision path
knowledge/      playbooks the agent may cite
evals/          labeled cases
tests/          unit tests and the gate
cloud/          Cloudflare control plane
.github/        CI and manual promotion
```

## License

MIT.
