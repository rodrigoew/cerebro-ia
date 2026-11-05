"use strict";
/* ---------- AJUSTES ---------- */
let ajustes = null;
function nomeAssist(){ return (estado.cfg && estado.cfg.assistente) || "Núcleo"; }
function aplicarNomeAssistente(){
  const n = nomeAssist();
  const b = document.querySelector('.nav button[data-tela="nucleo"]'); if (b) b.textContent = n;
  document.title = `Núcleo · ${n}`;
  ESTADOS.sentinela = ["Em escuta", `Diga “${(ajustes && ajustes.assistente.palavra_ativacao) || n}” ou “bom dia”. Tudo é processado neste computador.`];
  const inp = document.getElementById("n-input"); if (inp) inp.placeholder = `Fale com ${n}: pergunte, anote ou peça algo…  (Ctrl+Shift+K)`;
}
function statusAj(el, msg){ el.textContent = msg; setTimeout(()=>{ if (el.textContent === msg) el.textContent = ""; }, 4000); }
async function salvarAj(secao, dados, statusEl){
  try { const r = await api("/api/ajustes",{method:"PUT",body:JSON.stringify({secao, dados})}); ajustes = r.ajustes; statusAj(statusEl, "Salvo."); return true; }
  catch(err){ statusAj(statusEl, ""); avisar(err.message); return false; }
}
let audioAmostra = null;
async function ouvirAmostra(voz, velocidade, texto){
  try {
    const r = await fetch("/api/voz/falar",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({texto: texto || `Olá${estado.cfg && estado.cfg.nome ? ", " + estado.cfg.nome : ""}. Eu sou ${nomeAssist()}. Amanhã a mínima será de 17 graus e a máxima de 28.`, voz, velocidade})});
    if (!r.ok){ const d = await r.json().catch(()=>({})); throw new Error(d.erro || "Não consegui gerar a amostra."); }
    const url = URL.createObjectURL(await r.blob());
    if (audioAmostra) audioAmostra.pause();
    audioAmostra = new Audio(url); audioAmostra.play();
  } catch(err){ avisar(err.message); }
}
async function carregarAjustes(){
  const alvo = document.getElementById("tela-ajustes");
  try { ajustes = await api("/api/ajustes"); } catch(err){ alvo.replaceChildren(h("p",{class:"vazio"}, err.message)); return; }
  const A = ajustes;

  // assistente
  const stA = h("span",{class:"status-aj"});
  const nomeA = h("input",{type:"text", value:A.assistente.nome, maxlength:"30"});
  const palavra = h("input",{type:"text", value:A.assistente.palavra_ativacao, maxlength:"30"});
  const seuNome = h("input",{type:"text", value:A.assistente.seu_nome, maxlength:"40"});
  let palavraIgual = A.assistente.palavra_ativacao === A.assistente.nome;
  nomeA.addEventListener("input", () => { if (palavraIgual) palavra.value = nomeA.value; });
  palavra.addEventListener("input", () => { palavraIgual = palavra.value === nomeA.value; });
  const secAssist = h("section",{class:"painel aj"}, h("h2",{},"Assistente"),
    h("p",{class:"ajuda"},"O nome aparece no menu e nas respostas. A palavra de ativação é o que ele atende na escuta contínua; use um nome curto e fácil de pronunciar."),
    h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Nome do assistente"), nomeA), h("div",{}, h("label",{class:"rot"},"Palavra de ativação"), palavra)),
    h("label",{class:"rot"},"Como ele chama você"), seuNome,
    h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
      if (await salvarAj("assistente",{nome:nomeA.value, palavra_ativacao:palavra.value, seu_nome:seuNome.value}, stA)){
        estado.cfg.assistente = ajustes.assistente.nome; estado.cfg.nome = ajustes.assistente.seu_nome; aplicarNomeAssistente(); } }},"Salvar"), stA));

  // voz
  const stV = h("span",{class:"status-aj"});
  let vozSel = A.voz.voz;
  const vel = h("input",{type:"range", min:"0.8", max:"1.4", step:"0.05", value:String(A.voz.velocidade)});
  const velRot = h("span",{style:"min-width:44px;text-align:right;font-variant-numeric:tabular-nums"}, `${Number(A.voz.velocidade).toFixed(2)}x`);
  vel.addEventListener("input", () => velRot.textContent = `${Number(vel.value).toFixed(2)}x`);
  const grade = h("div",{class:"vozes"});
  function desenharVozes(){
    grade.replaceChildren(...A.voz.vozes.map(v => h("div",{class:"voz-op"+(v.instalada?"":" indisponivel"), role:"button", tabindex:"0",
      "aria-pressed":String(v.id === vozSel), onclick:()=>{ if (!v.instalada){ avisar("Essa voz ainda não foi baixada. Use o instalador no "+nomeAssist()+"."); return; } vozSel = v.id; desenharVozes(); }},
      h("b",{}, v.nome), h("small",{}, `${v.genero[0].toUpperCase()+v.genero.slice(1)}, ${v.motor}, qualidade ${v.qualidade}`),
      v.instalada ? h("button",{class:"btn pequeno ouvir", onclick:ev=>{ ev.stopPropagation(); ouvirAmostra(v.id, vel.value); }},"Ouvir") : h("small",{},"Não instalada"))));
  }
  desenharVozes();
  const secVoz = h("section",{class:"painel aj"}, h("h2",{},"Voz"),
    h("p",{class:"ajuda"},"Todas as vozes rodam neste computador, sem consumo de tokens. Kokoro tem a voz feminina (Dora) e soa mais natural; Piper é mais leve."),
    grade, h("label",{class:"rot"},"Velocidade da fala"), h("div",{class:"velocidade"}, vel, velRot),
    h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
      if (await salvarAj("voz",{voz:vozSel, velocidade:+vel.value}, stV)) carregarNucleo().catch(()=>{}); }},"Salvar"),
      h("button",{class:"btn", onclick:()=>ouvirAmostra(vozSel, vel.value)},"Ouvir a voz escolhida"), stV));

  // briefing
  const stB = h("span",{class:"status-aj"});
  const blocos = A.briefing.blocos.map(b => ({...b}));
  const listaB = h("ul",{class:"blocos"});
  function desenharBlocos(){
    listaB.replaceChildren(...blocos.map((b,i) => h("li",{class:b.ativo?"":"off"},
      h("input",{type:"checkbox", checked:b.ativo, "aria-label":"Incluir "+b.nome, onchange:ev=>{ b.ativo = ev.target.checked; desenharBlocos(); }}),
      h("span",{}, b.nome),
      h("div",{class:"mover"}, h("button",{"aria-label":"Subir", disabled:i===0, onclick:()=>{ [blocos[i-1],blocos[i]]=[blocos[i],blocos[i-1]]; desenharBlocos(); }},"↑"),
        h("button",{"aria-label":"Descer", disabled:i===blocos.length-1, onclick:()=>{ [blocos[i+1],blocos[i]]=[blocos[i],blocos[i+1]]; desenharBlocos(); }},"↓")))));
  }
  desenharBlocos();
  let estilo = A.briefing.estilo;
  const segEstilo = h("div",{class:"segmento",role:"group"});
  const desenharEstilo = () => segEstilo.replaceChildren(...[["completo","Completo"],["curto","Curto"]].map(([k,r]) =>
    h("button",{"aria-pressed":String(estilo===k), onclick:()=>{ estilo = k; desenharEstilo(); }}, r)));
  desenharEstilo();
  const nNot = h("select",{}, [0,1,2,3,4,5,6].map(x => h("option",{value:x, selected:x===A.briefing.noticias}, x === 0 ? "Nenhuma" : String(x))));
  const nEm = h("select",{}, [1,2,3,4,5].map(x => h("option",{value:x, selected:x===A.briefing.max_emails}, String(x))));
  const temasSel = new Set(A.briefing.temas_noticias);
  const temas = h("div",{class:"temas"}, (A.briefing.temas_disponiveis.length ? A.briefing.temas_disponiveis : A.briefing.temas_noticias).map(t =>
    h("label",{}, h("input",{type:"checkbox", checked:temasSel.has(t), onchange:ev=>{ ev.target.checked ? temasSel.add(t) : temasSel.delete(t); }}), t)));
  const abertura = h("input",{type:"text", value:A.briefing.abertura, maxlength:"200", placeholder:"Ex.: Vamos com tudo hoje."});
  const fechamento = h("input",{type:"text", value:A.briefing.fechamento, maxlength:"200", placeholder:"Ex.: Lembre de beber água."});
  const horario = h("input",{type:"time", value:"07:30"});
  const dadosB = () => ({blocos, estilo, noticias:+nNot.value, max_emails:+nEm.value, abertura:abertura.value, fechamento:fechamento.value,
    temas_noticias:[...(A.briefing.temas_disponiveis.length ? A.briefing.temas_disponiveis : A.briefing.temas_noticias)].filter(t => temasSel.has(t))});
  const secBrief = h("section",{class:"painel aj"}, h("h2",{},"Briefing do dia"),
    h("p",{class:"ajuda"},"Escolha o que entra, a ordem (setas) e o tamanho. No estilo curto, cada assunto vira uma frase só."),
    listaB,
    h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Estilo"), segEstilo),
      h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Notícias"), nNot), h("div",{}, h("label",{class:"rot"},"E-mails citados"), nEm))),
    h("label",{class:"rot"},"Temas das notícias (na ordem das suas fontes)"), temas,
    h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Frase extra na abertura"), abertura), h("div",{}, h("label",{class:"rot"},"Frase extra no fechamento"), fechamento)),
    h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:()=>salvarAj("briefing", dadosB(), stB)},"Salvar"),
      h("button",{class:"btn", onclick:async()=>{ if (await salvarAj("briefing", dadosB(), stB)) iniciarBriefing(); }},"Salvar e ouvir agora"), stB),
    h("label",{class:"rot", style:"margin-top:16px"},"Abrir sozinho no briefing (dias úteis)"),
    h("div",{class:"acoes-aj", style:"margin-top:0"}, h("div",{style:"width:130px"}, horario), h("button",{class:"btn", onclick:async()=>{
      try { const r = await api("/api/ajustes/agendar",{method:"POST",body:JSON.stringify({horario:horario.value})}); avisar(r.mensagem); } catch(err){ avisar(err.message); } }},"Agendar")));

  // clima
  const stC = h("span",{class:"status-aj"});
  const locais = A.clima.locais.map(l => ({...l, mostrar:[...(l.mostrar || ["hoje"])]}));
  const listaC = h("div",{class:"cidades"});
  const opcoes = [["agora","Agora"],["hoje","Hoje"],["amanha","Amanhã"],["semana","Próximos dias"]];
  function desenharCidades(){
    listaC.replaceChildren(...(locais.length ? locais.map((l,i) => h("div",{class:"cidade"},
      h("div",{}, h("b",{}, l.cidade || "Local"), h("br"), h("small",{}, `${(+l.latitude).toFixed(2)}, ${(+l.longitude).toFixed(2)}`)),
      h("div",{class:"mover"}, h("button",{"aria-label":"Subir", disabled:i===0, onclick:()=>{ [locais[i-1],locais[i]]=[locais[i],locais[i-1]]; desenharCidades(); }},"↑"),
        h("button",{"aria-label":"Descer", disabled:i===locais.length-1, onclick:()=>{ [locais[i+1],locais[i]]=[locais[i],locais[i+1]]; desenharCidades(); }},"↓"),
        h("button",{"aria-label":"Remover", onclick:()=>{ locais.splice(i,1); desenharCidades(); }},"×")),
      h("div",{class:"mostrar"}, h("span",{style:"color:var(--suave)"},"No briefing:"), opcoes.map(([k,r]) => h("label",{},
        h("input",{type:"checkbox", checked:l.mostrar.includes(k), onchange:ev=>{ ev.target.checked ? l.mostrar.push(k) : l.mostrar.splice(l.mostrar.indexOf(k),1); }}), r)))))
      : [h("p",{class:"vazio"},"Nenhuma cidade. Busque abaixo.")]));
  }
  desenharCidades();
  const busca = h("input",{type:"text", placeholder:"Buscar cidade (ex.: São Paulo, Maragogi)"});
  const resultados = h("div",{class:"resultados"});
  async function buscarCidade(){
    if (busca.value.trim().length < 2) return;
    try { const r = await api(`/api/ajustes/cidades?q=${encodeURIComponent(busca.value.trim())}`);
      resultados.replaceChildren(...(r.cidades.length ? r.cidades.map(c => h("button",{onclick:()=>{
        if (locais.length >= 6){ avisar("Até 6 cidades."); return; }
        locais.push({cidade:c.cidade, latitude:c.latitude, longitude:c.longitude, mostrar:["hoje"]}); resultados.replaceChildren(); busca.value = ""; desenharCidades(); }},
        `${c.cidade}${c.estado ? ", " + c.estado : ""}${c.pais ? " (" + c.pais + ")" : ""}`)) : [h("small",{class:"vazio"},"Nada encontrado.")]));
    } catch(err){ avisar(err.message); }
  }
  busca.addEventListener("keydown", ev => { if (ev.key === "Enter") buscarCidade(); });
  const secClima = h("section",{class:"painel aj"}, h("h2",{},"Clima"),
    h("p",{class:"ajuda"},"Adicione até 6 cidades e escolha o que dizer de cada uma. Também dá para perguntar ao assistente: “vai chover amanhã em Recife?”. A busca envia só o nome da cidade ao Open-Meteo."),
    listaC, h("div",{class:"acoes-aj", style:"margin-top:4px"}, h("div",{style:"flex:1"}, busca), h("button",{class:"btn", onclick:buscarCidade},"Buscar")), resultados,
    h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:()=>salvarAj("clima",{locais}, stC)},"Salvar"), stC));

  const extras = await secoesExtrasAjustes();
  alvo.replaceChildren(h("div",{class:"topo"}, h("div",{}, h("h1",{},"Ajustes"), h("div",{class:"sub"},"As mudanças valem na hora e ficam salvas no config.json (com cópia de segurança)."))),
    h("div",{class:"aj-grade"}, h("div",{style:"display:grid;gap:18px"}, secAssist, extras[0], secVoz, secClima),
      h("div",{style:"display:grid;gap:18px;align-content:start"}, secBrief, extras[1], extras[2], extras[3], extras[4])));
}
