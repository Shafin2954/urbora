"""Deterministic checks for the Round 1 form answers (ROUND1_FORM.md).

The "qualifier" gate of the form review loop (ROUND1_REVIEW.md). It checks what a
script can check reliably, so the reviewer agents can spend their attention on
judgement:

1. Word limits per answer (the form rejects text over the limit).
2. Team rules: the current name, no hotline, no blaming shops or officers,
   the prior-work disclosure is present.
3. AI-writing tells: em dashes, stock AI vocabulary, "not X but Y" frames,
   bold lead-ins, triplet lists, and flat sentence rhythm.

Usage:  python scripts/form_check.py [path]   (exit code 1 on any hard failure)
        python scripts/form_check.py --paste [path]   writes ROUND1_PASTE.txt: every answer
        with each paragraph on one line, ready to paste into the form boxes.
Only the text under "## <answer> (max N words)" headings is checked; Part 0 and
the team notes are ours, not the form's.
"""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

SECTION = re.compile(r"^## (.+?) \(max (\d+) words\)", re.M)

# Hard rules: any hit fails the gate.
BANNED = {
    "old name": r"\b(Agrosfeer|Sudin|Jigai|Urbor(?!a))\b|সুদিন",
    "hotline": r"16123|hotline|call cent(?:re|er)|Krishi Call",
    "blame": r"what the shop pushes|earns from what he sells|sells what pays|greedy|"
             r"push(?:es)? (?:the )?(?:product|what)|officers? (?:fail|ignore)",
}
REQUIRED = {"prior-work disclosure": r"Hackathon"}

# Soft rules: counted into the AI-tell index.
AI_WORDS = [
    "leverage", "seamless", "seamlessly", "empower", "empowering", "empowers", "robust",
    "holistic", "game-changer", "game changer", "revolutionize", "revolutionise",
    "cutting-edge", "unlock", "harness", "transformative", "landscape", "ecosystem",
    "crucial", "pivotal", "innovative", "delve", "foster", "bridge the gap", "at the heart of",
    "tailored", "testament", "navigate", "furthermore", "moreover", "additionally",
    "in today's", "ever-evolving", "paradigm", "synergy", "streamline", "comprehensive",
    "state-of-the-art", "a myriad", "plethora", "vibrant", "underscore", "it's worth noting",
    "whether you're", "imagine a", "stands as", "serves as a", "not just", "not only",
]
NOT_BUT = re.compile(r"\bnot (?:just |only |merely )?[^.;:]{1,40}?,? but\b|\bisn't just\b|"
                     r"\bit's not about\b", re.I)
CONTRAST = re.compile(r"instead of|rather than|, not (?:a|an|the|from|by|just)|"
                      r"doesn't [a-z]+[^.]{0,40}\. It", re.I)
LABEL = re.compile(r"(?m)(?:^|(?<=\. ))(?:\d+\.\s+)?[A-Z][a-z]+(?: [a-z]+){0,3}[.:] (?=[A-Z])")
TRIPLET = re.compile(r"\b[\w'-]+(?: [\w'-]+){0,2}, [\w'-]+(?: [\w'-]+){0,2},? (?:and|or) "
                     r"[\w'-]+", re.I)


def sections(text: str) -> list[tuple[str, int, str]]:
    heads = list(SECTION.finditer(text))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end]
        body = re.split(r"^---\s*$|^## ", body, maxsplit=1, flags=re.M)[0]
        body = body.split("\n", 1)[1] if "\n" in body else ""   # drop the heading's tail
        out.append((m.group(1).strip(), int(m.group(2)), body.strip()))
    return out


def words(body: str) -> int:
    plain = re.sub(r"\*\*|__|`", "", body)
    plain = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", plain, flags=re.M)
    return len(plain.split())


