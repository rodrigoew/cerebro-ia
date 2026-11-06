"use strict";
/* ---------- AJUSTES: contas, nuvem e licença ---------- */
async function secoesExtrasAjustes(){
  const contasSec = h("section",{class:"painel aj"}, h("h2",{},"Contas de e-mail"), h("p",{class:"ajuda"},"Gmail, Microsoft (Outlook, Hotmail, 365), qualquer IMAP e POP, ao mesmo tempo. As senhas ficam no cofre do sistema."));
  const nuvemSec = h("section",{class:"painel aj"}, h("h2",{},"Nuvem (opcional)"));
  const licSec = h("section",{class:"painel aj"}, h("h2",{},"Licença"));
  async function desenharContas(){
    const d = await api("/api/contas");
    const lista = h("div",{class:"cidades"}, d.contas.length ? d.contas.map(c => {
      const senha = h("input",{type:"password", placeholder: c.tipo === "gmail" ? "Senha de app do Google" : "Senha", style:"border:1px solid var(--linha);border-radius:7px;padding:6px 9px;background:var(--painel)"});
      const st = h("small",{}, c.credencial ? "Credencial guardada." : (c.tipo === "microsoft" ? "Ainda não conectada." : "Sem senha guardada."));
      return h("div",{class:"cidade"},
        h("div",{}, h("b",{}, c.apelido), h("br"), h("small",{}, `${c.usuario}, ${{gmail:"Gmail",microsoft:"Microsoft",imap:"IMAP",pop:"POP"}[c.tipo]}${c.host && c.tipo !== "gmail" && c.tipo !== "microsoft" ? ", " + c.host : ""}`)),
        h("div",{class:"mover"}, h("button",{"aria-label":"Remover", onclick:async()=>{ if (confirm(`Remover a conta ${c.apelido}?`)){ await api(`/api/contas/${encodeURIComponent(c.apelido)}`,{method:"DELETE"}); desenharContas(); } }},"×")),
        h("div",{class:"mostrar"},
          c.tipo === "microsoft"
            ? h("button",{class:"btn pequeno", onclick:async()=>{
                try { const r = await api(`/api/contas/${encodeURIComponent(c.apelido)}/microsoft`,{method:"POST",body:"{}"});
                  st.textContent = `Abra ${r.url} e digite o código ${r.codigo}. Aguardando…`;
                  const t = setInterval(async () => { const e = await api(`/api/contas/${encodeURIComponent(c.apelido)}/microsoft`);
                    if (e.estado !== "aguardando"){ clearInterval(t); st.textContent = e.mensagem; desenharContas(); } }, 3000);
                } catch(err){ avisar(err.message); } }}, c.credencial ? "Reconectar" : "Conectar com a Microsoft")
            : [senha, h("button",{class:"btn pequeno", onclick:async()=>{ try { const r = await api(`/api/contas/${encodeURIComponent(c.apelido)}/senha`,{method:"POST",body:JSON.stringify({senha:senha.value})}); senha.value = ""; st.textContent = r.mensagem; } catch(err){ avisar(err.message); } }},"Guardar senha")],
          h("button",{class:"btn pequeno", onclick:async()=>{ st.textContent = "Testando…"; try { const r = await api(`/api/contas/${encodeURIComponent(c.apelido)}/testar`,{method:"POST",body:"{}"}); st.textContent = r.mensagem; } catch(err){ st.textContent = err.message; } }},"Testar"),
          st));
    }) : [h("p",{class:"vazio"},"Nenhuma conta.")]);
    const tipo = h("select",{}, [["gmail","Gmail / Google Workspace"],["microsoft","Microsoft (Outlook, Hotmail, 365)"],["imap","Outro provedor (IMAP)"],["pop","Outro provedor (POP)"]].map(([k,r]) => h("option",{value:k}, r)));
    const apelido = h("input",{type:"text", placeholder:"Apelido (ex.: Pessoal, Trabalho)"}), usuario = h("input",{type:"text", placeholder:"E-mail"});
    const host = h("input",{type:"text", placeholder:"Servidor (ex.: imap.provedor.com.br)"}), porta = h("input",{type:"text", placeholder:"Porta"});
    const servidor = h("div",{class:"linha2", style:"display:none"}, host, porta);
    tipo.onchange = () => { servidor.style.display = ["imap","pop"].includes(tipo.value) ? "grid" : "none"; porta.placeholder = tipo.value === "pop" ? "995" : "993"; };
    const msId = h("input",{type:"text", value:(ajustes && ajustes.microsoft && ajustes.microsoft.client_id) || "", placeholder:"ID do aplicativo (Entra ID / Azure)"});
    contasSec.replaceChildren(contasSec.children[0], contasSec.children[1], lista,
      h("label",{class:"rot"},"Adicionar conta"), h("div",{class:"linha2"}, tipo, apelido), usuario, servidor,
      h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
        try { await api("/api/contas",{method:"POST",body:JSON.stringify({tipo:tipo.value, apelido:apelido.value, usuario:usuario.value, host:host.value, porta:porta.value})});
          apelido.value = usuario.value = host.value = porta.value = ""; desenharContas(); avisar("Conta adicionada. Agora guarde a senha ou conecte."); } catch(err){ avisar(err.message); } }},"Adicionar")),
      h("details",{style:"margin-top:10px"}, h("summary",{style:"cursor:pointer;color:var(--suave);font-size:13px"},"Configuração para contas Microsoft"),
        h("p",{class:"ajuda", style:"margin-top:8px"},"A Microsoft exige login moderno. Registre um aplicativo gratuito em entra.microsoft.com (o LEIAME explica em 5 passos) e cole o ID aqui. Quem vende o app registra uma vez e todos os compradores usam."),
        h("div",{class:"acoes-aj", style:"margin-top:0"}, h("div",{style:"flex:1"}, msId), h("button",{class:"btn", onclick:async()=>{ try { await api("/api/ajustes",{method:"PUT",body:JSON.stringify({secao:"microsoft", dados:{client_id:msId.value}})}); avisar("Salvo."); } catch(err){ avisar(err.message); } }},"Salvar"))));
  }
  async function desenharNuvem(){
    const n = await api("/api/nuvem");
    let prov = n.provedor_aprofundar || n.provedor;
    const seg = h("div",{class:"segmento",role:"group"});
    const desenharSeg = () => seg.replaceChildren(...[["claude","Claude"],["openai","Compatível com OpenAI"]].map(([k,r]) => h("button",{"aria-pressed":String(prov===k), onclick:()=>{ prov = k; desenharSeg(); campos(); }}, r)));
    const area = h("div");
    const modeloC = h("input",{type:"text", value:n.modelo_claude}), chaveC = h("input",{type:"password", placeholder:n.chave_claude ? "Chave guardada (cole outra para trocar)" : "sk-ant-..."});
    const url = h("input",{type:"text", value:n.url_openai}), modeloO = h("input",{type:"text", value:n.modelo_openai}), rotulo = h("input",{type:"text", value:n.rotulo_openai, placeholder:"Nome exibido (ex.: GPT, OpenRouter)"});
    const chaveO = h("input",{type:"password", placeholder:n.chave_openai ? "Chave guardada (cole outra para trocar)" : "Chave da API"});
    const politica = h("select",{}, h("option",{value:"sempre_perguntar", selected:n.politica==="sempre_perguntar"},"Permitir envios (conforme o roteamento abaixo)"), h("option",{value:"nunca", selected:n.politica==="nunca"},"Nunca enviar (100% local)"));
    const roteamento = h("select",{},
      h("option",{value:"perguntar", selected:n.roteamento==="perguntar"},"Manual: só quando eu clicar em Aprofundar"),
      h("option",{value:"geral", selected:n.roteamento==="geral"},"Automático para perguntas gerais (sem nenhum dado meu)"),
      h("option",{value:"total", selected:n.roteamento==="total"},"Automático total (meus dados vão mascarados)"));
    function campos(){ area.replaceChildren(...(prov === "claude"
      ? [h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Modelo"), modeloC), h("div",{}, h("label",{class:"rot"},"Chave da API"), chaveC))]
      : [h("label",{class:"rot"},"Endereço (base da API)"), url, h("div",{class:"linha2"}, h("div",{}, h("label",{class:"rot"},"Modelo"), modeloO), h("div",{}, h("label",{class:"rot"},"Nome exibido"), rotulo)),
         h("label",{class:"rot"},"Chave da API"), chaveO,
         h("p",{class:"ajuda", style:"margin-top:8px"},"Serve para OpenAI (GPT), OpenRouter, LM Studio ou um roteador local. Roteadores de planos gratuitos, como o FreeLLMAPI, são para uso pessoal e enviam seus pedidos a vários provedores.")])); }
    desenharSeg(); campos();
    const est = (estado.cfg && estado.cfg.freellmapi) || {};
    const fla = h("div",{class:"cidade", style:"margin:10px 0"},
      h("div",{}, h("b",{},"FreeLLMAPI local (uso pessoal)"), h("br"),
        h("small",{}, est.rodando ? `Rodando em ${est.url}. Painel: ${est.painel}` : est.instalado ? "Instalado, parado." : "Não instalado. Rode scripts\\instalar_freellmapi.bat.")),
      h("div",{}),
      h("div",{class:"mostrar"},
        h("button",{class:"btn pequeno", onclick:async()=>{ try { const r = await api("/api/nuvem/freellmapi",{method:"POST",body:"{}"}); avisar(r.mensagem); await carregarEstado(); desenharNuvem(); } catch(err){ avisar(err.message); } }},"Usar FreeLLMAPI"),
        h("button",{class:"btn pequeno", onclick:async()=>{ try { const r = await api("/api/nuvem/testar",{method:"POST",body:"{}"}); avisar(r.mensagem); } catch(err){ avisar(err.message); } }},"Testar conexão")));
    const provAuto = h("select",{},
      h("option",{value:"openai", selected:n.provedor_auto==="openai"},"FreeLLMAPI / compatível com OpenAI (grátis)"),
      h("option",{value:"claude", selected:n.provedor_auto==="claude"},"Claude (usa o crédito da API)"));
    nuvemSec.replaceChildren(h("h2",{},"Nuvem (opcional)"),
      h("p",{class:"ajuda"},"Dois papéis: as respostas automáticas (perguntas gerais, sem dados seus) e o Aprofundar (quando você clica, com prévia e dados mascarados). Plano Claude Max: resgate o crédito mensal da API em claude.ai > Configurações > Cobrança > Créditos de API e cole a chave aqui."),
      h("label",{class:"rot"},"Aprofundar (com prévia) usa"), seg, area, fla,
      h("label",{class:"rot"},"Respostas automáticas usam"), provAuto,
      h("label",{class:"rot"},"Política de envio"), politica,
      h("label",{class:"rot"},"Roteamento"), roteamento,
      h("p",{class:"ajuda", style:"margin-top:6px"},"No automático, a IA local responde tudo que envolve seus e-mails, finanças e notas; perguntas gerais vão ao provedor escolhido. Se ele falhar, a IA local assume sozinha."),
      h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
        try { await api("/api/nuvem",{method:"POST",body:JSON.stringify({provedor:prov, modelo_claude:modeloC.value, url_openai:url.value, modelo_openai:modeloO.value, rotulo:rotulo.value, politica:politica.value, roteamento:roteamento.value, provedor_auto:provAuto.value})});
          if (prov === "claude" && chaveC.value) await api("/api/nuvem/chave",{method:"POST",body:JSON.stringify({provedor:"claude", chave:chaveC.value})});
          if (prov === "openai" && chaveO.value) await api("/api/nuvem/chave",{method:"POST",body:JSON.stringify({provedor:"openai", chave:chaveO.value})});
          avisar("Nuvem salva."); desenharNuvem(); } catch(err){ avisar(err.message); } }},"Salvar")));
  }
  async function desenharLicenca(){
    const l = await api("/api/licenca");
    const texto = h("textarea",{placeholder:"Cole aqui o conteúdo do arquivo de licença", style:"width:100%;min-height:80px;border:1px solid var(--linha);border-radius:7px;padding:8px 10px;background:var(--fundo)"});
    licSec.replaceChildren(h("h2",{},"Licença"), h("p",{class:"ajuda"}, l.mensagem),
      h("div",{}, l.modo === "pessoal" ? null : [texto, h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
        try { const r = await api("/api/licenca",{method:"POST",body:JSON.stringify({conteudo:texto.value})}); avisar(r.mensagem); desenharLicenca(); carregarEstado(); } catch(err){ avisar(err.message); } }},"Instalar licença"))]));
  }
  await Promise.all([desenharContas(), desenharNuvem(), desenharLicenca()]).catch(err => avisar(err.message));
  let aparelhosSec = h("section",{class:"painel aj"}), vigiaSec = h("section",{class:"painel aj"});
  try { aparelhosSec = await secAparelhos(); } catch(e){}
  try { vigiaSec = await secVigia(); } catch(e){}
  let redeSec = h("section",{class:"painel aj"}), atuSec = h("section",{class:"painel aj"}), permSec = h("section",{class:"painel aj"});
  try { redeSec = await secRede(); } catch(e){}
  try { atuSec = await secAtualizacoes(); } catch(e){}
  try { permSec = await secPermissoes(); } catch(e){}
  return [contasSec, nuvemSec, aparelhosSec, vigiaSec, licSec, redeSec, atuSec, permSec];
}

