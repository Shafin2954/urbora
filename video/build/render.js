// Renders mg.html scenes to MP4: every frame is render(id, t), screenshotted and piped to ffmpeg.
const { chromium } = require('playwright'); const { spawn } = require('child_process');
const FF = process.env.FF || 'ffmpeg';
(async () => {
  const ids = process.argv.slice(2), fps = 30;
  const b = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {}); const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await pg.goto('http://127.0.0.1:8765/mg.html'); await pg.evaluate(() => window.ready);
  for (const id of ids) {
    const dur = await pg.evaluate(id => window.SCENES[id], id), n = Math.round(dur * fps);
    const ff = spawn(FF, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', `out/${id}.mp4`]);
    for (let i = 0; i < n; i++) {
      await pg.evaluate(([id, t]) => render(id, t), [id, i / fps]);
      await pg.evaluate(() => Promise.all([...document.images].map(im => im.complete ? 0 : new Promise(r => im.onload = r))));
      const buf = await pg.screenshot({ type: 'png' }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log(id, n, 'frames');
  }
  await b.close();
})();
