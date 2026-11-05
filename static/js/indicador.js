"use strict";
/* Indicador flutuante: mostra, por cima de tudo, se o Núcleo está ouvindo, pensando ou falando. */
const CORES = {normal:[217,168,69], atencao:[232,137,58], risco:[224,72,62], sucesso:[143,196,154], nuvem:[192,139,208], aprendendo:[236,214,150]};
const ROTULOS = {espera:"Em espera", ouvindo:"Ouvindo você…", conversa:"Escutando…", sentinela:"Aguardando a palavra",
  transcrevendo:"Entendendo…", analisando:"Pensando…", falando:"Falando…", confirmar:"Aguardando confirmação", claude:"Consultando a nuvem"};
let p = {estado:"espera", nivel:0, humor:"normal", ativo:false, vigia:false};
let cor = [217,168,69], energia = 0, t = 0;
const cv = document.getElementById("cv"), ctx = cv.getContext("2d");
function quadro(){
  const alvoCor = CORES[p.humor] || CORES.normal;
  cor = cor.map((v,i) => v + (alvoCor[i]-v)*.08);
  const alvo = {espera:.1, sentinela:.2, conversa:.3, ouvindo:.4, transcrevendo:.6, analisando:.8, falando:.55}[p.estado] || .15;
  energia += (alvo + p.nivel*2 - energia) * .12;
  t += .02 + energia*.05;
  const W = cv.width, c = W/2, rgb = cor.map(Math.round).join(",");
  ctx.clearRect(0,0,W,W);
  const g = ctx.createRadialGradient(c,c,8,c,c,c);
  g.addColorStop(0,`rgba(${rgb},${.35+energia*.3})`); g.addColorStop(1,"rgba(0,0,0,0)");
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c,c,c,0,Math.PI*2); ctx.fill();
  ctx.save(); ctx.translate(c,c); ctx.rotate(t);
  ctx.strokeStyle = `rgba(${rgb},.8)`; ctx.lineWidth = 6;
  for (let k=0;k<12;k++){ if (k%3===0) continue; ctx.beginPath(); ctx.arc(0,0,92,k*Math.PI/6,k*Math.PI/6+.38); ctx.stroke(); }
  ctx.restore();
  const r = 46 + Math.sin(t*3)*4*energia + p.nivel*40;
  const gi = ctx.createRadialGradient(c-12,c-14,4,c,c,r);
  gi.addColorStop(0,"#FFF6DD"); gi.addColorStop(.45,`rgb(${rgb})`); gi.addColorStop(1,"rgba(40,26,8,.95)");
  ctx.fillStyle = gi; ctx.shadowColor = `rgba(${rgb},.9)`; ctx.shadowBlur = 30 + energia*30;
  ctx.beginPath(); ctx.arc(c,c,r,0,Math.PI*2); ctx.fill(); ctx.shadowBlur = 0;
  requestAnimationFrame(quadro);
}
async function atualizar(){
  try {
    const r = await fetch("/api/presenca",{credentials:"same-origin"});
    if (r.ok){ p = await r.json();
      document.getElementById("rot").textContent = p.legenda && p.estado === "falando" ? p.legenda : (ROTULOS[p.estado] || "Em espera");
      document.getElementById("vigia").textContent = p.vigia ? "vigia ativo" : ""; }
  } catch(e){}
  setTimeout(atualizar, 350);
}
document.getElementById("caixa").addEventListener("dblclick", () => { if (window.pywebview) window.pywebview.api.mostrar_principal(); });
document.getElementById("caixa").addEventListener("click", ev => { if (ev.detail === 1) setTimeout(() => {}, 0); });
quadro(); atualizar();
