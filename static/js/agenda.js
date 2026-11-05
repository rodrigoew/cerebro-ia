"use strict";
/* ---------- AGENDA ---------- */
document.getElementById("ag-semana").onclick = () => { estado.agVista="semana"; desenharAgenda(); };
document.getElementById("ag-mes").onclick = () => { estado.agVista="mes"; desenharAgenda(); };
document.getElementById("ag-hoje").onclick = () => { estado.agRef=new Date(); desenharAgenda(); };
document.getElementById("ag-ant").onclick = () => mover(-1);
document.getElementById("ag-prox").onclick = () => mover(1);
function mover(n){
  const d = new Date(estado.agRef);
  if (estado.agVista === "semana") d.setDate(d.getDate()+7*n); else d.setMonth(d.getMonth()+n, 1);
  estado.agRef = d; desenharAgenda();
}
function periodoAgenda(){
  if (estado.agVista === "semana"){ const de = inicioSemana(estado.agRef); return [de, somaDias(de,7)]; }
  const primeiro = new Date(estado.agRef.getFullYear(), estado.agRef.getMonth(), 1);
  const de = inicioSemana(primeiro); return [de, somaDias(de,42)];
}
async function desenharAgenda(){
  if (!estado.cfg) return;
  document.getElementById("ag-semana").setAttribute("aria-pressed", estado.agVista==="semana");
  document.getElementById("ag-mes").setAttribute("aria-pressed", estado.agVista==="mes");
  const [de, ate] = periodoAgenda();
  const tituloEl = document.getElementById("ag-titulo");
  if (estado.agVista === "semana"){
    const fim = somaDias(de,6);
    tituloEl.textContent = de.getMonth()===fim.getMonth()
      ? `${de.getDate()} a ${fim.getDate()} de ${MESES[fim.getMonth()]}`
      : `${de.getDate()} de ${MESES[de.getMonth()]} a ${fim.getDate()} de ${MESES[fim.getMonth()]}`;
  } else tituloEl.textContent = `${MESES[estado.agRef.getMonth()]} de ${estado.agRef.getFullYear()}`;

  const leg = document.getElementById("ag-legenda"); leg.replaceChildren();
  estado.cfg.agendas.forEach((nome,i) => leg.append(h("label",{},
    h("input",{type:"checkbox", checked:!estado.agOcultas.has(i), onchange:ev=>{ ev.target.checked ? estado.agOcultas.delete(i) : estado.agOcultas.add(i); desenharAgenda(); }}),
    h("i",{style:`background:${corAgenda(i)}`}), nome)));
  leg.append(h("label",{}, h("input",{type:"checkbox", checked:estado.agVenc, onchange:ev=>{ estado.agVenc = ev.target.checked; desenharAgenda(); }}),
    h("i",{style:"background:var(--latao);border-radius:2px"}), "Vencimentos"));

  const corpo = document.getElementById("ag-corpo");
  if (!estado.cfg.agendas.length && !estado.agVenc){ corpo.replaceChildren(h("p",{class:"vazio",style:"padding:20px"},"Nenhuma agenda configurada.")); return; }
  let dados;
  try { dados = await api(`/api/agenda?de=${iso(de)}&ate=${iso(ate)}`); }
  catch(err){ corpo.replaceChildren(h("p",{class:"vazio",style:"padding:20px"}, err.message)); return; }
  const eventos = dados.eventos.filter(e => !estado.agOcultas.has(e.agenda_idx));
  const venc = estado.agVenc ? dados.vencimentos : [];
  document.getElementById("ag-falhas").replaceChildren(...dados.falhas.map(f => h("li",{},f)));
  if (estado.agVista === "semana") desenharSemana(corpo, de, eventos, venc);
  else desenharMes(corpo, de, eventos, venc);
}
function chipVencimento(v){
  const atrasada = !v.pago_em && v.vencimento < hojeISO();
  const cls = "chip venc" + (v.pago_em ? " paga" : atrasada ? " atrasada" : "");
  const rotulo = `${v.tipo==="receber"?"Receber":"Pagar"}: ${v.descricao}`;
  return h("button",{class:cls, title:rotulo, onclick:ev=>abrirDetalhe(ev, [
    h("h3",{}, rotulo),
    h("p",{}, `${reais(v.valor_centavos)}, vence ${ddmm(v.vencimento)}`),
    h("p",{}, `${v.carteira}${v.pago_em ? ", pago em "+ddmm(v.pago_em) : atrasada ? ", em atraso" : ""}`),
    h("p",{style:"margin-top:10px"}, h("button",{class:"btn pequeno", onclick:()=>{ fecharDetalhe(); irPara("financeiro"); }},"Abrir no Financeiro"))
  ])}, rotulo);
}
function detalheEvento(e){
  const ini = new Date(e.inicio), fim = e.fim ? new Date(e.fim) : null;
  return [h("h3",{}, e.titulo),
    h("p",{}, e.dia_inteiro ? "Dia todo" : `${hhmm(ini)}${fim ? " às "+hhmm(fim) : ""}`),
    h("p",{}, h("i",{style:`display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:${corAgenda(e.agenda_idx)}`}), e.agenda),
    e.local ? h("p",{}, e.local) : null,
    e.quem.length ? h("p",{}, "Com " + e.quem.join(", ")) : null];
}
function desenharSemana(corpo, de, eventos, venc){
  const HORA_PX = 48;
  const dias = [...Array(7)].map((_,i)=>somaDias(de,i));
  const hoje = hojeISO();
  let hMin = 7, hMax = 21;
  eventos.filter(e=>!e.dia_inteiro).forEach(e => {
    const a = new Date(e.inicio), b = new Date(e.fim || e.inicio);
    hMin = Math.min(hMin, a.getHours()); hMax = Math.max(hMax, Math.min(24, b.getHours() + (b.getMinutes()?1:0)));
  });
  const grade = h("div",{class:"semana"});
  grade.append(h("div",{class:"cab"}));
  dias.forEach(d => grade.append(h("div",{class:"cab"+(iso(d)===hoje?" hoje-col":"")}, DSEM[d.getDay()], h("b",{}, d.getDate()))));
  grade.append(h("div",{class:"diatodo-rot"},"dia todo"));
  dias.forEach(d => {
    const k = iso(d);
    const cel = h("div",{class:"diatodo"});
    eventos.filter(e => e.dia_inteiro && e.inicio.slice(0,10) <= k && (e.fim ? e.fim.slice(0,10) > k : e.inicio.slice(0,10) === k))
      .forEach(e => cel.append(h("button",{class:"chip", style:`--cor:${corAgenda(e.agenda_idx)}`, onclick:ev=>abrirDetalhe(ev, detalheEvento(e))}, e.titulo)));
    venc.filter(v => v.vencimento === k).forEach(v => cel.append(chipVencimento(v)));
    grade.append(cel);
  });
  const wrap = h("div",{class:"grade-wrap"});
  const altura = (hMax - hMin) * HORA_PX;
  const horas = h("div",{class:"horas", style:`height:${altura}px`});
  for (let x = hMin+1; x < hMax; x++) horas.append(h("span",{style:`top:${(x-hMin)*HORA_PX}px`}, `${String(x).padStart(2,"0")}:00`));
  wrap.append(horas);
  const agora = agoraNoFuso();
  dias.forEach(d => {
    const k = iso(d);
    const col = h("div",{class:"coluna"+(k===hoje?" hoje-col":""), style:`height:${altura}px`});
    for (let x = hMin+1; x < hMax; x++) col.append(h("div",{class:"linha-hora", style:`top:${(x-hMin)*HORA_PX}px`}));
    const ini0 = new Date(d.getFullYear(), d.getMonth(), d.getDate(), hMin), fim0 = new Date(d.getFullYear(), d.getMonth(), d.getDate(), hMax);
    const doDia = eventos.filter(e => !e.dia_inteiro).map(e => {
      const a = new Date(e.inicio), b = new Date(e.fim || (a.getTime()+30*60000));
      return {e, a:new Date(Math.max(a, ini0)), b:new Date(Math.min(b, fim0))};
    }).filter(x => x.b > x.a).sort((x,y)=>x.a-y.a || y.b-x.b);
    // distribui eventos sobrepostos lado a lado
    let grupo = [], fimGrupo = 0;
    const fechar = () => {
      const colunas = [];
      grupo.forEach(x => { let i = colunas.findIndex(fimCol => fimCol <= x.a); if (i<0){ i = colunas.length; colunas.push(0); } colunas[i] = x.b; x.col = i; });
      grupo.forEach(x => x.n = colunas.length); grupo = [];
    };
    doDia.forEach(x => { if (grupo.length && x.a >= fimGrupo) fechar(); grupo.push(x); fimGrupo = Math.max(fimGrupo, x.b); });
    if (grupo.length) fechar();
    doDia.forEach(x => {
      const topo = (x.a - ini0)/3600000*HORA_PX, alt = Math.max(22, (x.b - x.a)/3600000*HORA_PX - 2);
      const larg = 100 / x.n;
      col.append(h("button",{class:"bloco", style:`--cor:${corAgenda(x.e.agenda_idx)};top:${topo}px;height:${alt}px;left:calc(${x.col*larg}% + 2px);width:calc(${larg}% - 4px)`,
        onclick:ev=>abrirDetalhe(ev, detalheEvento(x.e))},
        h("b",{}, x.e.titulo), alt > 40 ? h("span",{}, `${hhmm(new Date(x.e.inicio))}${x.e.fim ? "–"+hhmm(new Date(x.e.fim)) : ""}`) : null));
    });
    if (k === hoje && agora >= ini0 && agora <= fim0) col.append(h("div",{class:"agora", style:`top:${(agora-ini0)/3600000*HORA_PX}px`}));
    wrap.append(col);
  });
  grade.append(wrap);
  corpo.replaceChildren(grade);
  wrap.scrollTop = 0;
}
function desenharMes(corpo, de, eventos, venc){
  const grade = h("div",{class:"mes"});
  ["seg","ter","qua","qui","sex","sáb","dom"].forEach(d => grade.append(h("div",{class:"dsem"}, d)));
  const mes = estado.agRef.getMonth(), hoje = hojeISO();
  for (let i = 0; i < 42; i++){
    const d = somaDias(de,i), k = iso(d);
    const cel = h("div",{class:"dia"+(d.getMonth()!==mes?" fora":"")+(k===hoje?" hoje-col":"")}, h("span",{class:"n"}, d.getDate()));
    const itens = [];
    eventos.filter(e => e.dia_inteiro ? (e.inicio.slice(0,10) <= k && (e.fim ? e.fim.slice(0,10) > k : e.inicio.slice(0,10)===k)) : iso(new Date(e.inicio)) === k)
      .forEach(e => itens.push(h("button",{class:"chip", style:`--cor:${corAgenda(e.agenda_idx)}`, onclick:ev=>abrirDetalhe(ev, detalheEvento(e))},
        e.dia_inteiro ? e.titulo : `${hhmm(new Date(e.inicio))} ${e.titulo}`)));
    venc.filter(v => v.vencimento === k).forEach(v => itens.push(chipVencimento(v)));
    itens.slice(0,3).forEach(x => cel.append(x));
    if (itens.length > 3) cel.append(h("button",{class:"mais", onclick:()=>{ estado.agRef = d; estado.agVista = "semana"; desenharAgenda(); }}, `mais ${itens.length-3}`));
    grade.append(cel);
  }
  corpo.replaceChildren(grade);
}
function abrirDetalhe(ev, conteudo){
  ev.stopPropagation();
  const p = document.getElementById("detalhe");
  p.replaceChildren(h("button",{class:"fechar","aria-label":"Fechar", onclick:fecharDetalhe},"×"), ...conteudo.filter(Boolean));
  p.classList.add("aberto");
  const r = ev.currentTarget.getBoundingClientRect();
  const x = Math.min(window.innerWidth - 340, r.right + 8 > window.innerWidth - 340 ? r.left - 330 : r.right + 8);
  p.style.left = Math.max(12, x) + "px";
  p.style.top = Math.min(window.innerHeight - p.offsetHeight - 12, Math.max(12, r.top)) + "px";
}
function fecharDetalhe(){ document.getElementById("detalhe").classList.remove("aberto"); }
document.addEventListener("click", ev => { if (!document.getElementById("detalhe").contains(ev.target)) fecharDetalhe(); });