/* ---------- Ajustes: aparelhos (sincronização), vigia e segurança ---------- */
async function secRede(){
  const e = estado.cfg || {};
  const liga = h("input",{type:"checkbox", checked:!!e.acesso_lan});
  return h("section",{class:"painel aj"}, h("h2",{},"Acesso na rede (celular, tablet e notebook)"),
    h("p",{class:"ajuda"}, e.acesso_lan ? `Ligado. Endereço deste aparelho: http://${e.ip_local}:${e.porta || 8765}` : "Desligado: o Núcleo só responde neste computador. Ligue no aparelho central para os outros se conectarem."),
    h("label",{style:"display:flex;gap:8px;align-items:center"}, liga, "Permitir acesso dos meus aparelhos na mesma rede"),
    h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
      try { const r = await api("/api/rede",{method:"POST",body:JSON.stringify({ativo:liga.checked})}); avisar(r.mensagem); } catch(err){ avisar(err.message); } }},"Salvar")));
}
async function secAtualizacoes(){
  const sec = h("section",{class:"painel aj"}, h("h2",{},"Atualizações"));
  async function desenhar(verificar){
    let d; try { d = await api("/api/atualizacao" + (verificar ? "?verificar=1" : "")); } catch(err){ sec.append(h("p",{class:"vazio"}, err.message)); return; }
    sec.replaceChildren(h("h2",{},"Atualizações"),
      h("p",{class:"ajuda"}, `Versão instalada: ${d.versao_local}. ` + (d.disponivel ? `Nova versão disponível: ${d.versao_remota}.` : (d.motivo || "Você está na versão mais recente."))),
      h("div",{class:"acoes-aj"},
        d.disponivel ? h("button",{class:"btn primario", onclick:async ev=>{ ev.target.disabled = true; ev.target.textContent = "Atualizando…";
          try { const r = await api("/api/atualizacao/aplicar",{method:"POST",body:"{}"}); avisar(r.mensagem);
            if (r.atualizou){ ev.target.textContent = "Reiniciando…"; setTimeout(() => location.reload(), 9000); } else { ev.target.disabled = false; ev.target.textContent = "Atualizar e reiniciar"; } }
          catch(err){ avisar(err.message); ev.target.disabled = false; } }},"Atualizar e reiniciar") : null,
        h("button",{class:"btn", onclick:()=>desenhar(true)},"Verificar agora")),
      h("p",{class:"ajuda"},"O atalho Núcleo (Nucleo.exe) também verifica e atualiza sozinho a cada abertura."));
  }
  await desenhar(false);
  return sec;
}
async function secAparelhos(){
  const s = h("section",{class:"painel aj"}, h("h2",{},"Seus aparelhos (sincronização)"));
  async function desenhar(){
    let d; try { d = await api("/api/sinc"); } catch(err){ s.append(h("p",{class:"vazio"}, err.message)); return; }
    let papel = d.papel || "central";
    const segP = h("div",{class:"segmento",role:"group"});
    const servidor = h("input",{type:"text", value:d.servidor || "", placeholder:"http://192.168.0.10:8765"});
    const frase = h("input",{type:"password", placeholder: d.tem_frase ? "Frase guardada (digite outra para trocar)" : "Frase secreta (igual em todos os aparelhos)"});
    const auto = h("input",{type:"checkbox", checked:d.automatico !== false});
    const usarCentral = h("input",{type:"checkbox", checked:d.usar_central !== false});
    const extra = h("div");
    const desenharExtra = () => extra.replaceChildren(...(papel === "central"
      ? [h("p",{class:"ajuda"}, `Este é o aparelho central. Nos outros, escolha “Secundário” e aponte para: http://${d.este_ip}:${(estado.cfg && estado.cfg.porta) || 8765}`),
         h("p",{class:"ajuda"}, "Tablet e iPhone não precisam de app: abrem esse mesmo endereço no navegador (veja Acesso pelo celular).")]
      : [h("label",{class:"rot"},"Endereço do aparelho central"), servidor,
         h("label",{style:"display:flex;gap:8px;align-items:center;margin-top:8px"}, usarCentral, "Usar a IA do central quando estiver na mesma rede (respostas melhores; fora de casa, volta para a deste aparelho)"),
         d.ia_central ? h("p",{class:"ajuda", style:"color:var(--salvia)"},"Agora usando a IA do central.") : null,
         h("label",{class:"rot"},"Sincronizar sozinho de tempos em tempos"), h("label",{style:"display:flex;gap:8px;align-items:center"}, auto, "Automático")]));
    const desenharSeg = () => segP.replaceChildren(...[["central","Central (fica mais ligado)"],["cliente","Secundário"]].map(([k,r]) =>
      h("button",{"aria-pressed":String(papel===k), onclick:()=>{ papel = k; desenharSeg(); desenharExtra(); }}, r)));
    desenharSeg(); desenharExtra();
    const st = h("span",{class:"status-aj"});
    if (d.ultimo && d.ultimo.quando) st.textContent = `Última: ${d.ultimo.recebidos} recebido(s), ${d.ultimo.enviados} enviado(s).`;
    s.replaceChildren(h("h2",{},"Seus aparelhos (sincronização)"),
      h("p",{class:"ajuda"},"Uma memória só, em todos os aparelhos. A troca é criptografada com a sua frase secreta e acontece pela sua rede; nada vai para a internet."),
      h("label",{class:"rot"},"Ligar sincronização"), h("label",{style:"display:flex;gap:8px;align-items:center;margin-bottom:8px"},
        h("input",{type:"checkbox", id:"sinc-on", checked:!!d.ativo}), "Sincronizar este aparelho"),
      h("label",{class:"rot"},"Papel"), segP, extra,
      h("label",{class:"rot"},"Frase secreta (a mesma em todos)"), frase,
      h("div",{class:"acoes-aj"},
        h("button",{class:"btn primario", onclick:async()=>{
          try { await api("/api/sinc/config",{method:"POST",body:JSON.stringify({ativo:document.getElementById("sinc-on").checked,
            papel, servidor:servidor.value, automatico:auto.checked, usar_central:usarCentral.checked, frase:frase.value || undefined})}); avisar("Sincronização salva."); desenhar(); }
          catch(err){ avisar(err.message); } }},"Salvar"),
        papel === "cliente" ? h("button",{class:"btn", onclick:async()=>{ try { const r = await api("/api/sinc/agora",{method:"POST",body:"{}"}); avisar(r.ok ? `Sincronizado: ${r.recebidos} recebido(s), ${r.enviados} enviado(s).` : r.mensagem); desenhar(); } catch(err){ avisar(err.message); } }},"Sincronizar agora") : null, st));
  }
  await desenhar();
  return s;
}
async function secVigia(){
  const s = h("section",{class:"painel aj"}, h("h2",{},"Widget sempre ativo (vigia)"));
  let d; try { d = await api("/api/vigia"); } catch(err){ /* vem no /api/estado também */ }
  const info = (estado.cfg && estado.cfg.vigia) || {};
  const liga = h("input",{type:"checkbox", checked:!!info.ligado});
  s.replaceChildren(h("h2",{},"Widget sempre ativo (vigia)"),
    h("p",{class:"ajuda"},"Em segundo plano, observa só o título da janela ativa (nunca o conteúdo) e avisa diante de risco: uma compra por impulso, uma transferência bancária, um comando perigoso no terminal, uma configuração sensível. Tudo no seu computador."),
    info.disponivel === false ? h("p",{class:"ajuda", style:"color:var(--vinho)"}, info.motivo || "Indisponível neste sistema.") : null,
    h("label",{style:"display:flex;gap:8px;align-items:center"}, liga, "Manter o vigia ativo"),
    h("div",{class:"acoes-aj"}, h("button",{class:"btn primario", onclick:async()=>{
      try { const r = await api("/api/vigia",{method:"POST",body:JSON.stringify({ativo:liga.checked})}); avisar(r.mensagem); } catch(err){ avisar(err.message); } }},"Aplicar")));
  return s;
}

