# Website image prompts (ChatGPT image generation)

For the উর্বরা home page redesign. Generate each image in ChatGPT, save it with the
file name given, and drop it in `frontend/public/img/`. I will crop, compress to WebP and wire it in.

**Rules for every image**
- Paste the **style block** first, then the image prompt, in the same message.
- No text, letters, logos or watermarks inside the image. Phone screens stay **blank white**:
  the site puts the real Urbora screens into them, so they can change as you click.
- If a result looks plastic or "AI" (glossy skin, perfect teeth, extra fingers), regenerate
  with: *"More documentary, less polished. Natural skin texture, real hands."*
- The site will mark these images as illustrative (প্রতীকী ছবি), because no generated image
  may pass as a real farmer or a real record (CLAUDE.md "no fake content").

---

## Style block (paste before every prompt)

```
Documentary photograph, rural Bangladesh, shot on a full-frame camera with a 35mm lens,
natural light only. Real people, real places, real textures: weathered hands, cotton lungi
and gamchha, dust, mud, worn plastic sandals. Colour grade: warm and calm, muted greens and
straw golds, soft highlights, no heavy saturation, no HDR, no lens flare. Nothing staged
or glossy, no stock-photo smiles, no text, no logos, no watermark.
```

---

## A. Hero and phones (most important, do these first)

### 1. `hero-field.jpg` — hero background · 16:9, landscape, largest size
```
A wide, low morning view across a green boro rice field in northern Bangladesh, about an
hour after sunrise. Soft mist lies over the far end of the field, a line of palm and mango
trees on the horizon, a thin raised earth path (ail) runs diagonally into the distance.
One farmer, small in the frame on the right third, walks the path with a phone in his hand.
The left half of the image is calm and uncluttered (mostly sky and soft field) so text can
sit on it. Golden low sun from the right, long soft shadows.
```

### 2. `phone-android-hand.png` — the smartphone · 4:5, portrait
```
Close-up of a Bangladeshi farmer's weathered, sun-darkened hand holding a budget Android
smartphone (plain black plastic, slightly scuffed, thin bezels) facing the camera almost
straight on, screen tilted only slightly. The screen is completely blank, pure flat white,
evenly lit, no reflections, no icons. Background: a softly blurred green rice field in
morning light. The phone fills about 60% of the frame height, sharp focus on the screen
edges and the fingers.
```

### 3. `phone-button-hand.png` — the button phone · 4:5, portrait
```
Close-up of an older Bangladeshi farmer's hand holding a basic keypad feature phone
(small colour screen, physical number keys, worn rubber keys, like a Nokia 105 or
Symphony button phone) facing the camera almost straight on. The small screen is
completely blank, flat pure white, no reflection. Background: softly blurred mud wall of a
village house with a hanging jute sack, warm afternoon light. Sharp focus on the keypad
and the screen edges.
```

### 4. `farmer-call.jpg` — someone on a voice call · 3:2, landscape
```
A Bangladeshi farmer in his fifties, standing at the edge of his potato field in winter
morning light, holding a basic phone to his ear and listening carefully, his other hand
resting on a hoe. Slight haze, green potato rows running away from camera. He is not
smiling for the camera; he is concentrating on the call. Medium shot, farmer on the left
third, field and sky on the right.
```

---

## B. "Every problem, one advisor" row (8 square tiles)

These make the consultancy idea visible: not just disease, every question a farmer has
across the season. Each is **1:1, square**. Same style block.

### 5. `topic-crop-choice.jpg` — what to grow this season
```
A farmer squatting at the edge of a freshly ploughed, empty field at dawn, holding a small
handful of seeds in his open palm and looking out over the bare soil, as if deciding what to
sow. Close-medium shot, the ploughed furrows leading away.
```

### 6. `topic-soil.jpg` — soil and fertiliser
```
Two cupped hands holding a clump of dark, moist, crumbly field soil, a few fine rice roots
visible in it, low side light showing the texture. Background: blurred green paddy.
Macro-style close-up.
```

### 7. `topic-pest-disease.jpg` — pest and disease
```
Close-up of a rice plant leaf held between a farmer's fingers, showing brown spots and
yellowing along the edge (a real crop problem, not dramatic), the rest of the field softly
out of focus behind. Natural daylight.
```

### 8. `topic-water.jpg` — irrigation and water
```
Clear water flowing from a shallow tube-well pipe into a green rice field through a small
cut in the earth bund, bright morning light catching the water, the farmer's bare feet and
rolled lungi at the edge of the frame.
```

### 9. `topic-weather.jpg` — weather
```
A dark monsoon rain cloud building over a wide green paddy field in Bangladesh, the light
still bright on the field in front, a farmer in the middle distance looking up at the sky.
Wide shot, dramatic but calm.
```

### 10. `topic-money.jpg` — costs and profit
```
A farmer and his wife sitting on the veranda of a tin-roofed village house, looking together
at a simple phone screen held between them (screen not visible to camera), a small notebook
and pencil beside them. Warm late-afternoon light, quiet and serious.
```

### 11. `topic-inputs.jpg` — buying seed, fertiliser, spray
```
Inside a small village agricultural input shop in Bangladesh: stacked sacks of fertiliser,
shelves of seed packets and spray bottles (labels blurred, no readable text), the
shopkeeper behind a wooden counter handing a bag to a farmer. Natural light from the open
shutter.
```

### 12. `topic-selling.jpg` — selling the harvest
```
A rural wholesale haat in the morning: rows of full jute sacks of potatoes and rice, a
farmer standing beside his sacks, a trader weighing a sack on an old iron scale. Busy but
not crowded, soft sunlight, dust in the air.
```

---

## C. Section backgrounds (soft, full-width, text sits on top)

### 13. `story-land.jpg` — "the same land gives less" · 21:9, very wide
```
A patchy, uneven rice field in late season, some plants thin and yellow, some healthy,
cracked dry soil visible between rows in the foreground, a lone farmer standing far away
looking over it. Muted, slightly overcast light. Plenty of empty space across the top half.
```

### 14. `closing-dawn.jpg` — the closing band, "স্বপ্ন ফলুক" · 21:9, very wide
```
A golden rice field ready for harvest at sunrise, heavy grain heads bending in the
foreground, the sun just above the horizon behind a line of trees, warm light, very calm.
The top half is soft glowing sky with room for a line of text.
```

---

## D. Wheat and paddy line art (you already sent two)

The two you sent (brown engraved wheat on paper, and sepia painted wheat) are good for
textures behind the text sections. Please send them at **full size** (at least 2400 px wide).
The screenshot I got is under 500 px per image. If you want a matching paddy one:

### 15. `paddy-engraving.png` · 16:9
```
Fine botanical engraving of ripe rice (paddy) stalks with drooping grain heads, dark brown
ink lines on warm textured handmade paper, soft diagonal window light across the paper,
lots of empty paper on the left side. No text, no border, no stamp.
```
