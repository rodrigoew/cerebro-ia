"use strict";
/* ---------- BRIEFING NARRADO ---------- */
const bri = {ativo:false, pausado:false, idx:0, seg:[], g:0};
function cartaoBriefing(c){
  const cab = h("div",{class:"cab"}, h("i"), {clima:"Clima", agenda:"Agenda", atencao:"E-mail", financeiro:"Financeiro", lembretes:"Lembretes",
    sistema:"Computador", noticia:"Notícias", desde_ontem:"Memória"}[c.tipo] || "Núcleo", h("span",{style:"margin-left:auto"}, hhmm(agoraNoFuso())));
  const lista = itens => h("ul",{}, itens.map(i => typeof i === "string" ? h("li",{class:"sem-hora"}, h("span",{}, i))
    : i.hora ? h("li",{}, h("b",{}, i.hora), h("span",{}, i.texto))
    : h("li",{class:"sem-hora"}, h("span",{}, i.titulo), i.detalhe ? h("small",{}, i.detalhe) : null)));
  let corpo;
  if (c.tipo === "clima"){
    corpo = h("div",{class:"b-clima"}, h("span",{class:"temp"}, `${Math.round(c.agora)}°`), h("span",{class:"desc"}, c.descricao ? c.descricao[0].toUpperCase() + c.descricao.slice(1) : ""),
      h("span",{class:"det"}, ...[`Mín ${Math.round(c.minima)}°`, `Máx ${Math.round(c.maxima)}°`,
        c.chuva != null ? `Chuva ${c.chuva}%` : null, c.umidade != null ? `Umidade ${c.umidade}%` : null,
        c.vento != null ? `Vento ${Math.round(c.vento)} km/h` : null].filter(Boolean).map(x => h("span",{}, x))));
  } else if (c.tipo === "noticia"){
    corpo = h("div",{class:"b-noticia"}, c.imagem ? h("img",{src:c.imagem, alt:"", onerror:ev=>ev.target.remove()}) : null,
      h("strong",{}, c.manchete), h("p",{}, c.resumo || ""), h("div",{class:"fonte"}, c.fonte));
  } else corpo = c.itens && c.itens.length ? lista(c.itens) : h("p",{style:"margin:0;color:var(--n-suave)"}, "Nada por aqui.");
  return h("div",{class:"b-cartao"}, cab, c.tipo === "noticia" ? null : h("h4",{}, c.titulo), corpo);
}
function mostrarSegmento(i){
  const atual = document.getElementById("b-atual"), bandeja = document.getElementById("b-bandeja");
  const anterior = atual.firstElementChild;
  if (anterior){ anterior.classList.remove("surgindo"); bandeja.append(anterior); bandeja.scrollLeft = bandeja.scrollWidth; }
  const s = bri.seg[i];
  const nivel = s.nivel || (s.cartao && s.cartao._nivel) || "normal";
  definirHumor(nivel); emitirOnda(nivel);
  if (s.cartao){ const el = cartaoBriefing(s.cartao); el.dataset.nivel = nivel; el.classList.add("surgindo"); atual.append(el); }
  document.getElementById("b-legenda").textContent = s.fala;
}
function esperar(ms){ return new Promise(ok => setTimeout(ok, ms)); }
async function narrar(texto){
  if (temPiper() || vozLocal()){ await falar(texto); }
  else { estadoNucleo("falando"); await esperar(Math.max(2600, texto.split(/\s+/).length * 380)); }
}
async function iniciarBriefing(){
  const caixa = document.getElementById("briefing");
  if (conversa.ativa && conversa.sentinela) conversa.acordadoAte = 0;
  interromperFala();
  bri.ativo = true; bri.pausado = false; bri.idx = 0; const g = ++bri.g;
  document.getElementById("b-atual").replaceChildren(); document.getElementById("b-bandeja").replaceChildren();
  document.getElementById("b-legenda").textContent = "Preparando o seu dia…";
  document.getElementById("b-estado").textContent = "ANALISANDO";
  caixa.classList.add("aberto"); estadoNucleo("analisando");
  try { const r = await api("/api/briefing"); bri.seg = r.segmentos; }
  catch(err){ document.getElementById("b-legenda").textContent = "Não consegui montar o briefing: " + err.message; return; }
  if (!nucleo.info){ try { nucleo.info = await api("/api/cerebro/estado"); } catch(e){} }
  // navegadores bloqueiam som sem um toque: se for o caso, pede um toque antes
  if (temPiper()){
    if (!fala.ac){ fala.ac = new (window.AudioContext || window.webkitAudioContext)(); fala.analisador = fala.ac.createAnalyser(); fala.analisador.fftSize = 1024; fala.analisador.connect(fala.ac.destination); }
    try { await fala.ac.resume(); } catch(e){}
    if (fala.ac.state !== "running"){
      const b = document.getElementById("b-iniciar"); b.style.display = "block";
      await new Promise(ok => b.onclick = async () => { b.style.display = "none"; try { await fala.ac.resume(); } catch(e){} ok(); });
    }
  }
  tocarBriefing(g);
}
async function tocarBriefing(g){
  document.getElementById("b-estado").textContent = "FALANDO";
  while (bri.idx < bri.seg.length && g === bri.g){
    if (bri.pausado) return;
    mostrarSegmento(bri.idx);
    await narrar(bri.seg[bri.idx].fala);
    if (g !== bri.g || bri.pausado) return;
    bri.idx++;
    await esperar(350);
  }
  if (g === bri.g){
    const atual = document.getElementById("b-atual").firstElementChild;
    if (atual){ atual.classList.remove("surgindo"); document.getElementById("b-bandeja").append(atual); }
    document.getElementById("b-estado").textContent = "PRONTO";
    estadoNucleo(estadoOcioso());
  }
}
function fecharBriefing(){
  bri.g++; bri.ativo = false; interromperFala(); definirHumor(humor.base);
  document.getElementById("briefing").classList.remove("aberto");
  if (document.fullscreenElement) document.exitFullscreen().catch(()=>{});
  if (location.hash === "#briefing") history.replaceState(null, "", location.pathname);
  estadoNucleo(estadoOcioso());
}
document.getElementById("b-fechar").onclick = fecharBriefing;
document.getElementById("b-pausa").onclick = ev => {
  if (!bri.pausado){ bri.pausado = true; interromperFala(); ev.target.textContent = "Continuar"; document.getElementById("b-estado").textContent = "PAUSADO"; }
  else { bri.pausado = false; ev.target.textContent = "Pausar"; document.getElementById("b-atual").replaceChildren(); tocarBriefing(bri.g); }
};
document.getElementById("b-pular").onclick = () => { if (!bri.ativo) return; interromperFala(); };
document.getElementById("b-tela").onclick = () => { const b = document.getElementById("briefing");
  if (document.fullscreenElement) document.exitFullscreen(); else b.requestFullscreen().catch(()=>{}); };
document.addEventListener("keydown", ev => {
  if (!document.getElementById("briefing").classList.contains("aberto")) return;
  if (ev.key === "Escape") fecharBriefing();
  if (ev.key === " ") { ev.preventDefault(); document.getElementById("b-pausa").click(); }
  if (ev.key === "ArrowRight") document.getElementById("b-pular").click();
});
