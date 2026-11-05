"use strict";
/* ---------- BUSCA GLOBAL (Ctrl+K em qualquer tela) ---------- */
const busca = {aberta:false, itens:[], sel:0, tempo:null};
function abrirBusca(){
  let caixa = document.getElementById("busca-global");
  if (!caixa){
    caixa = h("div",{id:"busca-global", class:"busca-global", role:"dialog", "aria-modal":"true", "aria-label":"Busca global",
      onclick:ev=>{ if (ev.target.id === "busca-global") fecharBusca(); }},
      h("div",{class:"bg-caixa"},
        h("input",{id:"bg-input", type:"search", autocomplete:"off", placeholder:"Buscar e-mails, pessoas, decisões, ideias, contas… ou perguntar ao assistente",
          oninput:ev=>{ clearTimeout(busca.tempo); busca.tempo = setTimeout(() => buscarGlobal(ev.target.value), 180); },
          onkeydown:teclaBusca}),
        h("div",{id:"bg-lista", class:"bg-lista", role:"listbox"}),
        h("div",{class:"bg-rodape"}, "↑↓ navegar · Enter abrir · Esc fechar")));
    document.body.append(caixa);
  }
  caixa.classList.add("aberta"); busca.aberta = true;
  const i = document.getElementById("bg-input"); i.value = ""; i.focus(); buscarGlobal("");
}
function fecharBusca(){ const c = document.getElementById("busca-global"); if (c) c.classList.remove("aberta"); busca.aberta = false; }
async function buscarGlobal(q){
  const lista = document.getElementById("bg-lista");
  let resultados = [];
  if (q.trim().length >= 2){ try { resultados = (await api(`/api/busca?q=${encodeURIComponent(q)}`)).resultados; } catch(e){} }
  busca.itens = q.trim() ? [{tipo:"Perguntar", titulo:`Perguntar a ${nomeAssist()}: “${q}”`, sub:"responde com seus dados, localmente", perguntar:q}, ...resultados]
    : [{tipo:"Ir para", titulo:`Falar com ${nomeAssist()}`, sub:"Ctrl+Shift+K", alvo:{tela:"nucleo"}}, {tipo:"Ir para", titulo:"E-mails", alvo:{tela:"emails"}},
       {tipo:"Ir para", titulo:"Pessoas e compromissos", alvo:{tela:"pessoas"}}, {tipo:"Ir para", titulo:"Mente", alvo:{tela:"mente"}},
       {tipo:"Ir para", titulo:"Briefing do dia", alvo:{tela:"briefing"}}];
  busca.sel = 0; desenharBusca();
  if (q.trim().length >= 2 && !resultados.length) lista.append(h("p",{class:"vazio", style:"padding:10px 14px"}, "Nada encontrado nos seus dados."));
}
function desenharBusca(){
  const lista = document.getElementById("bg-lista");
  lista.replaceChildren(...busca.itens.map((it, i) => h("button",{class:"bg-item", role:"option", "aria-selected":String(i === busca.sel),
    onmouseenter:()=>{ busca.sel = i; desenharBusca(); }, onclick:()=>abrirResultado(it)},
    h("span",{class:"bg-tipo"}, it.tipo), h("span",{class:"bg-tit"}, it.titulo), it.sub ? h("small",{}, it.sub) : null)));
  const s = lista.querySelector('[aria-selected="true"]'); if (s) s.scrollIntoView({block:"nearest"});
}
function teclaBusca(ev){
  if (ev.key === "ArrowDown"){ ev.preventDefault(); busca.sel = Math.min(busca.itens.length - 1, busca.sel + 1); desenharBusca(); }
  else if (ev.key === "ArrowUp"){ ev.preventDefault(); busca.sel = Math.max(0, busca.sel - 1); desenharBusca(); }
  else if (ev.key === "Enter"){ ev.preventDefault(); if (busca.itens[busca.sel]) abrirResultado(busca.itens[busca.sel]); }
  else if (ev.key === "Escape") fecharBusca();
}
function abrirResultado(it){
  fecharBusca();
  if (it.perguntar){ irPara("nucleo"); setTimeout(() => pedir(it.perguntar), 80); return; }
  const a = it.alvo || {};
  if (a.tela === "briefing"){ iniciarBriefing(); return; }
  if (a.tela === "mente"){ if (a.aba === "decisoes" && a.id) mt.decisao = a.id; irPara("mente"); carregarMente(a.aba); return; }
  if (a.tela === "emails"){ irPara("emails"); if (a.id) setTimeout(() => abrirEmail(a.id), 400); return; }
  if (a.tela === "pessoas"){ if (a.id) ps.atual = a.id; irPara("pessoas"); return; }
  if (a.tela === "nucleo"){ focarAssistente("nucleo"); return; }
  if (a.tela) irPara(a.tela);
}
document.addEventListener("keydown", ev => {
  if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey && ev.key.toLowerCase() === "k"){ ev.preventDefault(); busca.aberta ? fecharBusca() : abrirBusca(); }
});
