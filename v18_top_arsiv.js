"use strict";
// Reconstruct list rotations from each immutable published candidate pool.
(() => {
 const el=id=>document.getElementById(id), stamp=s=>new Date(s).toISOString().slice(0,16).replace('T',' ');
 let history=[], results=new Map(), revisions=[];
 function week(t){const d=new Date(t);d.setUTCHours(0,0,0,0);d.setUTCDate(d.getUTCDate()-(d.getUTCDay()+6)%7);return d.toISOString().slice(0,10);}
 function revisionsFor(n,now){const out=[]; for(let i=0;i<history.length;i++){const h=history[i], start=Date.parse(h.zaman),end=Math.min(now,i+1<history.length?Date.parse(history[i+1].zaman)-1:now);if(start>end)continue;
  const times=[start,...new Set(h.adaylar.map(r=>Date.parse(r.tarih)).filter(t=>t>start&&t<=end))].sort((a,b)=>a-b);let prev='';
  for(const t of times){const rows=h.adaylar.filter(r=>Date.parse(r.tarih)>t).slice(0,n),key=JSON.stringify(rows.map(r=>[r.id,r.secim,r.yuzde]));if(key===prev)continue;prev=key;out.push({t,rows,kind:t===start?'Yayın kaydı':'Saat bazlı liste değişimi'});}
 }return out.reverse();}
 function option(select,value,label){const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o);}
 function renderWeeks(){revisions=revisionsFor(Number(el('top-archive-size').value),Date.now());const s=el('top-archive-week'),old=s.value;s.replaceChildren();for(const w of new Set(revisions.map(x=>week(x.t))))option(s,w,w+' haftası (UTC)');if([...s.options].some(o=>o.value===old))s.value=old;renderVersions();}
 function renderVersions(){const s=el('top-archive-version');s.replaceChildren();revisions.forEach((r,i)=>{if(week(r.t)===el('top-archive-week').value)option(s,String(i),stamp(r.t)+' UTC · '+r.kind);});renderRows();}
 function renderRows(){const r=revisions[Number(el('top-archive-version').value)],body=el('top-archive-rows');body.replaceChildren();let w=0,l=0,p=0,u=0;if(!r||!el('top-archive-version').value){el('top-archive-summary').textContent='Henüz kayıt yok.';return;}
 r.rows.forEach((x,i)=>{const a=results.get(x.id);let grade='Bekliyor',score='—';if(a?.durum==='DOGRULANDI'&&a.sonuc){score=a.sonuc.skor??'—';const g=a.sonuc.toplam_gol;if(Number.isFinite(g)){if(g>Number(x.secim.split(' ')[0])){w++;grade='✅ Doğru';}else{l++;grade='❌ Yanlış';}}else{u++;grade='Skor incelenmeli';}}else p++;
 const tr=document.createElement('tr');for(const v of [i+1,x.mac+' / '+x.lig,stamp(x.tarih),x.secim.replace('UST','ÜST')+' · %'+x.yuzde,score,grade]){const td=document.createElement('td');td.textContent=v;tr.append(td);}body.append(tr);});el('top-archive-summary').textContent=`${r.rows.length} maç · ${w} doğru · ${l} yanlış · ${p} bekliyor · ${u} inceleme · Başarı: ${w+l?(100*w/(w+l)).toFixed(1)+'%':'—'}`;}
 async function load(){try{const [h,r]=await Promise.all(['v18_top_arsivi.json','v18_dogrulanan_sonuclar.json'].map(async f=>{const x=await fetch('./'+f,{cache:'no-store'});if(!x.ok)throw Error(f);return x.json();}));history=h.yayinlar;results=new Map(r.kayitlar.map(x=>[x.kimlik,x]));renderWeeks();}catch(e){el('top-archive-summary').textContent='TOP arşivi okunamadı: '+e.message;}}
 document.addEventListener('DOMContentLoaded',()=>{el('top-archive-size').addEventListener('change',renderWeeks);el('top-archive-week').addEventListener('change',renderVersions);el('top-archive-version').addEventListener('change',renderRows);el('refresh').addEventListener('click',load);load();});
})();
