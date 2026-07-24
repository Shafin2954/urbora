const CAPABILITIES = [
  ['intake', 'তথ্য সংগ্রহ', 'ask_farmer'],
  ['weather', 'লাইভ আবহাওয়া', 'get_forecast'],
  ['knowledge', 'জ্ঞানভান্ডার', 'rag_query'],
  ['ranking', 'ফসল বাছাই', 'crop_scorer'],
  ['finance', 'আর্থিক হিসাব', 'finance_projection'],
  ['plan', 'মৌসুম পরিকল্পনা', 'season_plan'],
]

export default function EvidencePanel({ trace, plan, finance }) {
  const called = new Set(trace.filter((event) => event.type === 'tool_call').map((event) => event.name))
  const complete = (key, tool) => {
    if (key === 'finance') return Boolean(finance) || called.has(tool)
    if (key === 'plan') return Boolean(plan) || called.has(tool)
    return called.has(tool)
  }
  const scorer = [...trace].reverse().find((event) => event.type === 'tool_result' && event.name === 'crop_scorer')?.result_raw
  const forecast = [...trace].reverse().find((event) => event.type === 'tool_result' && event.name === 'get_forecast')?.result_raw
  const retrieval = [...trace].reverse().find((event) => event.type === 'tool_result' && event.name === 'rag_query')?.result_raw
  const ranked = (scorer?.candidates ?? []).filter((candidate) => !candidate.excluded)

  return (
    <div className="evidence">
      <p className="evidence-intro">এই টার্নে যে প্রমাণ ব্যবহার হয়েছে। প্রতিটি কার্ডের বিস্তারিত Trace-এ দেখা যাবে।</p>
      <div className="capability-grid">
        {CAPABILITIES.map(([key, label, tool]) => (
          <div className={`capability ${complete(key, tool) ? 'is-done' : ''}`} key={key}>
            <strong>{complete(key, tool) ? '✓' : '○'} {label}</strong>
            <span className="mono">{complete(key, tool) ? tool : 'এই টার্নে এখনও হয়নি'}</span>
          </div>
        ))}
      </div>
      {forecast?.daily?.[0] && (
        <section className="evidence-card">
          <h3>সাম্প্রতিক পূর্বাভাস</h3>
          <p className="mono">{forecast.daily[0].date} · {forecast.daily[0].tmax_c}°C · {forecast.daily[0].precip_mm} mm</p>
          <small>Open-Meteo forecast · Trace-এ raw response আছে</small>
        </section>
      )}
      {ranked.length > 0 && (
        <section className="evidence-card">
          <h3>র‌্যাঙ্ক করা ফসল</h3>
          {ranked.map((candidate) => <p className="mono" key={candidate.crop}>{candidate.crop}: {candidate.composite_score}/100 · {candidate.water_need} water · {candidate.risk_level} risk</p>)}
        </section>
      )}
      {retrieval?.matches?.length > 0 && (
        <section className="evidence-card">
          <h3>জ্ঞানভান্ডার থেকে পাওয়া উৎস</h3>
          {retrieval.matches.map((match) => <p key={match.id}>{match.source_title} — <span className="mono">{match.locator}</span></p>)}
        </section>
      )}
    </div>
  )
}
