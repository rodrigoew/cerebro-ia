"use strict";
/* Widget flutuante: um mini-Núcleo vivo.
   Parado: hora + próximo compromisso. Ouvindo: onda que segue a sua voz. Pensando: pontos em órbita.
   Falando: cresce e mostra a legenda. Risco: borda pulsa em vermelho. Passe o mouse para os atalhos. */
const HUMOR = {normal:null, atencao:[255,176,32], risco:[255,60,56], sucesso:[24,236,132], nuvem:[186,66,255], aprendendo:[236,214,150]};
const BASE = {ambar:[217,168,69], jarvis:[92,200,255]};
const CORES_J = {azul:[92,200,255], carmim:[255,38,88], roxo:[186,66,255], verde:[24,236,132], laranja:[255,118,18], grafite:[176,184,196]};
const ROTULOS = {sentinela:"aguardando", conversa:"escutando", ouvindo:"ouvindo", transcrevendo:"entendendo",
  analisando:"pensando", claude:"pensando", falando:"falando", confirmar:"confirme na tela"};
const ATIVOS = new Set(["ouvindo","transcrevendo","analisando","falando","confirmar","claude"]);
const PENSANDO = new Set(["transcrevendo","analisando","claude"]);
const TAM = {normal:[264,46], largo:[330,46], ouvindo:[300,46], grande:[440,70]};
let p = {estado:"espera", nivel:0, humor:"normal", tema:"ambar"};
let cor = [217,168,69], energia = 0, t = 0, tamAtual = "", hist = new Array(28).fill(0);
const $ = id => document.getElementById(id);
const cv = $("cv"), ctx = cv.getContext("2d"), onda = $("onda"), octx = onda.getContext("2d");

function alvoCor(){ return HUMOR[p.humor] || (p.tema === "jarvis" ? CORES_J[p.cor] || BASE.jarvis : BASE.ambar); }

function orbe(){
  const W = cv.width, c = W/2, rgb = cor.map(Math.round).join(","), jarvis = p.tema === "jarvis";
  ctx.clearRect(0,0,W,W);
  if (jarvis){
    ctx.globalCompositeOperation = "lighter";
    for (let k=0;k<5;k++){
      const inc = .35 + k*.5, rot = t*(.6+k*.15) + k;
      ctx.save(); ctx.translate(c,c); ctx.rotate(rot);
      ctx.strokeStyle = `rgba(${rgb},${.22+energia*.35})`; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.ellipse(0,0,24+Math.sin(t*2+k)*energia*3,24*Math.abs(Math.cos(inc+t*.3)),0,0,Math.PI*2); ctx.stroke();
      ctx.restore();
    }
    ctx.globalCompositeOperation = "source-over";
  } else {
    ctx.save(); ctx.translate(c,c); ctx.rotate(t);
    ctx.strokeStyle = `rgba(${rgb},${.45+energia*.45})`; ctx.lineWidth = 3;
    for (let k=0;k<6;k++){ if (k%3===2) continue; ctx.beginPath(); ctx.arc(0,0,29,k*Math.PI/3,k*Math.PI/3+.7); ctx.stroke(); }
    ctx.restore();
  }
  const r = 12 + Math.sin(t*3)*1.6*energia + p.nivel*7;
  const g = ctx.createRadialGradient(c-3,c-4,1,c,c,r);
  g.addColorStop(0, jarvis ? "#EAFBFF" : "#FFF6DD"); g.addColorStop(.5,`rgb(${rgb})`); g.addColorStop(1, jarvis ? "rgba(4,20,40,.95)" : "rgba(40,26,8,.95)");
  ctx.fillStyle = g; ctx.shadowColor = `rgba(${rgb},.85)`; ctx.shadowBlur = 8 + energia*14;
  ctx.beginPath(); ctx.arc(c,c,r,0,Math.PI*2); ctx.fill(); ctx.shadowBlur = 0;
  if (PENSANDO.has(p.estado)){                      // pontos em órbita enquanto pensa
    for (let k=0;k<3;k++){
      const a = t*2.4 + k*2.094, x = c + Math.cos(a)*30, y = c + Math.sin(a)*30*.55;
      ctx.fillStyle = `rgba(${rgb},${.55+.45*Math.sin(t*4+k)})`;
      ctx.beginPath(); ctx.arc(x,y,2.6,0,Math.PI*2); ctx.fill();
    }
  }
}

function desenharOnda(){
  if (p.estado !== "ouvindo" && p.estado !== "conversa") return;
  const W = onda.width, H = onda.height, n = hist.length, larg = W/n, rgb = cor.map(Math.round).join(",");
  octx.clearRect(0,0,W,H);
  for (let i=0;i<n;i++){
    const v = Math.max(.06, hist[i]), h = v*H*.9;
    octx.fillStyle = `rgba(${rgb},${.35 + v*.65})`;
    const x = i*larg + larg*.2, w = larg*.6;
    octx.beginPath(); octx.roundRect ? octx.roundRect(x,(H-h)/2,w,h,w/2) : octx.rect(x,(H-h)/2,w,h); octx.fill();
  }
}

