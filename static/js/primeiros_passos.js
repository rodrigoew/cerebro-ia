"use strict";
/* ---------- PRIMEIROS PASSOS ---------- */
async function primeirosPassos(){
  const caixa = document.getElementById("boasvindas"); caixa.classList.add("aberto");
  const dados = {seu_nome:"", nome:"Núcleo", perfil:"", areas:"Pessoal, Trabalho", voz:"kokoro:pf_dora", cidade:null};
  let passo = 0;
  const passos = [
    () => [h("h1",{},"Olá. Vamos montar o seu segundo cérebro."), h("p",{},"Leva um minuto. Tudo fica neste computador."),
      h("label",{},"Como você quer ser chamado?"), h("input",{type:"text", value:dados.seu_nome, oninput:ev=>dados.seu_nome = ev.target.value}),
      h("label",{},"Que nome dar ao seu assistente?"), h("input",{type:"text", value:dados.nome, oninput:ev=>dados.nome = ev.target.value})],
    () => [h("h1",{},"Conte um pouco sobre você."), h("p",{},"Isso ajuda o assistente a entender seu contexto. Dá para mudar depois."),
      h("label",{},"O que você faz? (trabalho, negócios, rotina)"), h("textarea",{oninput:ev=>dados.perfil = ev.target.value}, dados.perfil),
      h("label",{},"Áreas da sua vida para separar finanças e assuntos (separe por vírgula)"), h("input",{type:"text", value:dados.areas, oninput:ev=>dados.areas = ev.target.value})],
    () => { const op = h("div",{class:"bv-op"}); const desenhar = () => op.replaceChildren(...[["kokoro:pf_dora","Dora","feminina"],["kokoro:pm_alex","Alex","masculina"],["kokoro:pm_santa","Santa","masculina"]].map(([id,n,g]) =>
        h("button",{"aria-pressed":String(dados.voz===id), onclick:()=>{ dados.voz = id; desenhar(); }}, n, h("small",{}, `Voz ${g}`)))); desenhar();
      return [h("h1",{},"Escolha a voz."), h("p",{},"As vozes rodam no seu computador, sem custo por uso. O instalador baixa as vozes no último passo."), op]; },
    () => { const busca = h("input",{type:"text", placeholder:"Sua cidade"}); const res = h("div",{class:"bv-op", style:"grid-template-columns:1fr"});
      const buscar = async () => { try { const r = await api(`/api/ajustes/cidades?q=${encodeURIComponent(busca.value)}`);
        res.replaceChildren(...r.cidades.slice(0,4).map(c => h("button",{"aria-pressed":String(dados.cidade && dados.cidade.latitude===c.latitude), onclick:ev=>{ dados.cidade = c; res.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed","false")); ev.currentTarget.setAttribute("aria-pressed","true"); }},
          `${c.cidade}${c.estado ? ", " + c.estado : ""}`, h("small",{}, c.pais)))); } catch(err){ avisar(err.message); } };
      busca.addEventListener("keydown", ev => { if (ev.key === "Enter") buscar(); });
      return [h("h1",{},"Onde você está?"), h("p",{},"Para o clima no briefing. Só o nome da cidade é consultado."), h("div",{style:"display:flex;gap:8px"}, busca, h("button",{class:"n-btn", onclick:buscar},"Buscar")), res]; },
    () => [h("h1",{},"Pronto para começar."), h("p",{},"Agora vamos instalar a IA local e as vozes (cerca de 9 GB, só uma vez). Depois, adicione suas contas de e-mail em Ajustes."),
      h("p",{},"Dica: diga “bom dia” no modo conversa para ouvir o briefing do dia.")],
  ];
  async function concluir(){
    try {
      await api("/api/ajustes",{method:"PUT",body:JSON.stringify({secao:"assistente", dados:{nome:dados.nome || "Núcleo", palavra_ativacao:dados.nome || "Núcleo", seu_nome:dados.seu_nome}})});
      await api("/api/ajustes",{method:"PUT",body:JSON.stringify({secao:"perfil", dados:{perfil:dados.perfil, areas:dados.areas.split(",").map(x => x.trim()).filter(Boolean), primeiro_uso:false}})});
      await api("/api/ajustes",{method:"PUT",body:JSON.stringify({secao:"voz", dados:{voz:dados.voz, velocidade:1.0}})}).catch(()=>{});
      if (dados.cidade) await api("/api/ajustes",{method:"PUT",body:JSON.stringify({secao:"clima", dados:{locais:[{...dados.cidade, mostrar:["agora","hoje"]}]}})});
    } catch(err){ avisar(err.message); return; }
    caixa.classList.remove("aberto"); await carregarEstado(); irPara("nucleo"); abrirInstalador();
  }
  function desenhar(){
    caixa.replaceChildren(h("div",{class:"bv-caixa"}, h("div",{class:"bv-passos"}, passos.map((_,i) => h("i",{class:i<=passo?"on":""}))), ...passos[passo](),
      h("div",{class:"bv-nav"}, passo ? h("button",{class:"n-btn", onclick:()=>{ passo--; desenhar(); }},"Voltar") : h("span"),
        h("button",{class:"n-btn forte", onclick:()=>{ if (passo < passos.length-1){ passo++; desenhar(); } else concluir(); }}, passo < passos.length-1 ? "Continuar" : "Instalar e começar"))));
  }
  desenhar();
}
