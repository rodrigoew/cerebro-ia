"use strict";
/* ---------- estados visuais nas respostas ---------- */
function aplicarNivel(r){
  const n = (r && r.nivel) || "normal";
  emitirOnda(n === "normal" ? humor.base : n);
  if (n !== "normal") definirHumor(n, n === "risco" ? 12000 : 7000);
}
function revelarTexto(el, texto){
  if (matchMedia("(prefers-reduced-motion: reduce)").matches){ el.textContent = texto; return; }
  const palavras = texto.split(/(\s+)/);
  el.replaceChildren(...palavras.map(p => /\s+/.test(p) ? document.createTextNode(p) : h("span",{class:"palavra"}, p)));
  const spans = el.querySelectorAll(".palavra"); let i = 0;
  const passo = () => { if (i < spans.length){ spans[i++].classList.add("on"); setTimeout(passo, 22); } };
  passo();
}
