const CONFIG={token:'0xa02d9a9a5f5453463aa4855f62e47d9cc27086d9',chain:'base',pairLabel:'FUND / WETH',refreshSec:30};
let state={price:0,liq:0,vol24:0,mcap:0,fdv:0,holders:169,txns24:{buys:0,sells:0,makers:0},reserves:{base:0,quote:0},priceChange:0,poolName:null};
let priceHistory=[];

// Load from initial inline data if present
function loadInline(){
  try{
    const el=document.getElementById('initial-data');
    if(!el) return false;
    const d=JSON.parse(el.textContent);
    parseData(d);
    return true;
  }catch(e){console.error('inline parse',e);return false;}
}

async function fetchLocal(){
  try{
    const r=await fetch('./data.json?r='+Date.now());
    if(!r.ok) throw new Error(r.status);
    const d=await r.json();
    parseData(d);
    return true;
  }catch(e){console.error('local fetch',e);return false;}
}

function parseData(d){
  const t=d.token||{};
  const p=d.pool||{};
  const vol24h = t.volume_24h || p.volume_24h || 0;
  const reservesUSD = p.reserve_usd || t.total_reserve_usd || 0;
  const tx24 = p.txns_24h || {buys:0,sells:0};

  state={
    price: t.price_usd||0,
    liq: reservesUSD,
    vol24: vol24h,
    mcap: t.market_cap||t.fdv||0,
    fdv: t.fdv||0,
    holders:169,
    txns24:{buys:tx24.buys||0,sells:tx24.sells||0,makers:tx24.buyers+tx24.sellers||0},
    reserves:{base:0,quote:0},
    priceChange: p.price_change_24h || 0,
    poolName: p.name || 'FUND / WETH',
    totalSupply: t.total_supply || 1000000000,
    updated: d.updated_at
  };

  if(p.base_price && p.quote_price){
    // rough reserve estimate from price and liq
    const half=reservesUSD/2;
    state.reserves.base=half/(t.price_usd||1);
    state.reserves.quote=half/(p.quote_price||1);
  }

  // store history point
  const now=Date.now();
  priceHistory.push({t:now,p:state.price});
  priceHistory=priceHistory.filter(h=>now-h.t<90*864e5); // 90 days
  saveHistory();
}

function impact(amountUSD){
  const liqUSD=state.liq;
  if(!liqUSD) return 0;
  return (amountUSD/(liqUSD+amountUSD))*100;
}

function fmtCompact(n){
  if(!n&&n!==0)return'--';
  if(n>=1e9)return(n/1e9).toFixed(2)+'B';
  if(n>=1e6)return(n/1e6).toFixed(2)+'M';
  if(n>=1e3)return(n/1e3).toFixed(2)+'K';
  if(n>=1)return n.toLocaleString('en-US',{maximumFractionDigits:2});
  return n.toFixed(6);
}
function fmtPct(n,d=2){if(!n&&n!==0)return'--';return(n>=0?'+':'')+n.toFixed(d)+'%';}
function cls(el,c){if(!el)return;el.classList.remove('up','down');if(c)el.classList.add(c);}

function updateDOM(){
  const el=id=>document.getElementById(id);

  const pEl=el('price');
  if(pEl){
    const old=parseFloat(pEl.dataset.val||0);
    pEl.textContent='$'+state.price.toFixed(8);
    pEl.dataset.val=state.price;
    if(old){cls(pEl,state.price>old?'up':'down');pEl.parentElement.classList.add('updated');setTimeout(()=>pEl.parentElement.classList.remove('updated'),900);}
  }

  const pcEl=el('price-change');if(pcEl){pcEl.textContent=fmtPct(state.priceChange);cls(pcEl,state.priceChange>=0?'up':'down');}
  const lEl=el('liquidity');if(lEl)lEl.textContent='$'+fmtCompact(state.liq);
  const lpEl=el('liq-pct');if(lpEl)lpEl.textContent='Pool: '+(state.poolName||'--');
  const mEl=el('mcap');if(mEl)mEl.textContent='$'+fmtCompact(state.mcap||state.fdv);
  const fEl=el('fdv');if(fEl)fEl.textContent='FDV: $'+fmtCompact(state.fdv);
  const vEl=el('volume');if(vEl)vEl.textContent='$'+fmtCompact(state.vol24);
  const vcEl=el('vol-change');if(vcEl)vcEl.textContent='24h vol';
  const hEl=el('holders');if(hEl)hEl.textContent=state.holders;
  const tEl=el('txns');if(tEl)tEl.textContent=(state.txns24.buys+state.txns24.sells);
  const tcEl=el('txn-change');if(tcEl)tcEl.textContent=`${state.txns24.buys} buy / ${state.txns24.sells} sell`;
  const rbEl=el('reserve-base');if(rbEl)rbEl.textContent=fmtCompact(state.reserves.base)+' FUND';
  const rqEl=el('reserve-quote');if(rqEl)rqEl.textContent=fmtCompact(state.reserves.quote)+' WETH';
  [50,100,500,1000].forEach(a=>{
    const iEl=el(`impact-${a}`);if(iEl){const imp=impact(a);iEl.textContent=imp.toFixed(2)+'%';iEl.style.color=imp>10?'var(--down)':imp>5?'var(--orange)':'var(--up)';}
  });
  const tsEl=el('last-update');if(tsEl)tsEl.textContent=state.updated?new Date(state.updated).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'--:--:--';
}

