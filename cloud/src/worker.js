/**
 * Warden control plane.
 * Queues cases, holds the kill switch, and arms a human lease.
 * The decision itself runs in the Python worker. This process stores state.
 */

const VERDICTS = new Set(["allow", "quarantine", "block", "review"])
const CHANNELS = new Set(["sms", "call", "message"])

function emptyState() {
  return {
    killed: false,
    lease: { armed_until: null, armed_by: null },
    cases: [],
  }
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z")
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  })
}

function log(fields) {
  console.log(JSON.stringify({ ts: nowIso(), ...fields }))
}

async function verifyToken(provided, expected) {
  const encoder = new TextEncoder()
  const [providedHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(provided)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ])
  return crypto.subtle.timingSafeEqual(providedHash, expectedHash)
}

async function authorized(request, env) {
  const expected = env.API_TOKEN || ""
  if (!expected) return { ok: false, status: 503, error: "token_not_configured" }
  const header = request.headers.get("Authorization") || ""
  const provided = header.startsWith("Bearer ") ? header.slice(7) : ""
  const match = await verifyToken(provided, expected)
  if (!match) return { ok: false, status: 401, error: "unauthorized" }
  return { ok: true }
}

async function readJson(request) {
  const declared = Number(request.headers.get("content-length") || "0")
  if (declared > 8000) {
    return { error: json({ error: "body_too_large" }, 413) }
  }
  const raw = await request.text()
  if (raw.length > 8000) {
    return { error: json({ error: "body_too_large" }, 413) }
  }
  if (!raw) return { value: {} }
  try {
    return { value: JSON.parse(raw) }
  } catch {
    return { error: json({ error: "bad_json" }, 400) }
  }
}

async function loadState(env) {
  const raw = await env.WARDEN.get("state", "json")
  const state = emptyState()
  if (raw && typeof raw === "object") {
    state.killed = Boolean(raw.killed)
    state.lease = { ...state.lease, ...(raw.lease || {}) }
    state.cases = Array.isArray(raw.cases) ? raw.cases : []
  }
  return state
}

async function saveState(env, state) {
  state.cases = state.cases.slice(-100)
  await env.WARDEN.put("state", JSON.stringify(state))
}

function leaseArmed(lease) {
  if (!lease || !lease.armed_until) return false
  const until = Date.parse(lease.armed_until)
  return Number.isFinite(until) && until > Date.now()
}

function publicCase(item) {
  return {
    id: item.id,
    household_id: item.household_id,
    channel: item.channel,
    sender: item.sender,
    status: item.status,
    verdict: item.verdict || null,
    tool: item.tool || null,
    risk: item.risk ?? null,
    created_at: item.created_at,
    closed_at: item.closed_at || null,
  }
}

async function handle(request, env) {
  const url = new URL(request.url)
  const path = url.pathname
  log({ message: "request", method: request.method, path })

  if (request.method === "GET" && path === "/v1/health") {
    const state = await loadState(env)
    const queued = state.cases.filter((item) => item.status === "queued").length
    return json({
      ok: true,
      killed: state.killed,
      lease: {
        armed: leaseArmed(state.lease),
        armed_until: state.lease.armed_until,
        armed_by: state.lease.armed_by,
      },
      queued,
    })
  }

  const auth = await authorized(request, env)
  if (!auth.ok) return json({ error: auth.error }, auth.status)

  const parsed = await readJson(request)
  if (parsed.error) return parsed.error
  const body = parsed.value
  const state = await loadState(env)

  if (request.method === "POST" && path === "/v1/lease/arm") {
    const minutes = Math.min(120, Math.max(1, Number(body.minutes || 30)))
    state.lease = {
      armed_until: new Date(Date.now() + minutes * 60 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
      armed_by: String(body.by || "operator").slice(0, 64),
    }
    await saveState(env, state)
    log({ message: "lease_armed", minutes, by: state.lease.armed_by })
    return json({ lease: state.lease, armed: true })
  }

  if (request.method === "POST" && path === "/v1/lease/clear") {
    state.lease = { armed_until: null, armed_by: null }
    await saveState(env, state)
    log({ message: "lease_cleared" })
    return json({ lease: state.lease, armed: false })
  }

  if (request.method === "POST" && path === "/v1/kill") {
    state.killed = Boolean(body.killed)
    await saveState(env, state)
    log({ message: "kill_switch", killed: state.killed })
    return json({ killed: state.killed })
  }

  if (request.method === "POST" && path === "/v1/cases") {
    const text = String(body.text || "")
    const channel = String(body.channel || "sms")
    const household = String(body.household_id || "").trim()
    if (!household || !CHANNELS.has(channel) || !text.trim() || text.length > 4000) {
      return json({ error: "bad_case" }, 400)
    }
    const item = {
      id: crypto.randomUUID(),
      household_id: household.slice(0, 64),
      channel,
      sender: String(body.sender || "unknown").slice(0, 64),
      text,
      status: "queued",
      created_at: nowIso(),
    }
    state.cases.push(item)
    await saveState(env, state)
    log({ message: "case_queued", case_id: item.id, household_id: item.household_id, channel })
    return json({ case: publicCase(item) }, 201)
  }

  if (request.method === "POST" && path === "/v1/cases/claim") {
    const item = state.cases.find((row) => row.status === "queued")
    if (!item) return json({ case: null })
    item.status = "claimed"
    item.claimed_at = nowIso()
    await saveState(env, state)
    log({ message: "case_claimed", case_id: item.id })
    return json({
      case: {
        ...publicCase(item),
        text: item.text,
      },
    })
  }

  if (request.method === "POST" && path === "/v1/cases/result") {
    const verdict = String(body.verdict || "")
    const item = state.cases.find((row) => row.id === body.id)
    if (!item) return json({ error: "not_found" }, 404)
    if (!VERDICTS.has(verdict)) return json({ error: "bad_verdict" }, 400)
    item.status = "closed"
    item.verdict = verdict
    item.tool = String(body.tool || "").slice(0, 64)
    item.risk = Number(body.risk || 0)
    item.reason = String(body.reason || "").slice(0, 64)
    item.closed_at = nowIso()
    item.text = ""
    await saveState(env, state)
    log({ message: "case_closed", case_id: item.id, verdict, tool: item.tool, risk: item.risk })
    return json({ case: publicCase(item) })
  }

  return json({ error: "not_found" }, 404)
}

export default {
  async fetch(request, env) {
    try {
      return await handle(request, env)
    } catch (error) {
      console.error(JSON.stringify({
        message: "request_failed",
        error: error instanceof Error ? error.message : String(error),
      }))
      return json({ error: "internal" }, 500)
    }
  },
}
