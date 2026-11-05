"use strict";
/* ---------- HOJE ---------- */
function desenharHoje(e){
  const alvo = document.getElementById("tela-hoje");
  alvo.replaceChildren();
  const r = e.resumo;
  const hoje = new Date();
  const titulo = `Bom dia${e.nome ? ", "+e.nome : ""}.`;
  alvo.append(h("div",{class:"topo"},
    h("div",{}, h("h1",{},titulo),
      h("div",{class:"sub"}, r ? r.data_longa : `${DSEM[hoje.getDay()]}, ${hoje.getDate()} de ${MESES[hoje.getMonth()]}`))));
  if (!r){
    alvo.append(h("p",{class:"carregando"}, e.atualizando ? "Lendo seus e-mails e agendas pela primeira vez." :
      "Ainda não há resumo. Clique em Atualizar agora."));
    return;
  }
  const grade = h("div",{class:"hoje"});
  const tres = h("section",{class:"tres","aria-label":"As 3 que mais importam"}, h("h2",{},"As 3 que mais importam"));
  if (!r.tres.length) tres.append(h("p",{class:"vazio"},"Nada urgente nos e-mails lidos nem no financeiro."));
  r.tres.forEach((t,i) => {
    const atraso = /venceu/.test(t.porque);
    const acoes = t.tipo === "conta" ? h("div",{class:"acoes"},
      h("button",{class:"btn pequeno", onclick:async ev=>{
        ev.target.disabled = true;
        try { await api(`/api/financeiro/${t.lancamento_id}/pagar`,{method:"POST",body:"{}"});
          avisar(t.receber ? "Marcado como recebido." : "Marcado como pago."); ev.target.textContent = t.receber ? "Recebido" : "Pago"; }
        catch(err){ avisar(err.message); ev.target.disabled = false; }
      }}, t.receber ? "Marcar como recebido" : "Marcar como pago"),
      h("button",{class:"btn pequeno", onclick:()=>irPara("financeiro")},"Ver no Financeiro")) : null;
    tres.append(h("article",{class:"painel item"+(atraso?" atraso":"")},
      h("span",{class:"num"}, String(i+1)),
      h("h3",{},t.titulo), h("p",{},t.oque),
      h("p",{class:"porque"}, "Por que hoje: ", h("b",{},t.porque)),
      h("p",{class:"acao"}, t.acao), acoes));
  });
  grade.append(tres);

  const lado = h("div",{class:"lado"});
  const comp = h("section",{class:"painel compromissos","aria-label":"Compromissos de hoje"}, h("h2",{},"Compromissos de hoje"));
  if (!estado.cfg.agendas.length) comp.append(h("p",{class:"vazio"},"Nenhuma agenda configurada no config.json."));
  else if (!r.compromissos.length) comp.append(h("p",{class:"vazio"},"Nenhum compromisso hoje."));
  r.compromissos.forEach(c => comp.append(h("div",{class:"ev"},
    h("span",{class:"hora"}, c.hora),
    h("span",{}, h("span",{class:"t"}, h("i",{style:`background:${corAgenda(c.agenda_idx)}`}), c.titulo),
      c.quem && c.quem !== "só você" ? h("span",{class:"quem"}, " com ", c.quem) : null),
    h("span",{class:"ctx"}, c.contexto))));
  lado.append(comp);
  lado.append(h("div",{class:"esperar"}, h("strong",{}, String(r.esperar)), h("span",{}, r.esperar === 1 ? "e-mail pode esperar" : "e-mails podem esperar")));
  r.lembretes.forEach(l => lado.append(h("div",{class:"lembrete"}, l)));
  (e.lembretes_hoje || []).forEach(l => lado.append(h("div",{class:"lembrete"},
    l.texto, h("span",{style:"font-weight:400;color:var(--suave)"}, l.data && l.data < e.hoje ? ` (desde ${ddmm(l.data)})` : l.hora ? ` às ${l.hora}` : ""))));
  grade.append(lado);

  const resp = h("section",{class:"resposta","aria-label":"Precisa de resposta"}, h("h2",{},"Precisa de resposta"));
  if (!r.resposta.length) resp.append(h("p",{class:"vazio"},"Nenhuma resposta pendente além das 3 acima."));
  else resp.append(h("ol",{}, r.resposta.map(x => h("li",{},
    h("span",{}, h("span",{class:"de"}, x.de), " sobre ", x.assunto, x.sem_abrir ? " (não consegui abrir o conteúdo)" : ""),
    h("span",{class:"meta"}, `${x.conta}, ${x.idade ? "há "+x.idade+(x.idade===1?" dia":" dias") : "hoje"}`)))));
  grade.append(resp);

  if (r.falhas.length) grade.append(h("ul",{class:"falhas"}, r.falhas.map(f => h("li",{},f))));
  alvo.append(grade);
}
