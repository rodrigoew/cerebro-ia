"use strict";
/* ---------- MENTE ---------- */
const mt = {aba:"pensar", dados:null, decisao:null};
async function carregarMente(aba){
  if (aba) mt.aba = aba;
  const alvo = document.getElementById("tela-mente");
  try { mt.dados = await api("/api/mente"); } catch(err){ alvo.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  const abas = [["pensar","Organizar pensamentos"],["ideias","Ideias"],["decisoes","Decisões"],["processos","Processos"]];
  const corpo = h("div");
  alvo.replaceChildren(h("div",{class:"topo"}, h("div",{}, h("h1",{},"Mente"), h("div",{class:"sub"},`Pensamentos, ideias, decisões e processos. ${nomeAssist()} organiza; você decide.`))),
    h("div",{class:"abas",role:"tablist"}, abas.map(([k,r]) => h("button",{role:"tab","aria-selected":String(mt.aba===k), onclick:()=>carregarMente(k)}, r))), corpo);
  ({pensar:abaPensar, ideias:abaIdeias, decisoes:abaDecisoes, processos:abaProcessos})[mt.aba](corpo);
}
function abaPensar(corpo){
  const area = h("textarea",{placeholder:"Escreva tudo o que está na sua cabeça, do jeito que vier. Ex.: preciso pagar o IPVA até sexta, pensei em lançar um curso, não sei se troco de notebook agora..."});
  const res = h("div",{class:"desp-itens"});
  corpo.replaceChildren(h("div",{class:"despejo"}, area, h("div",{class:"acoes-aj", style:"display:flex;gap:8px;margin-top:10px"},
    h("button",{class:"btn primario", onclick:async ev=>{ ev.target.disabled = true; ev.target.textContent = "Organizando…";
      try { const r = await api("/api/mente/organizar",{method:"POST",body:JSON.stringify({texto:area.value})}); mostrarItens(r.itens); }
      catch(err){ avisar(err.message); } ev.target.disabled = false; ev.target.textContent = "Organizar"; }},"Organizar"))), res);
  function mostrarItens(itens){
    const estado = itens.map(i => ({...i, guardar:true}));
    res.replaceChildren(...estado.map(i => h("div",{class:"desp-item"},
      h("input",{type:"checkbox", checked:true, onchange:ev=>i.guardar = ev.target.checked}),
      h("select",{onchange:ev=>i.tipo = ev.target.value}, [["tarefa","Tarefa"],["lembrete","Lembrete"],["ideia","Ideia"],["decisao","Decisão"],["nota","Nota"]].map(([k,r]) => h("option",{value:k, selected:i.tipo===k}, r))),
      h("input",{type:"text", value:i.texto + (i.quando ? ` (${i.quando})` : ""), oninput:ev=>i.texto = ev.target.value}))),
      h("div",{style:"display:flex;gap:8px"}, h("button",{class:"btn primario", onclick:async()=>{
        try { const r = await api("/api/mente/guardar",{method:"POST",body:JSON.stringify({itens:estado.filter(x => x.guardar)})});
          avisar("Guardado: " + Object.entries(r.guardados).map(([k,v]) => `${v} ${k}`).join(", ")); area.value = ""; res.replaceChildren(); }
        catch(err){ avisar(err.message); } }},"Guardar selecionados")));
  }
}
function abaIdeias(corpo){
  const nomes = {nova:"Novas", explorando:"Explorando", em_andamento:"Em andamento", feita:"Feitas", descartada:"Descartadas"};
  const ordem = Object.keys(nomes);
  const nova = h("input",{type:"text", placeholder:"Nova ideia", style:"flex:1;border:1px solid var(--linha);border-radius:7px;padding:8px 10px;background:var(--painel)"});
  const add = async () => { if (!nova.value.trim()) return; await api("/api/mente/ideias",{method:"POST",body:JSON.stringify({titulo:nova.value})}); carregarMente(); };
  nova.addEventListener("keydown", ev => { if (ev.key === "Enter") add(); });
  const mover = async (i, d) => { const k = ordem[Math.max(0, Math.min(ordem.length-1, ordem.indexOf(i.estado)+d))];
    await api(`/api/mente/ideias/${i.id}`,{method:"PUT",body:JSON.stringify({estado:k})}); carregarMente(); };
  corpo.replaceChildren(h("div",{style:"display:flex;gap:8px;margin-bottom:12px"}, nova, h("button",{class:"btn primario", onclick:add},"Adicionar")),
    h("div",{class:"kanban"}, ordem.map(k => { const lista = mt.dados.ideias.filter(i => i.estado === k);
      return h("div",{class:"coluna-k"}, h("h3",{}, nomes[k], h("span",{}, lista.length)), lista.map(i => h("div",{class:"ideia"},
        h("span",{}, i.titulo), i.projeto ? h("small",{}, i.projeto) : null,
        h("div",{class:"mv"}, h("button",{"aria-label":"Voltar", disabled:k===ordem[0], onclick:()=>mover(i,-1)},"←"),
          h("button",{"aria-label":"Avançar", disabled:k===ordem[ordem.length-1], onclick:()=>mover(i,1)},"→"),
          h("button",{"aria-label":"Apagar", onclick:()=>apagarIdeia(i)},"×"))))); })));
  corpo.querySelectorAll(".ideia").forEach((el, n) => {
    const i = mt.dados.ideias.find(x => x.titulo === el.firstChild.textContent);
    el.tabIndex = 0; el.setAttribute("aria-label", `${i ? i.titulo : ""}. Setas para mover entre colunas, Delete para apagar.`);
    el.addEventListener("keydown", ev => { if (!i) return;
      if (ev.key === "ArrowRight"){ ev.preventDefault(); mover(i, 1); }
      else if (ev.key === "ArrowLeft"){ ev.preventDefault(); mover(i, -1); }
      else if (ev.key === "Delete"){ ev.preventDefault(); apagarIdeia(i); } });
  });
  function apagarIdeia(i){
    mt.dados.ideias = mt.dados.ideias.filter(x => x.id !== i.id); abaIdeias(corpo);
    avisarDesfazer(`Ideia “${i.titulo.slice(0,40)}” apagada.`, () => carregarMente(), () => api(`/api/mente/ideias/${i.id}`,{method:"DELETE"}));
  }
}
function abaDecisoes(corpo){
  const ds = mt.dados.decisoes;
  if (!mt.decisao && ds.length) mt.decisao = ds[0].id;
  const nova = h("input",{type:"text", placeholder:"Qual decisão? Ex.: contratar estagiário ou terceirizar o suporte", style:"flex:1;border:1px solid var(--linha);border-radius:7px;padding:8px 10px;background:var(--painel)"});
  const criar = async ev => { if (!nova.value.trim()) return; ev && (ev.target.disabled = true);
    try { const r = await api("/api/mente/decisoes",{method:"POST",body:JSON.stringify({pergunta:nova.value})}); mt.decisao = r.id; carregarMente(); } catch(err){ avisar(err.message); } };
  const lista = h("div",{style:"display:grid;gap:6px;align-content:start"}, ds.map(d => h("button",{class:"dec-item","aria-current":String(d.id===mt.decisao), onclick:()=>{ mt.decisao = d.id; carregarMente(); }},
    h("strong",{}, d.pergunta), h("small",{}, d.estado === "aberta" ? "Em aberto" : `Decidido: ${d.escolha}`))));
  const d = ds.find(x => x.id === mt.decisao);
  let detalhe = h("p",{class:"vazio"},"Registre uma decisão para pensar com ajuda.");
  if (d){
    const escolha = h("input",{type:"text", value:d.escolha || "", placeholder:"O que você decidiu?"});
    const motivo = h("input",{type:"text", value:d.motivo || "", placeholder:"Por quê?"});
    const revisar = h("input",{type:"date", value:d.revisar_em || ""});
    const resultado = h("input",{type:"text", value:d.resultado || "", placeholder:"Depois: como foi? (aprendizado)"});
    detalhe = h("section",{class:"painel aj", style:"display:grid;gap:12px"},
      h("h2",{}, d.pergunta),
      d.opcoes.length ? h("div",{class:"opcoes"}, d.opcoes.map(o => h("div",{class:"opcao"+(d.escolha && d.escolha === o.nome ? " escolhida" : "")},
        h("h4",{}, o.nome), o.pros.length ? h("ul",{}, o.pros.map(x => h("li",{class:"pro"}, x))) : null,
        o.contras.length ? h("ul",{}, o.contras.map(x => h("li",{class:"contra"}, x))) : null,
        h("button",{class:"btn pequeno", onclick:()=>{ escolha.value = o.nome; motivo.focus(); }},"Escolher esta")))) : null,
      d.criterios.length ? h("p",{style:"margin:0"}, h("strong",{},"Critérios: "), d.criterios.join(", ")) : null,
      d.perguntas.length ? h("div",{}, h("strong",{},"Perguntas para pensar"), h("ul",{style:"margin:4px 0 0"}, d.perguntas.map(q => h("li",{}, q)))) : null,
      h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Decisão"), escolha), h("div",{}, h("label",{class:"rot"},"Motivo"), motivo)),
      h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Revisar em"), revisar), h("div",{}, h("label",{class:"rot"},"Resultado"), resultado)),
      h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
        try { await api(`/api/mente/decisoes/${d.id}`,{method:"PUT",body:JSON.stringify({escolha:escolha.value, motivo:motivo.value, revisar_em:revisar.value || null, resultado:resultado.value,
          estado: resultado.value ? "revisada" : (escolha.value ? "decidida" : "aberta")})});
          avisar(escolha.value ? "Decisão registrada. Ela entra no que eu sei sobre você." : "Salvo."); definirHumor("sucesso", 5000); emitirOnda("sucesso"); carregarMente(); } catch(err){ avisar(err.message); } }},"Salvar"),
        h("button",{class:"btn", onclick:async ev=>{ ev.target.disabled = true; ev.target.textContent = "Analisando…"; try { await api(`/api/mente/decisoes/${d.id}/analisar`,{method:"POST",body:"{}"}); carregarMente(); } catch(err){ avisar(err.message); } }},"Analisar de novo"),
        h("button",{class:"btn perigo", onclick:()=>{ mt.dados.decisoes = mt.dados.decisoes.filter(x => x.id !== d.id); mt.decisao = null; abaDecisoes(corpo);
          avisarDesfazer("Decisão apagada.", () => carregarMente(), () => api(`/api/mente/decisoes/${d.id}`,{method:"DELETE"})); }},"Apagar")));
  }
  corpo.replaceChildren(h("div",{style:"display:flex;gap:8px;margin-bottom:12px"}, nova, h("button",{class:"btn primario", onclick:criar},"Pensar com ajuda")),
    h("div",{class:"dec-lista"}, lista, detalhe));
}
function abaProcessos(corpo){
  const nome = h("input",{type:"text", placeholder:"Nome do processo (ex.: Fechamento do mês)", style:"flex:1;border:1px solid var(--linha);border-radius:7px;padding:8px 10px;background:var(--painel)"});
  const passos = h("textarea",{placeholder:"Um passo por linha (ou deixe vazio para a IA sugerir)", style:"width:100%;min-height:90px;border:1px solid var(--linha);border-radius:7px;padding:8px 10px;background:var(--painel);margin-top:8px"});
  const lista = h("div",{style:"display:grid;gap:12px;margin-top:16px"});
  mt.dados.processos.forEach(p => {
    const ex = p.execucao && !p.execucao.concluido_em ? p.execucao : null;
    const feitos = new Set(ex ? ex.feitos : []);
    const barra = h("i",{style:`width:${ex ? Math.round(feitos.size/p.passos.length*100) : 0}%`});
    lista.append(h("div",{class:"proc"},
      h("h3",{}, p.nome, h("span",{style:"display:flex;gap:6px"},
        ex ? null : h("button",{class:"btn pequeno primario", onclick:async()=>{ await api(`/api/mente/processos/${p.id}/iniciar`,{method:"POST",body:"{}"}); carregarMente(); }},"Iniciar"),
        h("button",{class:"btn pequeno perigo", onclick:()=>{ mt.dados.processos = mt.dados.processos.filter(x => x.id !== p.id); abaProcessos(corpo);
          avisarDesfazer(`Processo “${p.nome}” apagado.`, () => carregarMente(), () => api(`/api/mente/processos/${p.id}`,{method:"DELETE"})); }},"Apagar"))),
      ex ? h("div",{class:"barra-prog"}, barra) : h("small",{style:"color:var(--suave)"}, p.execucao && p.execucao.concluido_em ? `Última execução concluída em ${p.execucao.concluido_em.slice(8,10)}/${p.execucao.concluido_em.slice(5,7)}` : `${p.passos.length} passos`),
      h("ul",{class:"passos"}, p.passos.map((x,i) => h("li",{}, h("label",{}, ex ? h("input",{type:"checkbox", checked:feitos.has(i), onchange:async ev=>{
        const r = await api(`/api/mente/execucoes/${ex.id}/passo`,{method:"POST",body:JSON.stringify({indice:i, feito:ev.target.checked})});
        barra.style.width = Math.round(r.feitos.length/r.total*100)+"%"; ev.target.closest("label").querySelector("span").className = ev.target.checked ? "feito" : "";
        if (r.concluido){ avisar("Processo concluído!"); definirHumor("sucesso", 5000); emitirOnda("sucesso"); carregarMente(); } }}) : h("span",{style:"color:var(--suave);min-width:18px"}, `${i+1}.`),
        h("span",{class:feitos.has(i) ? "feito" : ""}, x)))))));
  });
  corpo.replaceChildren(h("div",{style:"display:flex;gap:8px"}, nome, h("button",{class:"btn primario", onclick:async ev=>{
      if (!nome.value.trim()) return; ev.target.disabled = true;
      const lista = passos.value.split("\n").map(x => x.trim()).filter(Boolean);
      try { await api("/api/mente/processos",{method:"POST",body:JSON.stringify({nome:nome.value, passos:lista, sugerir:!lista.length})}); carregarMente(); }
      catch(err){ avisar(err.message); ev.target.disabled = false; } }},"Criar processo")), passos,
    mt.dados.processos.length ? lista : h("p",{class:"vazio", style:"margin-top:14px"},"Nenhum processo ainda. Rotinas repetidas viram checklists aqui."));
}
