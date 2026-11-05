"use strict";
/* ---------- PESSOAS E COMPROMISSOS ---------- */
const ps = {atual:null, busca:"", aba:"pessoas"};
async function carregarPessoas(){
  const alvo = document.getElementById("tela-pessoas");
  const abas = [["pessoas","Pessoas"],["compromissos","Compromissos"]];
  const corpo = h("div");
  alvo.replaceChildren(h("div",{class:"topo"}, h("div",{}, h("h1",{},"Pessoas"),
      h("div",{class:"sub"},"Quem está na sua vida e o que foi combinado. Promessas são detectadas nos e-mails, localmente."))),
    h("div",{class:"abas",role:"tablist"}, abas.map(([k,r]) => h("button",{role:"tab","aria-selected":String(ps.aba===k), onclick:()=>{ ps.aba = k; carregarPessoas(); }}, r))), corpo);
  if (ps.aba === "compromissos") return abaCompromissos(corpo);
  let lista;
  try { lista = (await api(`/api/pessoas?busca=${encodeURIComponent(ps.busca)}`)).pessoas; } catch(err){ corpo.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  if (!ps.atual && lista.length) ps.atual = lista[0].email;
  const buscaEl = h("input",{type:"search", value:ps.busca, placeholder:"Buscar pessoa", class:"campo-busca",
    onkeydown:ev=>{ if (ev.key === "Enter"){ ps.busca = ev.target.value; carregarPessoas(); } }});
  const ficha = h("section",{class:"painel ficha"}, h("p",{class:"vazio"}, lista.length ? "Escolha uma pessoa." : "Nenhuma pessoa ainda. Elas aparecem conforme os e-mails são lidos."));
  corpo.replaceChildren(h("div",{class:"pes"},
    h("div",{class:"pes-lista"}, buscaEl, h("div",{class:"cx-itens"}, lista.map(p => h("button",{class:"cx-item", "aria-current":String(p.email===ps.atual), onclick:()=>{ ps.atual = p.email; carregarPessoas(); }},
      h("div",{class:"l1"}, h("span",{class:"de"}, p.nome), p.compromissos ? h("span",{class:"tag confirmar", style:"margin:0"}, `${p.compromissos} pendente(s)`) : null),
      h("span",{class:"pv"}, `${p.email} · ${p.interacoes} e-mail(s) · ${(p.ultimo || "").slice(8,10)}/${(p.ultimo || "").slice(5,7)}`))))),
    ficha));
  if (ps.atual) desenharFicha(ficha, ps.atual);
}
async function desenharFicha(caixa, email){
  let f; try { f = await api(`/api/pessoas/${encodeURIComponent(email)}`); } catch(err){ caixa.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  const hoje = estado.cfg ? estado.cfg.hoje : "";
  const resumo = h("p",{class:"resumo-rel"});
  const sec = (titulo, conteudo) => conteudo && conteudo.length ? h("div",{class:"ficha-sec"}, h("h3",{}, titulo), ...conteudo) : null;
  const linhaComp = c => h("div",{class:"comp"+(c.prazo && c.prazo < hoje ? " atrasado" : "")},
    h("span",{}, h("b",{}, c.direcao === "eu_devo" ? "Você deve: " : "Deve a você: "), c.texto,
      h("small",{}, c.prazo ? ` · prazo ${c.prazo.slice(8,10)}/${c.prazo.slice(5,7)}` : " · sem prazo")),
    h("span",{class:"comp-acoes"},
      h("button",{class:"btn pequeno", onclick:async()=>{ await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({estado:"cumprido"})}); definirHumor("sucesso",4000); carregarPessoas(); }},"Cumprido"),
      h("button",{class:"btn pequeno", onclick:async()=>{ const d = new Date(); d.setDate(d.getDate()+1); await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({prazo:iso(d)})}); carregarPessoas(); }},"Adiar 1 dia"),
      h("button",{class:"btn pequeno perigo", onclick:async()=>{ await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({estado:"descartado"})});
        avisarDesfazer("Compromisso descartado.", async()=>{ await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({estado:"aberto"})}); carregarPessoas(); }); carregarPessoas(); }},"Descartar")));
  const novoTexto = h("input",{type:"text", placeholder:"Novo combinado (ex.: enviar a proposta revisada)"});
  const novoPrazo = h("input",{type:"date"});
  const novoDir = h("select",{}, h("option",{value:"eu_devo"},"Eu devo"), h("option",{value:"me_devem"},"Me deve"));
  caixa.replaceChildren(...[
    h("div",{class:"ficha-topo"}, h("div",{}, h("h2",{}, f.nome), h("div",{class:"cx-meta"}, `${f.email} · ${f.recebidos} recebido(s), ${f.enviados} enviado(s)`)),
      h("button",{class:"btn", onclick:async ev=>{ ev.target.disabled = true; ev.target.textContent = "Resumindo…";
        try { resumo.textContent = (await api(`/api/pessoas/${encodeURIComponent(email)}/resumo`,{method:"POST",body:"{}"})).resumo; } catch(err){ avisar(err.message); }
        ev.target.disabled = false; ev.target.textContent = "Resumo da relação"; }},"Resumo da relação")),
    resumo,
    sec("Compromissos em aberto", f.compromissos.map(linhaComp)),
    h("div",{class:"novo-comp"}, novoDir, novoTexto, novoPrazo, h("button",{class:"btn primario", onclick:async()=>{
      try { await api("/api/compromissos",{method:"POST",body:JSON.stringify({direcao:novoDir.value, texto:novoTexto.value, pessoa:f.email, prazo:novoPrazo.value || null})}); carregarPessoas(); } catch(err){ avisar(err.message); } }},"Adicionar")),
    sec("Na agenda", f.eventos.map(e => h("p",{}, `${e.quando}: ${e.titulo}`))),
    sec("Conversas recentes", f.mensagens.map(m => h("button",{class:"msg-linha", onclick:()=>{ irPara("emails"); setTimeout(() => abrirEmail(m.id), 400); }},
      h("b",{}, (m.direcao === "recebido" ? "← " : "→ ") + m.assunto), h("small",{}, ` ${(m.data || "").slice(8,10)}/${(m.data || "").slice(5,7)} · ${m.previa}`)))),
    sec("Decisões ligadas", f.decisoes.map(d => h("p",{}, `${d.pergunta}${d.escolha ? " → " + d.escolha : ""}`))),
    sec("Notas", f.notas.map(n => h("p",{}, n.texto))),
    sec("O que sei", f.conhecimento.map(k => h("p",{}, k.texto))),
  ].filter(Boolean));
}
async function abaCompromissos(corpo){
  let lista; try { lista = (await api("/api/compromissos?estado=aberto")).compromissos; } catch(err){ corpo.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  const hoje = estado.cfg ? estado.cfg.hoje : "";
  const coluna = (titulo, itens) => h("div",{class:"coluna-k"}, h("h3",{}, titulo, h("span",{}, itens.length)),
    ...(itens.length ? itens.map(c => h("div",{class:"ideia"+(c.prazo && c.prazo < hoje ? " atrasado" : "")},
      h("span",{}, c.texto), h("small",{}, `${c.pessoa_nome || c.pessoa || "sem pessoa"}${c.prazo ? " · " + c.prazo.slice(8,10) + "/" + c.prazo.slice(5,7) : ""}`),
      h("div",{class:"mv"}, h("button",{onclick:async()=>{ await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({estado:"cumprido"})}); carregarPessoas(); }},"Cumprido"),
        h("button",{onclick:async()=>{ await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({estado:"descartado"})});
          avisarDesfazer("Descartado.", async()=>{ await api(`/api/compromissos/${c.id}`,{method:"PUT",body:JSON.stringify({estado:"aberto"})}); carregarPessoas(); }); carregarPessoas(); }},"Descartar"))))
      : [h("small",{class:"vazio"},"Nada aqui.")]));
  corpo.replaceChildren(h("div",{class:"comp-colunas"}, coluna("Você prometeu", lista.filter(c => c.direcao === "eu_devo")),
    coluna("Prometeram a você", lista.filter(c => c.direcao === "me_devem"))));
}