function quadro(){
  const a = alvoCor(); cor = cor.map((v,i) => v + (a[i]-v)*.08);
  const alvo = ATIVOS.has(p.estado) ? .5 + p.nivel*2 : .1;
  energia += (alvo - energia) * .12;
  t += .025 + energia*.06;
  hist.push(p.estado === "ouvindo" ? Math.min(1, Math.sqrt(p.nivel)*1.1*(.55 + Math.random()*.45)) : hist[hist.length-1]*.85); hist.shift();
  orbe(); desenharOnda();
  requestAnimationFrame(quadro);
}

function ajustar(nome){
  if (nome === tamAtual) return;
  tamAtual = nome;
  document.body.classList.toggle("grande", nome === "grande");
  const [w,h] = TAM[nome];
  if (window.pywebview && pywebview.api && pywebview.api.ajustar_indicador) pywebview.api.ajustar_indicador(w,h);
}

function linha2(){
  const l2 = $("l2"); l2.classList.remove("urgente");
  if (p.estado === "falando" && p.legenda){ l2.textContent = p.legenda; return; }
  if (p.estado === "confirmar"){ l2.textContent = p.legenda || "Preciso do seu ok para seguir"; return; }
  if (p.estado === "ouvindo"){ l2.textContent = "Pode falar…"; return; }
  if (PENSANDO.has(p.estado)){ l2.textContent = p.estado === "transcrevendo" ? "Entendendo o que você disse" : "Organizando a resposta"; return; }
  if (p.alerta === "risco" && p.alerta_texto){ l2.textContent = "⚠ " + p.alerta_texto; l2.classList.add("urgente"); return; }
  if (p.proximo){
    const m = p.proximo.minutos;
    const quando = m <= 0 ? "agora" : m < 60 ? `em ${m} min` : `às ${p.proximo.hora}`;
    l2.innerHTML = ""; const b = document.createElement("b"); b.textContent = quando.charAt(0).toUpperCase() + quando.slice(1);
    l2.append(b, document.createTextNode(" · " + p.proximo.titulo));
    if (m <= 15) l2.classList.add("urgente");
    return;
  }
  if (p.alerta === "atencao" && p.alerta_texto){ l2.textContent = p.alerta_texto; return; }
  l2.textContent = p.estado === "conversa" || p.estado === "sentinela" ? `Diga “${p.assistente || "Núcleo"}” quando precisar` : "Agenda livre por enquanto";
}

function pintar(){
  document.body.dataset.tema = p.tema === "jarvis" ? "jarvis" : "ambar";
  document.body.dataset.cor = p.cor || "azul";
  document.body.classList.toggle("ouvindo", p.estado === "ouvindo" || p.estado === "conversa");
  const agora = new Date();
  $("hora").textContent = agora.toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
  $("estado").textContent = ROTULOS[p.estado] || "";
  const cap = $("capsula");
  cap.classList.toggle("ativa", ATIVOS.has(p.estado));
  cap.classList.toggle("risco", p.alerta === "risco" && !ATIVOS.has(p.estado));
  cap.classList.toggle("atencao", p.alerta === "atencao" && !ATIVOS.has(p.estado));
  $("b-falar").classList.toggle("ligado", !!p.ativo);
  linha2();
  ajustar(p.estado === "falando" && p.legenda && p.legenda.length > 38 ? "grande"
        : (p.estado === "ouvindo" || p.estado === "conversa") ? "ouvindo"
        : (!ATIVOS.has(p.estado) && (p.alerta === "risco" || p.alerta === "atencao") && p.alerta_texto && !p.proximo) || p.estado === "confirmar" ? "largo" : "normal");
}

async function atualizar(){
  try {
    const r = await fetch("/api/presenca",{credentials:"same-origin"});
    if (r.ok){ p = await r.json(); pintar(); }
  } catch(e){}
  setTimeout(atualizar, 300);
}

function comando(acao){ if (window.pywebview && pywebview.api && pywebview.api.comando) pywebview.api.comando(acao); }
$("b-falar").addEventListener("click", e => { e.stopPropagation(); comando("conversa"); });
$("b-briefing").addEventListener("click", e => { e.stopPropagation(); comando("briefing"); });
$("b-abrir").addEventListener("click", e => { e.stopPropagation(); comando("abrir"); });
$("capsula").addEventListener("dblclick", () => { if (window.pywebview) pywebview.api.mostrar_principal(); });
window.__widget = {definir(x){ p = {...p, ...x}; pintar(); }};   // usado só nos testes visuais
quadro(); atualizar(); pintar();
