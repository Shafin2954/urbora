# Logo brief (for the team, Canva, Figma or an image model)

## The idea the logo must carry

"The one who knows, and tells you straight, for your own field." Farming reached through a
voice or a phone, without looking like a tech product.

## Three concepts to try (pick one, then refine)

1. **Paddy ear that listens.** A ripe paddy ear bending over into the shape of an ear or a
   speech bubble. Reads as "listens to the field". Works well as a small icon.
2. **Field in a speech bubble.** A rounded speech bubble whose lower half holds three
   furrow lines (a ploughed field), with one seedling rising out of the top. Reads as
   "conversation about your land". Plain and friendly, strong for the SMS and voice story.
3. **Leaf plus signal.** A single paddy leaf with two quiet signal arcs, like the placeholder
   mark now on the site (`frontend/src/components/BrandMark.jsx`). The safest, and closest
   to telecom brands such as GP.

## Wordmark

- **Bangla name first, Latin second, both always together.** Most users read Bangla; judges
  and partners read the Latin.
- Bangla set in **Tiro Bangla** (serif, trustworthy) or hand-drawn along its lines; Latin in
  **Hind Siliguri SemiBold** with slightly open tracking.
- The Bangla name is the larger of the two, or they are equal. Never Latin-dominant.

## Colours

- **Full colour.** Mark in Shyamol green `#0F5C3B` with one Dhani gold `#E3A92F` detail (the
  grain, the seedling tip). Wordmark in Shyamol or Ink `#14221A`.
- **On green.** Mark and wordmark in white, the gold detail kept.
- **One colour.** All Shyamol, or all white.
- **Never.** Gradients, shadows, 3D, neon, robot or circuit imagery, more than 3 colours.
  Akash blue is kept for the phone and channel UI, so the logo stays green and gold.

## Deliverables (put them in `brand/assets/logo/`)

| File | Use |
|---|---|
| `logo-full.svg` / `.png` (2000px) | Mark + Bangla + Latin wordmark, on light backgrounds |
| `logo-full-white.svg` | The same, for green or photo backgrounds |
| `mark.svg` / `mark-512.png` | Mark alone: app icon, favicon, social avatar |
| `mark-maskable-512.png` | Mark centred in the safe zone (PWA icon) |
| `wordmark-bn.svg`, `wordmark-en.svg` | Wordmarks alone, for the video end card |

When these land, replace `frontend/public/icon.svg`, `icon-maskable.svg` and
`components/BrandMark.jsx` with the new mark.

## Rules

- Clear space on every side equal to the height of the mark's main shape.
- Minimum size: mark 24px, full logo 120px wide.
- Recognisable in one colour at 24px on a cheap phone screen: test it before approving.

## Prompt starter (Canva or Figma AI, or an image model)

> Minimal flat vector logo mark for a Bangladeshi farm advice service. A ripe paddy ear
> bending gently into the shape of a speech bubble. Deep green #0F5C3B with a single warm
> gold #E3A92F grain accent, on a white background. Simple geometric shapes, even stroke
> weight, no gradient, no shadow, no text, works at 24 pixels, calm and trustworthy, rooted in
> rural Bengal.
