"use strict";
"use strict";
const TOKEN = "";   // a autenticação vai pelo cookie httpOnly; o X-Token só é usado na sincronização entre máquinas
const MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
const DSEM = ["dom","seg","ter","qua","qui","sex","sáb"];
const BRL = new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"});
const estado = {cfg:null, tela:"hoje", agVista:"semana", agRef:new Date(), agOcultas:new Set(), agVenc:true,
  finMes:null, finCarteira:"todas", finStatus:"pendentes", editando:null, tipoForm:"pagar"};

/* ---------- utilidades ---------- */
function h(tag, attrs, ...filhos){
  const el = document.createElement(tag);
  for (const [k,v] of Object.entries(attrs||{})){
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.setAttribute("style", v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()){
    if (f === null || f === undefined || f === false) continue;
    el.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return el;
}
async function api(caminho, opcoes={}){
  const r = await fetch(caminho, {...opcoes, credentials:"same-origin", headers:{"Content-Type":"application/json"}});
  const dados = await r.json().catch(()=>({}));
  if (!r.ok) throw new Error(dados.erro || "Falha na comunicação com o aplicativo.");
  return dados;
}
function avisar(msg){
  const a = document.getElementById("aviso"); a.textContent = msg; a.classList.add("visivel");
  clearTimeout(avisar.t); avisar.t = setTimeout(()=>a.classList.remove("visivel"), 2600);
}
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const deISO = s => { const [a,m,d] = s.split("-").map(Number); return new Date(a,m-1,d); };
const somaDias = (d,n) => { const x = new Date(d); x.setDate(x.getDate()+n); return x; };
const inicioSemana = d => { const x = new Date(d.getFullYear(),d.getMonth(),d.getDate()); const w=(x.getDay()+6)%7; return somaDias(x,-w); };
const hhmm = d => `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
const ddmm = s => { const d = deISO(s); return `${String(d.getDate()).padStart(2,"0")}/${String(d.getMonth()+1).padStart(2,"0")}`; };
const reais = c => c === null || c === undefined ? "sem valor" : BRL.format(c/100);
const corAgenda = i => `var(--c${i % 7})`;
function lerReais(txt){
  const t = String(txt||"").trim().replace(/[R$\s]/g,"");
  if (!t) return null;
  const normal = t.includes(",") ? t.replace(/\./g,"").replace(",",".") : t;
  const n = Number(normal);
  if (!isFinite(n) || n < 0) throw new Error("Valor inválido. Use o formato 1.234,56.");
  return Math.round(n*100);
}
function hojeISO(){ return estado.cfg ? estado.cfg.hoje : iso(new Date()); }
function agoraNoFuso(){
  // Relógio no fuso do config, para a linha de "agora" bater com a agenda.
  const fuso = estado.cfg ? estado.cfg.fuso : undefined;
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-CA",{timeZone:fuso,year:"numeric",month:"2-digit",day:"2-digit",
    hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(new Date()).map(x=>[x.type,x.value]));
  return new Date(+p.year, +p.month-1, +p.day, +p.hour, +p.minute);
}

/* ---------- navegação ---------- */
document.querySelectorAll(".nav button").forEach(b => b.addEventListener("click", () => irPara(b.dataset.tela)));
function irPara(tela){
  estado.tela = tela;
  document.querySelectorAll(".nav button").forEach(b => {
    if (b.dataset.tela === tela) b.setAttribute("aria-current","page"); else b.removeAttribute("aria-current");
  });
  document.querySelectorAll(".tela").forEach(s => s.classList.toggle("ativa", s.id === "tela-"+tela));
  fecharDetalhe();
  if (tela === "agenda") desenharAgenda();
  if (tela === "financeiro") carregarFinanceiro();
  if (tela === "nucleo") carregarNucleo();
  if (tela === "ajustes") carregarAjustes();
  if (tela === "emails") carregarEmails();
  if (tela === "mente") carregarMente();
  if (tela === "pessoas") carregarPessoas();
}

/* ---------- estado geral ---------- */
async function carregarEstado(){
  const e = await api("/api/estado");
  estado.cfg = e;
  document.getElementById("nome-usuario").textContent = e.nome ? `segundo cérebro de ${e.nome}` : "seu segundo cérebro";
  aplicarNomeAssistente();
  if (e.versao) document.getElementById("versao").textContent = `Núcleo ${e.versao}`;
  if (e.alerta){ const mudou = humor.atual === humor.base; humor.base = e.alerta.nivel; if (mudou) definirHumor(humor.base);
    const mot = document.getElementById("n-motivos"); if (mot) mot.textContent = e.alerta.motivos.slice(0,3).join(" · "); }
  const lic = document.getElementById("selo-licenca");
  if (e.licenca && e.licenca.modo !== "pessoal" && e.licenca.modo !== "licenciado"){ lic.hidden = false; lic.textContent = e.licenca.mensagem; lic.classList.toggle("alerta", !e.licenca.liberado); }
  else lic.hidden = true;
  if (e.primeiro_uso && !document.getElementById("boasvindas").classList.contains("aberto")) primeirosPassos();
  const st = document.getElementById("estado"), btn = document.getElementById("btn-atualizar");
  btn.disabled = e.atualizando;
  btn.textContent = e.atualizando ? "Atualizando…" : "Atualizar agora";
  if (e.atualizando) st.textContent = "Lendo e-mails e agendas.";
  else if (e.erro) st.textContent = "Última atualização falhou: " + e.erro;
  else if (e.resumo) st.textContent = "Atualizado às " + new Date(e.resumo.gerado_em).toLocaleTimeString("pt-BR",{timeZone:e.fuso,hour:"2-digit",minute:"2-digit"}) + ".";
  else st.textContent = "";
  (e.notificacoes || []).forEach(mostrarNotificacao);
  desenharHoje(e);
  return e;
}
async function atualizar(){
  try { await api("/api/atualizar",{method:"POST"}); } catch(err){ avisar(err.message); }
  acompanhar();
}
async function acompanhar(){
  const e = await carregarEstado().catch(()=>null);
  if (e && e.atualizando) setTimeout(acompanhar, 2500);
  else if (estado.tela === "financeiro") carregarFinanceiro();
}
document.getElementById("btn-atualizar").addEventListener("click", atualizar);

/* ---------- foco do assistente (atalho global e bandeja) ---------- */
window.focarAssistente = function(alvo){
  if (alvo === "briefing"){ iniciarBriefing(); return; }
  irPara("nucleo"); setTimeout(() => { const i = document.getElementById("n-input"); if (i) i.focus(); }, 60);
};

/* ---------- notificações dentro do app ---------- */
function mostrarNotificacao(n){
  let pilha = document.getElementById("pilha-notif");
  if (!pilha){ pilha = h("div",{id:"pilha-notif", class:"pilha-notif", role:"status", "aria-live":"polite"}); document.body.append(pilha); }
  const el = h("button",{class:"notif", "data-nivel":n.nivel || "normal", onclick:()=>{ if (n.tela) irPara(n.tela); el.remove(); }},
    h("b",{}, n.titulo), h("span",{}, n.texto));
  pilha.append(el);
  setTimeout(() => el.classList.add("saindo"), 9000); setTimeout(() => el.remove(), 9600);
  if (typeof definirHumor === "function" && n.nivel && n.nivel !== "normal"){ definirHumor(n.nivel, 8000); emitirOnda(n.nivel); }
}
setInterval(() => { if (!estado.cfg || !estado.cfg.atualizando) carregarEstado().catch(()=>{}); }, 60000);

/* ---------- desfazer ---------- */
function avisarDesfazer(mensagem, desfazer, efetivar, ms = 6000){
  let pilha = document.getElementById("pilha-notif");
  if (!pilha){ pilha = h("div",{id:"pilha-notif", class:"pilha-notif", role:"status", "aria-live":"polite"}); document.body.append(pilha); }
  let feito = false;
  const el = h("div",{class:"notif desfazer"}, h("span",{}, mensagem),
    h("button",{class:"btn pequeno", onclick:()=>{ feito = true; el.remove(); desfazer && desfazer(); }}, "Desfazer"));
  pilha.append(el);
  setTimeout(() => { el.remove(); if (!feito && efetivar) efetivar(); }, ms);
}
