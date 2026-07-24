import { useEffect, useMemo, useRef, useState } from 'react'

/**
 * Renders an `input_request` event (PLAN.md §2) as a widget.
 *
 * These are accelerators, not a form wizard (PRD.md §8 Tier0.1): the composer
 * stays live the whole time, so a farmer who would rather type a sentence
 * always can, and the agent extracts what it needs from free text. The widget
 * only removes typing for the common answer.
 *
 * Bangla labels come from the agent in `options[].label_bn`. Unit labels are
 * the one exception — the contract sends `unit_options` as bare canonical
 * strings, so the Bangla mapping below mirrors UNIT_LABELS_BN in
 * backend/units.py. Keep the two in step.
 */

const UNIT_LABELS_BN = {
  ha: 'হেক্টর',
  bigha: 'বিঘা',
  katha: 'কাঠা',
  decimal: 'শতক',
  acre: 'একর',
  sq_m: 'বর্গমিটার',
  sq_ft: 'বর্গফুট',
  kg: 'কেজি',
  maund: 'মণ',
  seer: 'সের',
  quintal: 'কুইন্টাল',
  metric_ton: 'টন',
}

const unitLabel = (unit) => UNIT_LABELS_BN[unit] ?? unit

export default function InputRequest({ request, onAnswer, disabled }) {
  const { input_kind: kind, prompt_bn: prompt, options, unit_options: unitOptions } = request

  return (
    <section className="input-request" aria-label={prompt}>
      <p className="ir-prompt">{prompt}</p>
      {kind === 'chips' && (
        <Chips options={options ?? []} onAnswer={onAnswer} disabled={disabled} />
      )}
      {kind === 'dropdown' && (
        <SearchableDropdown
          options={options ?? []}
          onAnswer={onAnswer}
          disabled={disabled}
        />
      )}
      {kind === 'number' && <NumberInput onAnswer={onAnswer} disabled={disabled} />}
      {kind === 'number_unit' && (
        <NumberWithUnit
          unitOptions={unitOptions ?? []}
          onAnswer={onAnswer}
          disabled={disabled}
        />
      )}
      {kind === 'text' && <TextInput onAnswer={onAnswer} disabled={disabled} />}
    </section>
  )
}

/* --- chips: soil, water, season, land type ------------------------------- */

function Chips({ options, onAnswer, disabled }) {
  return (
    <div className="chips">
      {options.map((option) => (
        <button
          key={option.value}
          className="chip"
          disabled={disabled}
          onClick={() => onAnswer(option.label_bn)}
        >
          {option.label_bn}
        </button>
      ))}
    </div>
  )
}

/* --- dropdown: the 64 districts ------------------------------------------ */

function SearchableDropdown({ options, onAnswer, disabled }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const boxRef = useRef(null)

  // 64 districts is too many to scroll on a phone, so it filters as you type.
  // Matching on both Bangla label and canonical value means "raj" and "রাজ"
  // both work — a farmer types Bangla, a judge might type English.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return options
    return options.filter(
      (option) =>
        option.label_bn.toLowerCase().includes(q) ||
        String(option.value).toLowerCase().includes(q),
    )
  }, [options, query])

  useEffect(() => {
    const onClickAway = (event) => {
      if (boxRef.current && !boxRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickAway)
    return () => document.removeEventListener('mousedown', onClickAway)
  }, [])

  return (
    <div className="dropdown" ref={boxRef}>
      <input
        className="field"
        type="text"
        value={query}
        disabled={disabled}
        placeholder="খুঁজুন…"
        onChange={(event) => {
          setQuery(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
      />
      {open && filtered.length > 0 && (
        <ul className="dropdown-list">
          {filtered.map((option) => (
            <li key={option.value}>
              <button
                className="dropdown-item"
                disabled={disabled}
                onClick={() => {
                  setOpen(false)
                  setQuery('')
                  onAnswer(option.label_bn)
                }}
              >
                {option.label_bn}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && filtered.length === 0 && (
        <p className="dropdown-empty">কোনো মিল পাওয়া যায়নি</p>
      )}
    </div>
  )
}

/* --- number: budget ------------------------------------------------------ */

function NumberInput({ onAnswer, disabled }) {
  const [value, setValue] = useState('')
  const submit = () => {
    if (value.trim()) onAnswer(value.trim())
  }
  return (
    <div className="row">
      {/* inputMode numeric gets the digit keypad on Android without blocking
          paste or Bangla digits typed by a determined user. */}
      <input
        className="field"
        type="number"
        inputMode="numeric"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => event.key === 'Enter' && submit()}
      />
      <button disabled={disabled || !value.trim()} onClick={submit}>
        ঠিক আছে
      </button>
    </div>
  )
}

/* --- number + unit: farm area -------------------------------------------- */

function NumberWithUnit({ unitOptions, onAnswer, disabled }) {
  const [value, setValue] = useState('')
  const [unit, setUnit] = useState(unitOptions[0] ?? 'bigha')

  const submit = () => {
    // Sent as "2 বিঘা" — natural Bangla the agent already has to parse from
    // free text, so the widget needs no separate server-side path.
    if (value.trim()) onAnswer(`${value.trim()} ${unitLabel(unit)}`)
  }

  return (
    <div className="row">
      <input
        className="field field-narrow"
        type="number"
        inputMode="decimal"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => event.key === 'Enter' && submit()}
      />
      <select
        className="field field-narrow"
        value={unit}
        disabled={disabled}
        onChange={(event) => setUnit(event.target.value)}
      >
        {unitOptions.map((option) => (
          <option key={option} value={option}>
            {unitLabel(option)}
          </option>
        ))}
      </select>
      <button disabled={disabled || !value.trim()} onClick={submit}>
        ঠিক আছে
      </button>
    </div>
  )
}

/* --- free text ----------------------------------------------------------- */

function TextInput({ onAnswer, disabled }) {
  const [value, setValue] = useState('')
  const submit = () => {
    if (value.trim()) onAnswer(value.trim())
  }
  return (
    <div className="row">
      <input
        className="field"
        type="text"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => event.key === 'Enter' && submit()}
      />
      <button disabled={disabled || !value.trim()} onClick={submit}>
        ঠিক আছে
      </button>
    </div>
  )
}
