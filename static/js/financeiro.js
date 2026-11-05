"use strict";
/* ---------- FINANCEIRO ---------- */
document.getElementById("fin-ant").onclick = () => moverMes(-1);
document.getElementById("fin-prox").onclick = () => moverMes(1);
document.getElementById("fin-atual").onclick = () => { estado.finMes = hojeISO().slice(0,7); carregarFinanceiro(); };
document.getElementById("fin-novo").onclick = () => abrirGaveta(null);
function moverMes(n){
  const [a,m] = estado.finMes.split("-").map(Number); const d = new Date(a, m-1+n, 1);
  estado.finMes = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`; carregarFinanceiro();
}
async function carregarFinanceiro(){
  if (!estado.finMes) estado.finMes = hojeISO().slice(0,7);
  let f;
  try { f = await api(`/api/financeiro?mes=${estado.finMes}`); } catch(err){ avisar(err.message); return; }
  estado.fin = f;
  const [a,m] = f.mes.split("-").map(Number);
  document.getElementById("fin-titulo").textContent = `Financeiro de ${MESES[m-1]}`;
  const t = f.totais;
  const pendentesConfirmar = [...f.lancamentos, ...f.atrasadas, ...f.sem_data].filter(l => !l.confirmado && !l.pago_em).length;
  document.getElementById("conta-fin").textContent = pendentesConfirmar ? String(pendentesConfirmar) : "";
  document.getElementById("fin-numeros").replaceChildren(
    h("div",{class:"painel numero pagar"}, h("div",{class:"rot"},"A pagar"), h("div",{class:"val"}, reais(t.a_pagar)),
      h("div",{class:"nota"}, t.vencidas ? `${t.vencidas} em atraso` : "nada em atraso")),
    h("div",{class:"painel numero"}, h("div",{class:"rot"},"Já pago"), h("div",{class:"val"}, reais(t.pago)),
      h("div",{class:"nota"}, t.sem_valor ? `${t.sem_valor} sem valor informado` : "\u00a0")),
    h("div",{class:"painel numero receber"}, h("div",{class:"rot"},"A receber"), h("div",{class:"val"}, reais(t.a_receber)),
      h("div",{class:"nota"}, `${reais(t.recebido)} já recebido`)),
    h("div",{class:"painel numero"}, h("div",{class:"rot"},"Saldo previsto do mês"), h("div",{class:"val"}, reais(t.saldo_previsto)),
      h("div",{class:"nota"},"recebimentos menos pagamentos"))
  );
  const filtros = document.getElementById("fin-filtros");
  const segCart = h("div",{class:"segmento",role:"group","aria-label":"Carteira"},
    ["todas", ...f.carteiras].map(c => h("button",{"aria-pressed":String(estado.finCarteira===c), onclick:()=>{ estado.finCarteira=c; carregarFinanceiro(); }}, c==="todas"?"Todas":c)));
  const segStatus = h("div",{class:"segmento",role:"group","aria-label":"Situação"},
    [["pendentes","Pendentes"],["pagas","Pagas"],["todas","Todas"]].map(([k,r]) => h("button",{"aria-pressed":String(estado.finStatus===k), onclick:()=>{ estado.finStatus=k; carregarFinanceiro(); }}, r)));
  filtros.replaceChildren(segCart, segStatus);

  const passa = l => (estado.finCarteira==="todas" || l.carteira===estado.finCarteira)
    && (estado.finStatus==="todas" || (estado.finStatus==="pagas" ? !!l.pago_em : !l.pago_em));
  const tabela = document.getElementById("fin-tabela");
  tabela.replaceChildren(h("thead",{}, h("tr",{}, h("th",{},"Vencimento"), h("th",{},"Descrição"), h("th",{},"Carteira"), h("th",{style:"text-align:right"},"Valor"), h("th",{}))));
  const tb = h("tbody",{});
  const secao = (rot, linhas) => { const l = linhas.filter(passa); if (!l.length) return; tb.append(h("tr",{class:"secao"}, h("td",{colspan:"5"}, rot))); l.forEach(x => tb.append(linhaFin(x))); };
  secao("Em atraso de meses anteriores", f.atrasadas);
  secao(`Vencimentos de ${MESES[m-1]}`, f.lancamentos);
  secao("Sem data de vencimento, conferir", f.sem_data);
  if (!tb.children.length) tb.append(h("tr",{}, h("td",{colspan:"5",class:"vazio",style:"padding:22px 12px"},
    estado.finStatus==="pagas" ? "Nenhum lançamento pago neste filtro." : "Nada pendente neste filtro. Use Novo lançamento para cadastrar contas fixas, como aluguel e cartões.")));
  tabela.append(tb);

  const cart = document.getElementById("fin-carteiras");
  cart.replaceChildren(h("h2",{},"Por carteira"));
  const nomes = [...new Set([...f.carteiras, ...Object.keys(f.por_carteira)])];
  nomes.forEach(n => {
    const v = f.por_carteira[n] || {pagar:0,receber:0,pago:0,recebido:0};
    const total = v.pagar + v.pago;
    const pct = total ? Math.round(v.pago/total*100) : 0;
    cart.append(h("div",{class:"cart"},
      h("div",{class:"nome"}, n, h("span",{}, reais(v.pagar))),
      h("div",{class:"barra-cart",title:`${pct}% pago`}, h("i",{style:`width:${pct}%;background:var(--salvia)`}), h("i",{style:`width:${100-pct}%;background:${total?"var(--vinho)":"transparent"};opacity:.55`})),
      h("div",{class:"det"}, total ? `${reais(v.pago)} pago de ${reais(total)}` : "Sem contas neste mês",
        (v.receber + v.recebido) ? `. A receber: ${reais(v.receber)}` : "")));
  });
}
function linhaFin(l){
  const hoje = hojeISO();
  const atrasada = !l.pago_em && l.vencimento && l.vencimento < hoje;
  const tags = [];
  if (!l.confirmado && !l.pago_em) tags.push(h("span",{class:"tag confirmar"},"a confirmar"));
  if (atrasada) tags.push(h("span",{class:"tag atrasada"},"em atraso"));
  if (l.pago_em) tags.push(h("span",{class:"tag paga"}, (l.tipo==="receber"?"recebido ":"pago ") + ddmm(l.pago_em)));
  if (l.tipo === "receber" && !l.pago_em) tags.push(h("span",{class:"tag receber"},"a receber"));
  const extra = [l.categoria, l.recorrencia==="mensal" ? "todo mês" : l.recorrencia==="anual" ? "todo ano" : null, l.observacao].filter(Boolean).join(", ");
  return h("tr",{class:l.pago_em?"paga":""},
    h("td",{class:"data"}, l.vencimento ? ddmm(l.vencimento) : "sem data"),
    h("td",{}, h("span",{class:"desc"}, l.descricao), tags, extra ? h("small",{}, extra) : null),
    h("td",{}, l.carteira),
    h("td",{class:"valor"}, (l.tipo==="receber" ? "+ " : "") + reais(l.valor_centavos)),
    h("td",{class:"acoes"},
      h("button",{class:"btn pequeno", onclick:async()=>{
        try { const r = await api(`/api/financeiro/${l.id}/pagar`,{method:"POST",body:JSON.stringify({desfazer:!!l.pago_em})});
          avisar(l.pago_em ? "Pagamento desfeito." : r.proximo_id ? "Pago. A próxima ocorrência já foi lançada." : (l.tipo==="receber"?"Marcado como recebido.":"Marcado como pago."));
          carregarFinanceiro(); acompanharSilencioso(); } catch(err){ avisar(err.message); }
      }}, l.pago_em ? "Desfazer" : (l.tipo==="receber" ? "Recebido" : "Pagar")),
      h("button",{class:"btn pequeno", onclick:()=>abrirGaveta(l)},"Editar"),
      h("button",{class:"btn pequeno perigo", "aria-label":"Excluir", onclick:async()=>{
        try { await api(`/api/financeiro/${l.id}`,{method:"DELETE"}); carregarFinanceiro();
          avisarDesfazer(`“${l.descricao}” excluído.`, async () => { await api(`/api/financeiro/${l.id}/restaurar`,{method:"POST",body:"{}"}); carregarFinanceiro(); }); }
        catch(err){ avisar(err.message); }
      }},"Excluir")));
}
function acompanharSilencioso(){ carregarEstado().catch(()=>{}); }

/* ---------- gaveta ---------- */
const gaveta = document.getElementById("gaveta"), veu = document.getElementById("veu");
gaveta.querySelectorAll("[data-tipo]").forEach(b => b.onclick = () => definirTipo(b.dataset.tipo));
function definirTipo(t){ estado.tipoForm = t; gaveta.querySelectorAll("[data-tipo]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.tipo===t))); }
function abrirGaveta(l){
  estado.editando = l;
  document.getElementById("gaveta-titulo").textContent = l ? "Editar lançamento" : "Novo lançamento";
  const cart = document.getElementById("f-cart");
  cart.replaceChildren(...estado.cfg.carteiras.map(c => h("option",{value:c}, c)));
  if (l && !estado.cfg.carteiras.includes(l.carteira)) cart.append(h("option",{value:l.carteira}, l.carteira));
  document.getElementById("lista-cat").replaceChildren(...estado.cfg.categorias.map(c => h("option",{value:c})));
  definirTipo(l ? l.tipo : "pagar");
  document.getElementById("f-desc").value = l ? l.descricao : "";
  document.getElementById("f-valor").value = l && l.valor_centavos !== null ? (l.valor_centavos/100).toLocaleString("pt-BR",{minimumFractionDigits:2}) : "";
  document.getElementById("f-venc").value = l ? (l.vencimento || "") : "";
  cart.value = l ? l.carteira : (estado.finCarteira !== "todas" ? estado.finCarteira : estado.cfg.carteiras[0]);
  document.getElementById("f-cat").value = l ? (l.categoria || "") : "";
  document.getElementById("f-rec").value = l ? l.recorrencia : "nenhuma";
  document.getElementById("f-obs").value = l ? (l.observacao || "") : "";
  document.getElementById("f-erro").textContent = "";
  veu.classList.add("aberto"); gaveta.classList.add("aberta");
  setTimeout(()=>document.getElementById("f-desc").focus(), 60);
}
function fecharGaveta(){ veu.classList.remove("aberto"); gaveta.classList.remove("aberta"); }
veu.onclick = fecharGaveta;
document.getElementById("f-cancelar").onclick = fecharGaveta;
document.addEventListener("keydown", ev => { if (ev.key === "Escape"){ fecharGaveta(); fecharDetalhe(); } });
document.getElementById("f-salvar").onclick = async () => {
  const erro = document.getElementById("f-erro");
  try {
    const corpo = {
      tipo: estado.tipoForm,
      descricao: document.getElementById("f-desc").value,
      valor_centavos: lerReais(document.getElementById("f-valor").value),
      vencimento: document.getElementById("f-venc").value || null,
      carteira: document.getElementById("f-cart").value,
      categoria: document.getElementById("f-cat").value || null,
      recorrencia: document.getElementById("f-rec").value,
      observacao: document.getElementById("f-obs").value || null,
    };
    if (!corpo.descricao.trim()) throw new Error("Descreva o lançamento.");
    if (corpo.recorrencia !== "nenhuma" && !corpo.vencimento) throw new Error("Para repetir, informe o vencimento.");
    if (estado.editando) await api(`/api/financeiro/${estado.editando.id}`,{method:"PUT",body:JSON.stringify(corpo)});
    else await api("/api/financeiro",{method:"POST",body:JSON.stringify(corpo)});
    fecharGaveta(); avisar("Lançamento salvo."); carregarFinanceiro(); acompanharSilencioso();
  } catch(err){ erro.textContent = err.message; }
};