/* SVG Chart */
function renderChart(){
  const svg=document.getElementById('chart');
  const overlay=document.getElementById('chart-overlay');
  if(!svg||!overlay)return;

  const btn=document.querySelector('.interval.active');
  const interval=btn?btn.dataset.i:'24h';
  let ms;
  switch(interval){case'1h':ms=3600e3;break;case'6h':ms=21600e3;break;case'24h':ms=86400e3;break;case'7d':ms=604800e3;break;case'30d':ms=2592000e3;break;default:ms=86400e3;}
  const cutoff=Date.now()-ms;
  const data=priceHistory.filter(h=>h.t>cutoff);

  if(data.length<2){
    overlay.style.display='flex';
    overlay.textContent='Collecting price data... ('+priceHistory.length+' points)';
    // still show history line if we have any at all
    if(priceHistory.length<2){svg.innerHTML='';return;}
  }else overlay.style.display='none';

  const w=800,h=300;
  const prices=data.map(d=>d.p);
  const min=Math.min(...prices)*.9995;
  const max=Math.max(...prices)*1.0005;
  const range=max-min||1;
  const x=i=>w*(i/(data.length-1));
  const y=p=>h-((p-min)/range)*h;

  let grid='';
  for(let i=0;i<=4;i++){const yy=h*(i/4);grid+=`<line x1="0" y1="${yy}" x2="${w}" y2="${yy}" class="chart-grid"/>`;}
  for(let i=0;i<data.length;i+=Math.ceil(data.length/6)){const xx=x(i);grid+=`<line x1="${xx}" y1="0" x2="${xx}" y2="${h}" class="chart-grid"/>`;}

  let area=`M0 ${h} `;data.forEach((d,i)=>area+=`L${x(i)} ${y(d.p)} `);area+=`L${w} ${h} Z`;
  let line=`M${x(0)} ${y(data[0].p)} `;data.forEach((d,i)=>{if(i)line+=`L${x(i)} ${y(d.p)} `;});

  const last=data[data.length-1];
  const lx=x(data.length-1),ly=y(last.p);
  const tipText=`$${last.p.toFixed(8)}`;
  const tipW=tipText.length*6.5+16;
  const tipH=22;
  const tipX=Math.min(lx,w-tipW-4);
  const tipY=Math.max(ly-tipH-10,4);

  svg.innerHTML=grid+
    `<path d="${area}" class="chart-area"/>`+
    `<path d="${line}" class="chart-line"/>`+
    `<circle cx="${lx}" cy="${ly}" r="4" fill="var(--accent)"/>`+
    `<g><rect x="${tipX}" y="${tipY}" width="${tipW}" height="${tipH}" class="tooltip-bg"/>`+
    `<text x="${tipX+tipW/2}" y="${tipY+16}" text-anchor="middle" fill="var(--fg)" font-size="11">${tipText}</text></g>`;

  const hiEl=document.getElementById('chart-high');if(hiEl)hiEl.textContent='High: $'+max.toFixed(8);
  const loEl=document.getElementById('chart-low');if(loEl)loEl.textContent='Low: $'+min.toFixed(8);
}

/* History */
function saveHistory(){try{localStorage.setItem('fund_price_hist',JSON.stringify(priceHistory));}catch(e){}}
function loadHistory(){try{const s=localStorage.getItem('fund_price_hist');if(s){const parsed=JSON.parse(s);return parsed.filter(h=>typeof h.p==='number');}}catch(e){console.error(e)}return [];}

/* Intervals */
function bindIntervals(){
  document.querySelectorAll('.interval').forEach(b=>{
    b.addEventListener('click',()=>{
      document.querySelectorAll('.interval').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      renderChart();
    });
  });
}

/* Main */
async function init(){
  priceHistory=loadHistory();
  bindIntervals();

  // try inline first, then local fetch
  const inlineOk=loadInline();
  if(!inlineOk) await fetchLocal();
  updateDOM();
  renderChart();

  // poll local json every N seconds
  setInterval(async()=>{
    const ok=await fetchLocal();
    if(ok){updateDOM();renderChart();}
  }, CONFIG.refreshSec*1000);
}

init();
