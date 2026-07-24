/**
 * traceGraph.js — turns the flat SSE trace array into a provenance graph.
 *
 * Pure, no React, no DOM. `buildGraph(trace)` reads the same `tool_call` /
 * `tool_result` events TracePanel.jsx renders as JSON and turns them into:
 *
 *   - nodes: facts the plan rests on (the farm, a place, a weather reading, a
 *     retrieved source, a ranked crop, the season plan, the finance summary,
 *     a question asked back to the farmer)
 *   - edges: the tool call that produced each fact, `{from, to, tool, callId}`
 *   - callsById: every paired call, keyed by id, for the node inspector
 *
 * No arithmetic happens here (CLAUDE.md rule 1). Every sub-label either
 * quotes a server value verbatim or counts array length. If a value isn't on
 * the wire already, it doesn't appear on a node.
 *
 * `trace` is never cleared between turns (useChat.js), and the same fact can
 * be re-fetched turn after turn — so every node id below is a STABLE, DEDUPED
 * key (farm, a rounded lat/lon, a crop name, a KB doc id, ...). Re-running a
 * tool updates the existing node (last write wins) instead of adding a
 * duplicate. Without this a three-turn session would draw three weather
 * triangles instead of one.
 */

const CROP_LABELS = {
  boro_rice: 'Boro Rice',
  aman_rice: 'Aman Rice',
  potato: 'Potato',
  mustard: 'Mustard',
  lentil: 'Lentil',
}

function cropLabel(key) {
  return CROP_LABELS[key] ?? titleCase(key)
}

