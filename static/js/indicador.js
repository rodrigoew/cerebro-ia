"use strict";
/* Indicador flutuante: uma cápsula pequena que mostra se o Núcleo está ouvindo, pensando ou falando. */
const CORES = {normal:[217,168,69], atencao:[232,137,58], risco:[224,72,62], sucesso:[143,196,154], nuvem:[192,139,208], aprendendo:[236,214,150]};
const ROTULOS = {espera:"Núcleo", sentinela:"Aguardando", conversa:"Escutando", ouvindo:"Ouvindo…",
  transcrevendo:"Entendendo…", analisando:"Pensando…", falando:"Falando…", confirmar:"Confirme na tela", claude:"Na nuvem…"};
const ATIVOS = new Set(["ouvindo","transcrevendo","analisando","falando","confirmar","claude"]);
let p = {estado:"espera", nivel:0, humor:"normal"};
let cor = [217,168,69], energia = 0, t = 0;
const cv = document.getElementById("cv"), ctx = cv.getContext("2d");
function quadro(){
  const alvoCor = CORES[p.humor] || CORES.normal;
  cor = cor.map((v,i) => v + (alvoCor[i]-v)*.1);
  const alvo = ATIVOS.has(p.estado) ? .5 + p.nivel*2 : .08;
  energia += (alvo - energia) * .15;
  t += .03 + energia*.08;
  const W = cv.width, c = W/2, rgb = cor.map(Math.round).join(",");
  ctx.clearRect(0,0,W,W);
  ctx.save(); ctx.translate(c,c); ctx.rotate(t);
  ctx.strokeStyle = `rgba(${rgb},${.5+energia*.4})`; ctx.lineWidth = 3;
  for (let k=0;k<6;k++){ if (k%3===2) continue; ctx.beginPath(); ctx.arc(0,0,22,k*Math.PI/3,k*Math.PI/3+.7); ctx.stroke(); }
  ctx.restore();
  const r = 11 + Math.sin(t*3)*1.5*energia + p.nivel*6;
  const g = ctx.createRadialGradient(c-3,c-4,1,c,c,r);
  g.addColorStop(0,"#FFF6DD"); g.addColorStop(.5,`rgb(${rgb})`); g.addColorStop(1,"rgba(40,26,8,.95)");
  ctx.fillStyle = g; ctx.shadowColor = `rgba(${rgb},.8)`; ctx.shadowBlur = 6 + energia*10;
  ctx.beginPath(); ctx.arc(c,c,r,0,Math.PI*2); ctx.fill(); ctx.shadowBlur = 0;
  requestAnimationFrame(quadro);
}
async function atualizar(){
  try {
    const r = await fetch("/api/presenca",{credentials:"same-origin"});
    if (r.ok){
      p = await r.json();
      document.getElementById("rot").textContent = ROTULOS[p.estado] || "Núcleo";
      document.getElementById("capsula").classList.toggle("ativa", ATIVOS.has(p.estado));
    }
  } catch(e){}
  setTimeout(atualizar, 350);
}
document.getElementById("capsula").addEventListener("dblclick", () => { if (window.pywebview) window.pywebview.api.mostrar_principal(); });
quadro(); atualizar();