async function secPermissoes(){
  const sec = h("section",{class:"painel aj"}, h("h2",{},"Permissões das ações"));
  async function desenhar(){
    let d; try { d = (await api("/api/acoes/permissoes")).permissoes; } catch(err){ sec.append(h("p",{class:"vazio"}, err.message)); return; }
    const rotulo = {abrir_programa:"Abrir programas", abrir_arquivo:"Abrir arquivos", abrir_pasta:"Abrir pastas",
      abrir_site:"Abrir sites", info_sistema:"Ver informações do computador", verificar_atualizacoes:"Verificar atualizações",
      aplicar_atualizacoes:"Instalar atualizações", abrir_windows_update:"Abrir o Windows Update",
      organizar_downloads:"Organizar a pasta Downloads", rascunho_email:"Salvar rascunho de e-mail",
      bloquear_tela:"Bloquear a tela", desligar:"Desligar ou reiniciar", cancelar_desligamento:"Cancelar desligamento"};
    const linha = a => h("div",{class:"perm"},
      h("div",{}, h("b",{}, rotulo[a.nome] || a.descricao), a.risco === "alto" ? h("span",{class:"tag atrasada", style:"margin-left:6px"},"delicada") : null,
        h("br"), h("small",{}, a.descricao + (a.vezes ? ` · usada ${a.vezes}×` : ""))),
      a.risco === "alto"
        ? h("small",{style:"color:var(--suave)"},"sempre pergunta")
        : h("select",{value:a.decisao, onchange:async ev=>{ try { await api(`/api/acoes/permissoes/${encodeURIComponent(a.nome)}`,{method:"PUT",body:JSON.stringify({decisao:ev.target.value})}); avisar("Salvo."); } catch(err){ avisar(err.message); } }},
            h("option",{value:"perguntar", selected:a.decisao==="perguntar"},"Perguntar"),
            h("option",{value:"sempre", selected:a.decisao==="sempre"},"Sempre deixar"),
            h("option",{value:"nunca", selected:a.decisao==="nunca"},"Nunca deixar")));
    sec.replaceChildren(h("h2",{},"Permissões das ações"),
      h("p",{class:"ajuda"},"Quando você pede uma ação pela primeira vez, o Núcleo pergunta. Se escolher “não perguntar mais”, ela passa a valer aqui. Ações delicadas (instalar atualizações, desligar) sempre pedem confirmação."),
      h("h3",{class:"g-sub", style:"margin:10px 0 4px"},"Do assistente"), ...d.filter(a => a.nome.startsWith("nucleo:")).map(linha),
      h("h3",{class:"g-sub", style:"margin:14px 0 4px"},"No computador"), ...d.filter(a => !a.nome.startsWith("nucleo:")).map(linha));
  }
  await desenhar();
  return sec;
}
