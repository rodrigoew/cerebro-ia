"use strict";
/* ---------- E-MAILS ---------- */
const cx = {filtro:"todos", conta:"", busca:"", atual:null, lista:[]};
async function carregarEmails(){
  const alvo = document.getElementById("tela-emails");
  let d;
  try { d = await api(`/api/emails?filtro=${cx.filtro}&conta=${encodeURIComponent(cx.conta)}&busca=${encodeURIComponent(cx.busca)}`); }
  catch(err){ alvo.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  cx.lista = d.emails;
  if (!alvo.querySelector(".cx")){
    const busca = h("input",{type:"search", placeholder:"Buscar", value:cx.busca, onkeydown:ev=>{ if (ev.key === "Enter"){ cx.busca = ev.target.value; carregarEmails(); } }});
    const contaSel = h("select",{onchange:ev=>{ cx.conta = ev.target.value; carregarEmails(); }}, h("option",{value:""},"Todas as contas"), d.contas.map(c => h("option",{value:c}, c)));
    const filtros = h("div",{class:"segmento",role:"group"}, [["todos","Todos"],["nao_lidos","Não lidos"],["resposta","Pedem resposta"],["importantes","Importantes"],["pessoas","Pessoas"]].map(([k,r]) =>
      h("button",{"data-f":k, "aria-pressed":String(cx.filtro===k), onclick:()=>{ cx.filtro = k; alvo.querySelectorAll("[data-f]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.f===k))); carregarEmails(); }}, r)));
    alvo.replaceChildren(
      h("div",{class:"topo"}, h("div",{}, h("h1",{},"E-mails"), h("div",{class:"sub"},"Todas as contas num lugar só. Respostas viram rascunhos: o envio é sempre seu, no seu programa de e-mail.")),
        h("button",{class:"btn", onclick:()=>{ atualizar(); avisar("Buscando e-mails novos…"); setTimeout(carregarEmails, 8000); }},"Buscar novos")),
      h("div",{class:"cx-filtros"}, filtros, contaSel, busca),
      h("div",{class:"cx"}, h("div",{class:"cx-lista"}, h("div",{class:"cx-itens", id:"cx-itens"})), h("section",{class:"painel cx-leitor", id:"cx-leitor"}, h("p",{class:"vazio"},"Escolha uma mensagem."))));
    if (!d.contas.length) document.getElementById("cx-leitor").replaceChildren(h("p",{class:"vazio"},"Nenhuma conta configurada."), h("button",{class:"btn primario", onclick:()=>irPara("ajustes")},"Adicionar conta em Ajustes"));
  }
  const itens = document.getElementById("cx-itens");
  itens.replaceChildren(...(d.emails.length ? d.emails.map(e => h("button",{class:"cx-item"+(e.lida?"":" nao-lida"), "aria-current":String(cx.atual===e.id), onclick:()=>abrirEmail(e.id)},
    h("div",{class:"l1"}, h("span",{class:"de"}, e.de_nome || e.de), h("small",{style:"color:var(--suave);white-space:nowrap"}, e.data ? `${e.data.slice(8,10)}/${e.data.slice(5,7)} ${e.data.slice(11,16)}` : "")),
    h("span",{class:"as"}, e.assunto),
    e.previa ? h("span",{class:"pv"}, e.previa) : null,
    h("span",{class:"tags"}, h("span",{class:"tag", style:"margin:0;background:var(--painel-2)"}, e.conta),
      (!e.respondida && !e.automatica && e.pontos >= 50) ? h("span",{class:"tag confirmar", style:"margin:0"},"pede resposta") : null,
      e.sinalizada ? h("span",{class:"tag atrasada", style:"margin:0"},"sinalizada") : null)))
    : [h("p",{class:"vazio", style:"padding:16px;background:var(--painel)"},"Nada neste filtro.")]));
}
async function abrirEmail(id){
  cx.atual = id;
  document.querySelectorAll(".cx-item").forEach(b => b.setAttribute("aria-current","false"));
  const leitor = document.getElementById("cx-leitor");
  leitor.replaceChildren(h("p",{class:"vazio"},"Abrindo…"));
  let e; try { e = await api(`/api/emails/${id}`); } catch(err){ leitor.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  const editorBox = h("div");
  const acao = (a, rot, perigo) => h("button",{class:"btn"+(perigo?" perigo":""), onclick:async()=>{
    if (a === "arquivar" && !confirm("Arquivar esta mensagem no servidor?")) return;
    try { const r = await api(`/api/emails/${id}/acao`,{method:"POST",body:JSON.stringify({acao:a})}); avisar(r.mensagem); carregarEmails(); } catch(err){ avisar(err.message); } }}, rot);
  leitor.replaceChildren(...[
    h("h2",{}, e.assunto),
    h("div",{class:"cx-meta"}, `De ${e.de_nome ? e.de_nome + " <" + e.de + ">" : e.de}, ${e.data ? e.data.slice(8,10)+"/"+e.data.slice(5,7)+"/"+e.data.slice(0,4)+" "+e.data.slice(11,16) : ""}, conta ${e.conta}`),
    h("div",{class:"cx-acoes"},
      h("button",{class:"btn primario", onclick:()=>abrirEditor(e, editorBox)},"Rascunhar resposta"),
      acao(e.lida ? "nao_lida" : "lida", e.lida ? "Marcar como não lida" : "Marcar como lida"),
      e.tipo_conta !== "pop" ? acao(e.sinalizada ? "tirar_sinal" : "sinalizar", e.sinalizada ? "Tirar sinal" : "Sinalizar") : null,
      e.tipo_conta !== "pop" ? acao("arquivar","Arquivar", true) : null),
    editorBox,
    e.erro ? h("p",{class:"vazio"}, e.erro) : null,
    h("div",{class:"cx-corpo"}, (e.corpo || "(sem conteúdo)").slice(0, 20000))].filter(Boolean));
}
function abrirEditor(e, caixa){
  const instr = h("input",{type:"text", placeholder:"O que responder? Ex.: aceitar a proposta e pedir a nota fiscal até sexta"});
  const tom = h("select",{}, ["cordial e profissional","direto e objetivo","amigável e informal","formal"].map(t => h("option",{value:t}, t)));
  const para = h("input",{type:"text", value:e.de}), cc = h("input",{type:"text", value:""});
  const assunto = h("input",{type:"text", value:e.assunto.toLowerCase().startsWith("re:") ? e.assunto : "Re: " + e.assunto});
  const corpo = h("textarea",{placeholder:"Clique em Redigir com a IA local ou escreva aqui."});
  const st = h("span",{class:"status-aj"});
  caixa.replaceChildren(h("div",{class:"cx-editor"},
    h("div",{class:"linha"}, "Orientação", h("div",{style:"display:grid;grid-template-columns:1fr 200px auto;gap:8px"}, instr, tom,
      h("button",{class:"btn", onclick:async ev=>{ ev.target.disabled = true; ev.target.textContent = "Redigindo…";
        try { const r = await api(`/api/emails/${e.id}/rascunho`,{method:"POST",body:JSON.stringify({instrucao:instr.value, tom:tom.value})});
          corpo.value = r.corpo; assunto.value = r.assunto; para.value = r.para; }
        catch(err){ avisar(err.message); } ev.target.disabled = false; ev.target.textContent = "Redigir com a IA local"; }},"Redigir com a IA local"))),
    h("div",{class:"linha"}, "Para", para), h("div",{class:"linha"}, "Cc", cc), h("div",{class:"linha"}, "Assunto", assunto),
    corpo,
    h("div",{class:"cx-acoes"},
      h("button",{class:"btn primario", onclick:async()=>{
        try { const r = await api(`/api/emails/${e.id}/salvar-rascunho`,{method:"POST",body:JSON.stringify({para:para.value, cc:cc.value, assunto:assunto.value, corpo:corpo.value})});
          avisar(r.mensagem); statusAj(st, "Rascunho salvo.");
          if (r.mailto) caixa.querySelector(".cx-acoes").append(h("a",{class:"btn", href:r.mailto},"Abrir no meu programa de e-mail")); }
        catch(err){ avisar(err.message); } }},"Salvar como rascunho"),
      h("button",{class:"btn", onclick:()=>caixa.replaceChildren()},"Descartar"), st,
      h("small",{style:"color:var(--suave)"},"Nada é enviado. O rascunho aparece na pasta Rascunhos da conta.")))); 
  instr.focus();
}