function titleCase(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

function round2(n) {
  return Math.round(n * 100) / 100
}

// Shape + color are the second, coarser signal (kind); text color is the
// finer one (see GraphPanel.jsx: label vs sub vs edge-tool each get their own
// ink). One dict, shared by GraphPanel and the legend, so they can't drift.
export const NODE_STYLE = {
  farm: { shape: 'hexagon', r: 26, fill: 'var(--green)', stroke: 'var(--green-dark)', textFill: '#fff' },
  place: { shape: 'triangle', r: 17, fill: 'var(--surface)', stroke: 'var(--soil)' },
  weather: { shape: 'triangle', r: 17, fill: 'var(--surface)', stroke: 'var(--soil)' },
  source: { shape: 'pentagon', r: 15, fill: 'var(--surface)', stroke: 'var(--leaf)' },
  crop: { shape: 'circle', r: 20, fill: 'var(--green-tint)', stroke: 'var(--green)' },
  plan: { shape: 'square', r: 18, fill: 'var(--surface-sunk)', stroke: 'var(--green-dark)' },
  finance: { shape: 'square', r: 18, fill: 'var(--surface-sunk)', stroke: 'var(--green-dark)' },
  question: { shape: 'circle', r: 12, fill: 'var(--surface)', stroke: 'var(--ink-faint)' },
}

export const LEGEND = [
  { kind: 'farm', label: 'Farm' },
  { kind: 'place', label: 'Place' },
  { kind: 'weather', label: 'Weather' },
  { kind: 'source', label: 'KB / dataset source' },
  { kind: 'crop', label: 'Crop' },
  { kind: 'plan', label: 'Plan' },
  { kind: 'finance', label: 'Finance' },
  { kind: 'question', label: 'Question' },
]

function pairEvents(trace) {
  const calls = {}
  const order = []
  for (const event of trace) {
    if (event.type !== 'tool_call' && event.type !== 'tool_result') continue
    const id = event.id
    if (!calls[id]) {
      calls[id] = { id, name: event.name }
      order.push(id)
    }
    const rec = calls[id]
    if (event.type === 'tool_call') {
      rec.params = event.params
      rec.tsCall = event.ts
      rec.redactedCall = event.redacted ?? []
    } else {
      rec.result = event.result_raw
      rec.tsResult = event.ts
      rec.redactedResult = event.redacted ?? []
    }
  }
  return { calls, order }
}

function formatFarmSub(fields) {
  const parts = []
  if (fields.district) parts.push(fields.district)
  if (fields.area != null) parts.push(`${fields.area}${fields.area_unit ? ` ${fields.area_unit}` : ''}`)
  if (fields.soil_type) parts.push(fields.soil_type)
  if (fields.water_source) parts.push(fields.water_source)
  if (fields.season) parts.push(fields.season)
  if (fields.budget_bdt != null) parts.push(`৳${fields.budget_bdt}`)
  return parts.length ? parts.join(' · ') : 'profile forming…'
}

export function buildGraph(trace) {
  const { calls, order } = pairEvents(trace)

  const nodes = new Map()
  const edges = new Map()

  const upsertNode = (id, patch) => nodes.set(id, { ...(nodes.get(id) ?? { id }), ...patch })
  const upsertEdge = (from, to, tool, callId) => {
    const key = `${from}=>${to}:${tool}`
    edges.set(key, { id: key, from, to, tool, callId })
  }

  // The farm hexagon always exists, even before any tool has fired — the
  // graph has a center from the first token of the conversation.
  upsertNode('farm', { kind: 'farm', label: 'Farm', sub: 'profile forming…' })

  // Farm profile: last-wins merge of every field any relevant call has ever
  // carried, walked in trace order so a later turn's correction (e.g. area
  // edited from 2 to 3 bigha) overwrites the earlier value.
  const farmFields = {}
  let farmSourceCallId = null
  for (const event of trace) {
    if (event.type !== 'tool_call') continue
    if (!['remember_farm', 'crop_scorer', 'finance_projection'].includes(event.name)) continue
    const p = event.params ?? {}
    let touched = false
    for (const key of ['district', 'area', 'area_unit', 'soil_type', 'water_source', 'budget_bdt', 'season']) {
      if (p[key] !== undefined && p[key] !== null && p[key] !== '') {
        farmFields[key] = p[key]
        touched = true
      }
    }
    if (touched) farmSourceCallId = event.id
  }
  upsertNode('farm', { sub: formatFarmSub(farmFields), sourceCallId: farmSourceCallId })

  // Retrieval linkage: loop.py force-emits rag_query ahead of crop_scorer and
  // season_plan under id `retrieval-{parentCallId}`. Collect those source
  // node ids per parent so the crop_scorer/season_plan pass below can draw
  // source -> crop / source -> plan edges — the one edge that makes "this
  // advice is grounded in a retrieved document" visible rather than claimed.
  const retrievalSourcesByParent = new Map()

  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'rag_query' || !rec.result || !Array.isArray(rec.result.matches)) continue
    const isForced = id.startsWith('retrieval-')
    const parentId = isForced ? id.slice('retrieval-'.length) : null
    const sourceIds = []
    for (const match of rec.result.matches) {
      const sourceId = `source:${match.id}`
      upsertNode(sourceId, {
        kind: 'source',
        label: match.source_title ?? match.id,
        sub: match.locator ?? match.crop ?? '',
        sourceCallId: id,
      })
      sourceIds.push(sourceId)
      if (!isForced) upsertEdge('farm', sourceId, 'rag_query', id)
    }
    if (isForced && sourceIds.length) retrievalSourcesByParent.set(parentId, sourceIds)
  }

  // geocode -> place. Kept for weather to attach to when a place was
  // resolved; falls back to farm otherwise.
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'geocode' || !rec.result?.candidates?.length) continue
    const c = rec.result.candidates[0]
    if (c.lat == null || c.lon == null) continue
    const placeId = `place:${round2(c.lat)},${round2(c.lon)}`
    upsertNode(placeId, {
      kind: 'place',
      label: c.name,
      sub: [c.district, c.division].filter(Boolean).join(', '),
      sourceCallId: id,
    })
    upsertEdge('farm', placeId, 'geocode', id)
  }

  // get_forecast / get_climatology -> weather. Deduped by location + kind, so
  // re-fetching the same farm's weather across turns updates one node.
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'get_forecast' && rec.name !== 'get_climatology') continue
    const lat = rec.params?.lat ?? rec.result?.lat
    const lon = rec.params?.lon ?? rec.result?.lon
    if (lat == null || lon == null) continue
    const isClimatology = rec.name === 'get_climatology'
    const weatherId = `weather:${isClimatology ? 'climatology' : 'forecast'}:${round2(lat)},${round2(lon)}`
    const degraded = Boolean(rec.result?.error)
    let sub
    if (degraded) {
      sub = 'unavailable — তথ্য যথেষ্ট নয়'
    } else if (isClimatology) {
      const n = rec.result?.normals?.length ?? 0
      sub = `${n} month normals${rec.result?.window ? ` · ${rec.result.window}` : ''}`
    } else {
      const daily = rec.result?.daily ?? []
      sub = daily.length
        ? `${daily.length}d · day1 ${daily[0].precip_mm}mm, ${daily[0].tmax_c}°C`
        : '0 days returned'
    }
    upsertNode(weatherId, {
      kind: 'weather',
      label: isClimatology ? 'Climatology' : 'Forecast',
      sub,
      dashed: isClimatology,
      degraded,
      sourceCallId: id,
    })
    const placeId = `place:${round2(lat)},${round2(lon)}`
    const from = nodes.has(placeId) ? placeId : 'farm'
    upsertEdge(from, weatherId, rec.name, id)
  }

  // crop_scorer -> one crop node per candidate, survivors and exclusions
  // alike (an exclusion is evidence too: it shows the deterministic screen
  // working, not the model guessing).
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'crop_scorer' || !rec.result?.candidates) continue
    for (const candidate of rec.result.candidates) {
      const cropId = `crop:${candidate.crop}`
      upsertNode(cropId, {
        kind: 'crop',
        label: cropLabel(candidate.crop),
        sub: candidate.excluded
          ? truncate(candidate.exclusion_reason, 60)
          : `${candidate.composite_score}/100 · ${candidate.water_need} water · ${candidate.risk_level} risk`,
        excluded: candidate.excluded,
        sourceCallId: id,
      })
      upsertEdge('farm', cropId, 'crop_scorer', id)
    }
    const sources = retrievalSourcesByParent.get(id) ?? []
    if (sources.length) {
      const survivors = rec.result.candidates.filter((c) => !c.excluded)
      for (const sourceId of sources) {
        for (const survivor of survivors) {
          upsertEdge(sourceId, `crop:${survivor.crop}`, 'rag_query', id)
        }
      }
    }
  }

  // season_plan -> the single plan node.
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'season_plan' || !rec.result?.plan) continue
    const plan = rec.result.plan
    upsertNode('plan', {
      kind: 'plan',
      label: 'Season Plan',
      sub: `${plan.tasks.length} tasks · ${cropLabel(plan.crop)}`,
      sourceCallId: id,
    })
    const cropId = `crop:${plan.crop}`
    const from = nodes.has(cropId) ? cropId : 'farm'
    upsertEdge(from, 'plan', 'season_plan', id)
    for (const sourceId of retrievalSourcesByParent.get(id) ?? []) {
      upsertEdge(sourceId, 'plan', 'rag_query', id)
    }
  }

  // finance_projection -> the single finance node.
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'finance_projection') continue
    const p = rec.params ?? {}
    const ok = rec.result && !rec.result.error
    upsertNode('finance', {
      kind: 'finance',
      label: 'Finance',
      sub: ok
        ? `net ৳${rec.result.summary.net_profit_bdt} · ROI ${rec.result.summary.roi_pct}%`
        : `degraded: ${rec.result?.error ?? 'pending'}`,
      degraded: !ok,
      sourceCallId: id,
    })
    const cropId = `crop:${p.crop}`
    const from = nodes.has(cropId) ? cropId : 'farm'
    upsertEdge(from, 'finance', 'finance_projection', id)
  }

  // ask_farmer -> a question node per field asked.
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'ask_farmer' || !rec.params?.field) continue
    const qId = `q:${rec.params.field}`
    upsertNode(qId, {
      kind: 'question',
      label: rec.params.field,
      sub: truncate(rec.params.prompt_bn, 40),
      sourceCallId: id,
    })
    upsertEdge('farm', qId, 'ask_farmer', id)
  }

  // cropdb_sql standalone -> a dataset source node (never forced/paired, so
  // every call here stands alone).
  for (const id of order) {
    const rec = calls[id]
    if (rec.name !== 'cropdb_sql') continue
    const p = rec.params ?? {}
    const sourceId = `source:cropdb:${id}`
    upsertNode(sourceId, {
      kind: 'source',
      label: p.action ?? 'cropdb_sql',
      sub: [p.crop, p.district].filter(Boolean).join(' / '),
      sourceCallId: id,
    })
    upsertEdge('farm', sourceId, 'cropdb_sql', id)
  }

  const nodeList = [...nodes.values()]
  const nodeIds = new Set(nodeList.map((n) => n.id))
  const edgeList = [...edges.values()].filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))

  return { nodes: nodeList, edges: edgeList, callsById: calls }
}
