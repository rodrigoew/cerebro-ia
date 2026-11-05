"use strict";
/* ---------- início ---------- */
(async () => {
  try {
    const e = await carregarEstado();
    if (e.atualizando) acompanhar();
    else if (!e.resumo || (Date.now() - new Date(e.resumo.gerado_em)) > 60*60*1000) atualizar();
    estado.finMes = e.hoje.slice(0,7);
    if (!location.hash || location.hash === "#nucleo") irPara("nucleo");
    if (location.hash === "#briefing") iniciarBriefing();
    if (location.hash === "#nucleo") focarAssistente("nucleo");
    if (escutaContinuaLigada()) api("/api/cerebro/estado").then(i => { nucleo.info = i; if (i.voz_status && i.voz_status.ouvir) alternarConversa(true); }).catch(()=>{});
    api(`/api/financeiro?mes=${estado.finMes}`).then(f => {
      const n = [...f.lancamentos, ...f.atrasadas, ...f.sem_data].filter(l => !l.confirmado && !l.pago_em).length;
      document.getElementById("conta-fin").textContent = n ? String(n) : "";
    }).catch(()=>{});
  } catch(err){
    document.getElementById("tela-hoje").replaceChildren(h("p",{class:"carregando"}, "Não consegui falar com o aplicativo: " + err.message));
  }
})();