def sentences(body: str) -> list[str]:
    plain = re.sub(r"\*\*|`", "", body)
    plain = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", plain, flags=re.M)
    parts = re.split(r"(?<=[.!?।])\s+|\n\s*\n", plain)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def tells(body: str) -> dict:
    low = body.lower()
    n = max(words(body), 1)
    sent = sentences(body)
    lengths = [len(s.split()) for s in sent]
    cv = (statistics.pstdev(lengths) / statistics.mean(lengths)) if len(lengths) > 2 else 0.0
    hits = [w for w in AI_WORDS if re.search(rf"\b{re.escape(w)}\b", low)]
    t = {
        "em_dash": body.count("—") + body.count(" -- "),
        "ai_words": hits,
        "not_but": len(NOT_BUT.findall(body)),
        "bold_leadins": len(re.findall(r"\*\*[^*]{2,60}\*\*", body)),
        "triplets_per_100w": round(100 * len(TRIPLET.findall(body)) / n, 1),
        "colons_per_100w": round(100 * body.count(":") / n, 1),
        "sentence_cv": round(cv, 2),
        "contrast_per_100w": round(100 * len(CONTRAST.findall(body)) / n, 1),
        "label_leadins": len(LABEL.findall(body)),
    }
    # Index: 0 is clean. Each tell adds points; a flat rhythm (cv < 0.4) adds too.
    idx = (3 * t["em_dash"] + 4 * len(hits) + 4 * t["not_but"] + 1 * t["bold_leadins"]
           + max(0.0, t["triplets_per_100w"] - 1.5) * 3
           + max(0.0, t["colons_per_100w"] - 1.5) * 2
           + (max(0.0, 0.4 - cv) * 20 if lengths else 0)
           + max(0.0, t["contrast_per_100w"] - 1.0) * 2 + 2 * t["label_leadins"])
    t["ai_tell_index"] = round(idx, 1)
    return t


def main(path: str = "ROUND1_FORM.md") -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    text = Path(path).read_text(encoding="utf-8")
    secs = sections(text)
    if not secs:
        print(f"No '## <answer> (max N words)' sections found in {path}")
        return 1
    fails: list[str] = []
    answers = "\n".join(b for _, _, b in secs)
    print(f"{'answer':<44} {'words':>11}  tell-index  notes")
    for name, limit, body in secs:
        n, t = words(body), tells(body)
        over = n > limit
        if over:
            fails.append(f"{name}: {n} words, limit {limit}")
        notes = []
        if t["em_dash"]:
            notes.append(f"em-dash x{t['em_dash']}")
        if t["ai_words"]:
            notes.append("ai-words: " + ", ".join(t["ai_words"]))
        if t["not_but"]:
            notes.append(f"not-X-but-Y x{t['not_but']}")
        if t["bold_leadins"]:
            notes.append(f"bold lead-ins x{t['bold_leadins']}")
        if t["sentence_cv"] < 0.4:
            notes.append(f"flat rhythm (cv {t['sentence_cv']})")
        if t["contrast_per_100w"] > 1.0:
            notes.append(f"contrast frames {t['contrast_per_100w']}/100w")
        if t["label_leadins"]:
            notes.append(f"label lead-ins x{t['label_leadins']}")
        if t["triplets_per_100w"] > 1.5:
            notes.append(f"triplets {t['triplets_per_100w']}/100w")
        flag = "OVER" if over else "ok"
        print(f"{name[:44]:<44} {n:>4}/{limit:<4}{flag:>3}  {t['ai_tell_index']:>9}  "
              + "; ".join(notes))
    for rule, pat in BANNED.items():
        for m in re.finditer(pat, answers, flags=re.I):
            fails.append(f"{rule}: '{m.group(0)}'")
    for rule, pat in REQUIRED.items():
        if not re.search(pat, answers):
            fails.append(f"missing {rule}")
    print()
    if fails:
        print("HARD FAILS:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("Hard gates: all pass.")
    return 0


def paste(path: str = "ROUND1_FORM.md", out: str = "ROUND1_PASTE.txt") -> int:
    """Unwrap each answer's paragraphs so the form boxes get no stray line breaks."""
    text = Path(path).read_text(encoding="utf-8")
    title = re.search(r"^## Idea title\s*\n+(.+?)\n", text, flags=re.M)
    parts = [f"IDEA TITLE\n\n{title.group(1).strip()}"] if title else []
    for name, limit, body in sections(text):
        paras = [" ".join(line.strip() for line in p.splitlines())
                 for p in re.split(r"\n\s*\n", body) if p.strip()]
        parts.append(f"{name.upper()} ({words(body)}/{limit} words)\n\n" + "\n\n".join(paras))
    Path(out).write_text("\n\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    if "--paste" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--paste"]
        sys.exit(paste(*args[:1]))
    sys.exit(main(*sys.argv[1:2]))
