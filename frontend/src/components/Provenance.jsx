/**
 * Tap a number, see where it came from (PRD.md §7, CLAUDE.md §2.3).
 *
 * The rule is "a number without provenance must not render", so this component
 * is built to make violating it hard: `<Value>` takes the number AND its
 * provenance together, and if the provenance is missing it renders the honest
 * marker "—" instead of the bare number. You cannot accidentally print an
 * unsourced figure by forgetting a prop; you have to pass one explicitly.
 *
 * The disclosure is a <details> rather than a modal or tooltip: it works with
 * a thumb, it works without JavaScript state, it prints, and a judge can open
 * several at once to compare sources.
 */

const SOURCE_LABEL = {
  kb: 'জ্ঞানভাণ্ডার',
  api: 'লাইভ API',
  dataset: 'ডেটাসেট',
  static_table: 'সারণি',
  computed: 'গণনা',
}

const CONFIDENCE_LABEL = {
  high: 'উচ্চ',
  medium: 'মাঝারি',
  low: 'নিম্ন',
}

/**
 * A value with its source attached.
 *
 * @param value    what to display (already formatted — this component does no
 *                 arithmetic and no rounding; the engine owns both)
 * @param prov     a Provenance object from the API
 * @param unit     optional unit shown after the value
 */
export default function Value({ value, prov, unit }) {
  if (value === null || value === undefined) return <span className="mono">—</span>

  if (!prov) {
    // Deliberately not the number. If this shows up on screen it is a bug we
    // want to see, not one that hides behind a plausible figure.
    return (
      <span className="mono unsourced" title="no provenance — not rendered">
        —
      </span>
    )
  }

  return (
    <details className="prov">
      <summary>
        <span className="mono">{value}</span>
        {unit && <span className="prov-unit">{unit}</span>}
      </summary>
      <div className="prov-body">
        <p className="prov-title">{prov.source_title}</p>
        <ul>
          <li>
            <span className="prov-key">উৎস</span>
            <span>
              {SOURCE_LABEL[prov.source_type] ?? prov.source_type}
              <span className="mono"> ({prov.source_id})</span>
            </span>
          </li>
          {prov.locator && (
            <li>
              <span className="prov-key">অবস্থান</span>
              <span className="mono">{prov.locator}</span>
            </li>
          )}
          {prov.formula && (
            <li>
              <span className="prov-key">পদ্ধতি</span>
              <span>{prov.formula}</span>
            </li>
          )}
          <li>
            <span className="prov-key">নির্ভরযোগ্যতা</span>
            <span className={`conf conf-${prov.confidence}`}>
              {CONFIDENCE_LABEL[prov.confidence] ?? prov.confidence}
            </span>
          </li>
          <li>
            <span className="prov-key">সময়</span>
            <span className="mono">{prov.retrieved_at}</span>
          </li>
        </ul>
      </div>
    </details>
  )
}

/** A provenance with no number of its own — used for assumptions. */
export function Assumption({ prov }) {
  if (!prov) return null
  return (
    <details className="prov prov-assumption">
      <summary>
        {prov.source_title}
        {prov.value !== null && prov.value !== undefined && (
          <span className="mono"> {String(prov.value)}</span>
        )}
      </summary>
      <div className="prov-body">
        <ul>
          <li>
            <span className="prov-key">উৎস</span>
            <span>
              {SOURCE_LABEL[prov.source_type] ?? prov.source_type}
              <span className="mono"> ({prov.source_id})</span>
            </span>
          </li>
          {prov.locator && (
            <li>
              <span className="prov-key">অবস্থান</span>
              <span className="mono">{prov.locator}</span>
            </li>
          )}
          {prov.formula && (
            <li>
              <span className="prov-key">পদ্ধতি</span>
              <span>{prov.formula}</span>
            </li>
          )}
          <li>
            <span className="prov-key">নির্ভরযোগ্যতা</span>
            <span className={`conf conf-${prov.confidence}`}>
              {CONFIDENCE_LABEL[prov.confidence] ?? prov.confidence}
            </span>
          </li>
        </ul>
      </div>
    </details>
  )
}
