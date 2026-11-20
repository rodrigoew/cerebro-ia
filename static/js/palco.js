"use strict";
/* ---------- PALCO: tela inicial em tela cheia ----------
   O núcleo fica no centro, pergunta o que você quer ver e mostra só o que importa agora.
   A resposta surge do núcleo em destaque; o resto fica recolhido nas abas laterais. */
const palco = {conversas:0, ultimaPergunta:"", ultimaPres:"", enviadoEm:0};

function saudacao(){
  const h = new Date().getHours();
  const nome = estado.cfg && estado.cfg.nome ? `, ${estado.cfg.nome.split(" ")[0]}` : "";
  return (h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite") + nome + ".";
}
async function carregarFoco(){
  document.getElementById("p-saudacao").textContent = saudacao();
  try {
    const d = await api("/api/foco");
    document.getElementById("p-foco").replaceChildren(...d.foco.map((f, i) => h("button",{"data-nivel":f.nivel, style:`--i:${i}`,
      onclick:()=>{ if (f.id === "briefing") iniciarBriefing(); else pedir(f.pergunta); }},
      h("b",{}, f.rotulo), h("small",{}, f.detalhe))));
    const modo = estado.cfg && estado.cfg.cerebro_modo;
    if (modo && modo !== "claude"){
      document.getElementById("p-foco").append(h("button",{class:"p-dica", onclick:()=>irPara("ajustes")},
        h("b",{}, "Respostas mais naturais"), h("small",{}, "ligar o Claude em Ajustes > Cérebro")));
    }
  } catch(e){}
}

/* resposta no palco */
function mostrarCartao(conteudo){
  const c = document.getElementById("p-cartao");
  c.hidden = false;
  c.replaceChildren(h("p",{class:"p-voce"}, h("span",{}, "Você: ", h("b",{}, palco.ultimaPergunta)),
    h("button",{class:"p-icone g-fechar", "aria-label":"Voltar ao início", title:"Voltar ao início (Esc)", onclick:fecharCartao}, "×")), ...conteudo);
  document.getElementById("tela-nucleo").classList.add("com-cartao");
}
function fecharCartao(){
  document.getElementById("tela-nucleo").classList.remove("com-cartao");
  document.getElementById("p-cartao").hidden = true;
  carregarFoco();
}
function palcoPergunta(texto){
  palco.ultimaPergunta = texto; palco.conversas++;
  document.getElementById("b-conversa").textContent = palco.conversas;
  mostrarCartao([h("div",{class:"n-resp ao-vivo"}, h("span",{class:"selo"}, h("i"), h("span",{}, "Pensando…")), h("div",{class:"txt-vivo"}))]);
}
function palcoAoVivo(rotulo){
  const s = document.querySelector("#p-cartao .ao-vivo .selo span");
  if (s) s.textContent = rotulo;
}
function palcoTexto(texto){
  const v = document.querySelector("#p-cartao .txt-vivo");
  if (v){ v.textContent = texto; const c = document.getElementById("p-cartao"); c.scrollTop = c.scrollHeight; }
}
function palcoFinal(r, transmitido){
  if (r.tipo === "briefing"){ fecharCartao(); return; }
  mostrarCartao([cartaoResposta(r, {semDigitacao: transmitido})]);
}

/* legenda: o que você disse e o que ele está falando */
function legenda(quem, texto){
  const l = document.getElementById("p-legenda");
  if (!l) return;
  if (!texto){ l.replaceChildren(); return; }
  l.replaceChildren(h("span",{class:"quem"}, quem), texto);
}

/* abas laterais (painéis recolhidos) */
function abrirGaveta(id){
  document.querySelectorAll(".p-gaveta").forEach(g => g.classList.toggle("aberta", g.id === "g-" + id && !g.classList.contains("aberta")));
  document.querySelectorAll(".p-abas button").forEach(b =>
    b.setAttribute("aria-pressed", String(document.getElementById("g-" + b.dataset.gaveta).classList.contains("aberta"))));
  if (id === "memoria") api("/api/cerebro/mapa").then(desenharMapa).catch(()=>{});
  if (id === "conversa") rolarFeed();
}
function fecharGavetas(){
  document.querySelectorAll(".p-gaveta.aberta").forEach(g => g.classList.remove("aberta"));
  document.querySelectorAll(".p-abas button").forEach(b => b.setAttribute("aria-pressed","false"));
}
document.querySelectorAll(".p-abas button").forEach(b => b.addEventListener("click", () => abrirGaveta(b.dataset.gaveta)));
document.querySelectorAll(".p-gaveta .g-fechar").forEach(b => b.addEventListener("click", fecharGavetas));

/* menu, busca e tela cheia */
document.getElementById("p-menu").addEventListener("click", ev => { ev.stopPropagation(); document.body.classList.toggle("menu-aberto"); });
document.addEventListener("click", ev => {
  if (document.body.classList.contains("menu-aberto") && !ev.target.closest(".trilho") && !ev.target.closest("#p-menu"))
    document.body.classList.remove("menu-aberto");
});
document.querySelectorAll(".trilho .nav button").forEach(b => b.addEventListener("click", () => document.body.classList.remove("menu-aberto")));
document.getElementById("p-busca").addEventListener("click", () => abrirBusca());
function alternarTelaCheia(){
  if (window.pywebview && window.pywebview.api) window.pywebview.api.alternar_tela_cheia();
  else if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(()=>{});
}
document.getElementById("p-telacheia").addEventListener("click", alternarTelaCheia);
document.addEventListener("keydown", ev => {
  if (ev.key === "F11"){ ev.preventDefault(); alternarTelaCheia(); return; }
  if (ev.key === "Escape" && estado.tela === "nucleo" && !(typeof bri !== "undefined" && bri.ativo)){
    if (document.querySelector(".p-gaveta.aberta")){ fecharGavetas(); return; }
    if (document.getElementById("tela-nucleo").classList.contains("com-cartao")) fecharCartao();
  }
});

/* presença: conta ao app se está ouvindo/falando (o indicador flutuante mostra isso fora da janela) */
setInterval(() => {
  if (typeof nucleo === "undefined") return;
  const p = {ativo: !!(typeof conversa !== "undefined" && conversa.ativa), estado: nucleo.estado,
             nivel: Math.round((nucleo.nivel || 0) * 100) / 100, humor: humor.atual,
             legenda: (document.getElementById("p-legenda").textContent || "").slice(0, 150)};
  const chave = JSON.stringify(p);
  if (chave === palco.ultimaPres && Date.now() - palco.enviadoEm < 5000) return;
  palco.ultimaPres = chave; palco.enviadoEm = Date.now();
  api("/api/presenca",{method:"POST",body:chave}).catch(()=>{});
}, 300);
