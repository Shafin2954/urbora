/**
 * Minimal markdown-to-JSX for the chat surface. No dependency — the model's
 * output shape is bounded (Bangla replies, **bold** crop names, flat `-`/`১./1.`
 * lists, paragraph breaks), and the project's own pattern throughout is to own
 * small pieces of infra rather than add a dependency for a narrow need (LOG2:
 * "hand-rolled the SSE layer instead of adding sse-starlette"). Streaming-safe:
 * called fresh on every token update against the full text so far, never on a
 * diff, so a mid-stream `**` with no closing pair just renders as a literal
 * `**` until the close arrives — never throws.
 *
 * Supports: **bold**, flat `-`/`*` bullet lists, flat numbered lists (`1.`,
 * `১.`), paragraph breaks (blank line). Does NOT support nesting, headings,
 * links, code blocks, or tables — the model isn't asked to produce those in
 * chat replies (PRD §9: detailed structure lives in the tabs, not the bubble).
 */

const BENGALI_DIGITS = '০১২৩৪৫৬৭৮৯'

function isListLine(line) {
  const trimmed = line.trimStart()
  if (/^[-*]\s+/.test(trimmed)) return true
  // "1. " / "১. " / "12) " — Western or Bengali digits, dot or paren.
  return new RegExp(`^[0-9${BENGALI_DIGITS}]+[.)]\\s+`).test(trimmed)
}

function stripListMarker(line) {
  const trimmed = line.trimStart()
  return trimmed
    .replace(/^[-*]\s+/, '')
    .replace(new RegExp(`^[0-9${BENGALI_DIGITS}]+[.)]\\s+`), '')
}

/** Render `**bold**` spans inside one line/paragraph of plain text. */
function renderInline(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter((part) => part !== '')
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={`${keyPrefix}-${index}`}>{part.slice(2, -2)}</strong>
    }
    return <span key={`${keyPrefix}-${index}`}>{part}</span>
  })
}

/** Render full message text (possibly still streaming) as React nodes. */
export default function MarkdownLite({ text }) {
  if (!text) return null
  const blocks = text.split(/\n{2,}/)

  return blocks.map((block, blockIndex) => {
    const lines = block.split('\n').filter((line) => line.trim() !== '')
    if (lines.length === 0) return null

    if (lines.every(isListLine)) {
      const isOrdered = !/^[-*]\s+/.test(lines[0].trimStart())
      const ListTag = isOrdered ? 'ol' : 'ul'
      return (
        <ListTag key={blockIndex} className="msg-list">
          {lines.map((line, lineIndex) => (
            <li key={lineIndex}>
              {renderInline(stripListMarker(line), `${blockIndex}-${lineIndex}`)}
            </li>
          ))}
        </ListTag>
      )
    }

    return (
      <p key={blockIndex} className="msg-block">
        {lines.map((line, lineIndex) => (
          <span key={lineIndex}>
            {renderInline(line, `${blockIndex}-${lineIndex}`)}
            {lineIndex < lines.length - 1 && <br />}
          </span>
        ))}
      </p>
    )
  })
}
