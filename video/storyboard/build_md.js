// Writes video/FINAL_STORYBOARD.md from shots.js. Run from the repo root:
//   node video/storyboard/build_md.js
const fs = require('fs');
const path = require('path');
const { BRAND, STYLE, CAST, ACTS, SHOTS, REPLICAS } = require('./shots.js');

const fmt = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
const TEX = { HF: 'Live action (Higgsfield)', HYP: 'Line art (HTML motion graphics)', REC: 'Real app (recording or HTML replica)' };
const out = [];
const w = s => out.push(s);

w(`# ${BRAND.bn} ${BRAND.en}: final storyboard (Round 1 video, ${fmt(SHOTS[SHOTS.length - 1].t[1])})`);
w('');
w('Generated from `video/storyboard/shots.js` by `video/storyboard/build_md.js`. Edit the .js file, not this one.');
w('');
w('One film built from the three earlier storyboards: A (the family story) gives the heart, B (the quick ad) gives the pace and the proof, C (line art) gives the road that rolls up into a phone.');
w('');
w('## Timeline');
w('');
w('| Time | Shot | Act | Texture | Hook |');
w('|---|---|---|---|---|');
SHOTS.forEach(s => w(`| ${fmt(s.t[0])}–${fmt(s.t[1])} | ${s.id} ${s.title} | ${s.act} | ${s.tex.join(' + ')} | ${s.hook ? 'yes' : ''} |`));
w('');
w('## Cast (generate a character sheet for each before any shot; prompts refer to them as @NAME)');
w('');
CAST.forEach(c => w(`- **@${c.id}**, ${c.who}: ${c.ref}`));
w('');
w(`**Style line, appended to every Higgsfield prompt:** ${STYLE}`);
w('');
ACTS.forEach(a => {
  w(`## Act ${a.id}: ${a.name} (${fmt(a.t[0])}–${fmt(a.t[1])})`);
  w('');
  w(`_${a.job}_`);
  w('');
  SHOTS.filter(s => s.act === a.id).forEach(s => {
    w(`### ${s.id} · ${fmt(s.t[0])}–${fmt(s.t[1])} (${s.t[1] - s.t[0]} s) · ${s.title}`);
    w('');
    w(`From: ${s.from} · Texture: ${s.tex.map(t => TEX[t]).join(', ')}`);
    if (s.hook) w(`\n**Hook:** ${s.hook}`);
    w(`\n**Picture:** ${s.pic}`);
    w(`\n**Camera:** ${s.cam}`);
    if (s.vo.length) { w('\n**Sound:**'); s.vo.forEach(v => w(`- ${v.who}: ${v.bn} (${v.en})`)); }
    if (s.sfx) w(`- SFX: ${s.sfx}`);
    if (s.ost) w(`\n**On screen:** ${s.ost}`);
    if (s.label.length) w(`\n**Labels:** ${s.label.join('; ')}`);
    const hf = s.hf ? (Array.isArray(s.hf) ? s.hf : [s.hf]) : [];
    hf.forEach((h, i) => w(`\n**Higgsfield prompt${hf.length > 1 ? ` ${i + 1}` : ''} (16:9):**\n\n> ${h}`));
    if (s.hyp) w(`\n**Motion graphics:** ${s.hyp}`);
    if (s.rec) w(`\n**App screen:** ${s.rec} (see below)`);
    if (s.note) w(`\n**Note:** ${s.note}`);
    w('');
  });
});
w('## App screens (one real run of Mahmud\'s case feeds all of them)');
w('');
REPLICAS.forEach(r => w(`- **${r.id} ${r.name}** (${r.shots}), from \`${r.page}\`: ${r.spec}`));
w('');
w('## Honesty');
w('');
w('- Credits line: dramatization · AI-generated footage (Higgsfield) · keypad shown in simulator (CLAUDE.md rules 13 and 15).');
w('- Every number on screen comes from the real run. Blanks such as "__ গ্রাম" are filled from that output, never typed.');
w('- No generated shot shows a readable phone screen; screens are composited from the replicas.');
w('');
fs.writeFileSync(path.join(__dirname, '..', 'FINAL_STORYBOARD.md'), out.join('\n'));
console.log('wrote video/FINAL_STORYBOARD.md');
