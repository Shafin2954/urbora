const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1920,height:1080}});
const errs=[];pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
await pg.goto('http://127.0.0.1:8765/mg.html');await pg.evaluate(()=>window.ready);
const plan=JSON.parse(process.argv[2]);
for(const [id,ts] of Object.entries(plan))for(const t of ts){await pg.evaluate(([id,t])=>render(id,t),[id,t]);await pg.waitForTimeout(80);await pg.screenshot({path:`stills/${id}_${t}.png`})}
console.log('errors',errs);await b.close()})();
