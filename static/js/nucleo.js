"use strict";
/* ---------- NÚCLEO ---------- */
const nucleo = {estado:"espera", nivel:0, locais:0, info:null, gravando:null, mapa:null, iniciado:false};
const ESTADOS = {
  espera:["Em espera","Tudo é analisado neste computador."],
  ouvindo:["Ouvindo","O áudio é transcrito aqui mesmo, sem sair da máquina."],
  transcrevendo:["Transcrevendo","Convertendo sua fala em texto localmente."],
  analisando:["Analisando localmente","Cruzando notas, e-mails, agenda e financeiro."],
  confirmar:["Aguardando você","Nada sai deste computador sem o seu clique."],
  claude:["Consultando o Claude","Enviando só o pacote que você aprovou."],
  falando:["Falando","Voz gerada neste computador."],
  conversa:["Pode falar","Modo conversa ligado. Fale quando quiser."],
  sentinela:["Em escuta","Diga “Núcleo” ou “bom dia”. Tudo é processado neste computador."],
};
function estadoNucleo(e){
  nucleo.estado = e;
  document.getElementById("n-estado").textContent = ESTADOS[e][0];
  document.getElementById("n-sub").textContent = ESTADOS[e][1];
}

/* núcleo animado */
/* paletas de estado: âmbar (normal), laranja (atenção), vermelho (risco), sálvia (sucesso/confiança),
   ameixa (consultando a nuvem) e champanhe (aprendendo). Nenhum azul. */
const PALETAS = {
  normal:     {anel:[217,168,69],  brilho:[255,207,110], miolo:["#FFF1C9","#FFCF6E","#B07E22"], rotulo:"Tudo em ordem"},
  atencao:    {anel:[232,137,58],  brilho:[255,178,102], miolo:["#FFE8CF","#FFAA5E","#B5561C"], rotulo:"Atenção"},
  risco:      {anel:[224,72,62],   brilho:[255,122,104], miolo:["#FFDCD5","#FF6B5B","#8E1F1A"], rotulo:"Risco"},
  sucesso:    {anel:[143,196,154], brilho:[196,238,202], miolo:["#F0FFF2","#9EE0AA","#2F6B3F"], rotulo:"Confirmado"},
  nuvem:      {anel:[192,139,208], brilho:[228,186,242], miolo:["#F8ECFF","#D6A5EA","#5E2F73"], rotulo:"Consultando a nuvem"},
  aprendendo: {anel:[236,214,150], brilho:[255,240,196], miolo:["#FFFBEF","#F3DE9C","#8C7330"], rotulo:"Aprendendo"},
};
const humor = {atual:"normal", base:"normal", cor:[217,168,69], brilho:[255,207,110], ondas:[], timer:null};
function misturar(a, b, k){ return a.map((v,i) => v + (b[i]-v)*k); }
function rgba(c, a){ return `rgba(${c.map(v=>Math.round(v)).join(",")},${a})`; }
function hex2rgb(h){ return [1,3,5].map(i => parseInt(h.slice(i,i+2),16)); }
function definirHumor(nome, duracaoMs){
  if (!PALETAS[nome]) nome = "normal";
  humor.atual = nome;
  clearTimeout(humor.timer);
  if (duracaoMs) humor.timer = setTimeout(() => definirHumor(humor.base), duracaoMs);
  const p = PALETAS[nome], raiz = document.documentElement.style;
  raiz.setProperty("--n-latao", `rgb(${p.anel.join(",")})`);
  raiz.setProperty("--n-brilho", `rgb(${p.brilho.join(",")})`);
  raiz.setProperty("--n-linha", `rgba(${p.anel.join(",")},.20)`);
  document.querySelectorAll("[data-humor-alvo]").forEach(el => el.dataset.humor = nome);
  const selo = document.getElementById("n-humor");
  if (selo){ selo.dataset.humor = nome; selo.querySelector("span").textContent = p.rotulo; }
}
function emitirOnda(nome){ humor.ondas.push({r:100, a:.9, cor:(PALETAS[nome] || PALETAS.normal).brilho.slice()}); }

function animarNucleo(cv){
  const ctx = cv.getContext("2d");
  const reduzir = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const particulas = [...Array(46)].map(()=>({a:Math.random()*Math.PI*2, r:150+Math.random()*95, v:(Math.random()*.6+.2)*(Math.random()<.5?-1:1), s:Math.random()*1.8+.6}));
  let t = 0, energia = 0, cor = [217,168,69], brilho = [255,207,110], miolo = PALETAS.normal.miolo.map(hex2rgb);
  function quadro(){
    const W = cv.width, H = cv.height, cx = W/2, cy = H/2;
    const p = PALETAS[humor.atual] || PALETAS.normal;
    cor = misturar(cor, p.anel, .06); brilho = misturar(brilho, p.brilho, .06);
    miolo = miolo.map((c,i) => misturar(c, hex2rgb(p.miolo[i]), .06));
    const risco = humor.atual === "risco";
    const alvo = ({espera:.15, ouvindo:.35 + nucleo.nivel*3, conversa:.28 + nucleo.nivel*3, sentinela:.2, falando:.45 + nucleo.nivel*3,
      transcrevendo:.6, analisando:.8, confirmar:.3, claude:1}[nucleo.estado] || .15) + (risco ? .25 : 0);
    energia += (Math.min(alvo,1.4) - energia) * .08;
    t += reduzir ? 0 : (.006 + energia*.03);
    ctx.clearRect(0,0,W,H);
    const pulsoRisco = risco ? (Math.sin(t*9)*.5+.5) : 0;
    // halo
    const g = ctx.createRadialGradient(cx,cy,10,cx,cy,250);
    g.addColorStop(0, rgba(brilho, .30+energia*.25+pulsoRisco*.15)); g.addColorStop(.35, rgba(cor, .12+energia*.12+pulsoRisco*.1)); g.addColorStop(1,"rgba(0,0,0,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx,cy,250,0,Math.PI*2); ctx.fill();
    // ondas de resposta (cada resposta "emite" um anel)
    humor.ondas = humor.ondas.filter(o => o.a > .02);
    humor.ondas.forEach(o => { o.r += reduzir ? 40 : 3.2; o.a *= .965;
      ctx.strokeStyle = rgba(o.cor, o.a); ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(cx,cy,o.r,0,Math.PI*2); ctx.stroke(); });
    // anéis segmentados
    const aneis = [[205,.9,24,1.2],[178,-1.4,60,2.5],[150,.6,8,1.4],[232,-.35,90,.8]];
    aneis.forEach(([r,vel,seg,lw],i) => {
      ctx.save(); ctx.translate(cx,cy); ctx.rotate(t*vel*(1+energia));
      ctx.strokeStyle = i===3 ? rgba(cor,.35) : rgba(i===1 ? brilho : cor, .55+energia*.3);
      ctx.lineWidth = lw*2;
      const passo = Math.PI*2/seg;
      for (let k=0;k<seg;k++){ if ((k+i)%3===0 && i!==2) continue; ctx.beginPath(); ctx.arc(0,0,r,k*passo,k*passo+passo*(i===2?.5:.72)); ctx.stroke(); }
      ctx.restore();
    });
    if (risco){ ctx.strokeStyle = rgba(brilho, .25+pulsoRisco*.5); ctx.lineWidth = 4; ctx.setLineDash([18,14]);
      ctx.beginPath(); ctx.arc(cx,cy,240,0,Math.PI*2); ctx.stroke(); ctx.setLineDash([]); }
    // marcas de escala
    ctx.save(); ctx.translate(cx,cy); ctx.rotate(-t*.2);
    for (let k=0;k<72;k++){ const a = k/72*Math.PI*2, l = k%6===0 ? 14 : 6;
      ctx.strokeStyle = `rgba(241,231,210,${k%6===0?.5:.2})`; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(Math.cos(a)*246,Math.sin(a)*246); ctx.lineTo(Math.cos(a)*(246-l),Math.sin(a)*(246-l)); ctx.stroke(); }
    ctx.restore();
    // partículas em órbita
    particulas.forEach(q => { q.a += q.v*.004*(1+energia*4); const r = q.r + Math.sin(t*3+q.a*2)*6*energia;
      ctx.fillStyle = rgba(brilho, .35+energia*.4); ctx.beginPath(); ctx.arc(cx+Math.cos(q.a)*r, cy+Math.sin(q.a)*r, q.s*2, 0, Math.PI*2); ctx.fill(); });
    // esfera central que respira
    const base = 92 + Math.sin(t*4)*4*(.4+energia) + nucleo.nivel*60 + pulsoRisco*6;
    ctx.save(); ctx.translate(cx,cy); ctx.beginPath();
    for (let k=0;k<=96;k++){ const a = k/96*Math.PI*2; const onda = Math.sin(a*5+t*6)*3*energia + Math.sin(a*3-t*4)*4*energia;
      const r = base + onda; k ? ctx.lineTo(Math.cos(a)*r,Math.sin(a)*r) : ctx.moveTo(Math.cos(a)*r,Math.sin(a)*r); }
    const gi = ctx.createRadialGradient(-20,-24,6,0,0,base+10);
    gi.addColorStop(0, rgba(miolo[0],1)); gi.addColorStop(.35, rgba(miolo[1],1)); gi.addColorStop(.75, rgba(miolo[2],1)); gi.addColorStop(1,"rgba(30,20,10,.9)");
    ctx.fillStyle = gi; ctx.shadowColor = rgba(cor,.9); ctx.shadowBlur = 50 + energia*40; ctx.fill(); ctx.restore();
    ctx.strokeStyle = "rgba(255,245,225,.45)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx,cy,base*.62,-1.9+t,-.6+t); ctx.stroke();
    if (!reduzir || nucleo.estado !== "espera" || humor.ondas.length) requestAnimationFrame(quadro);
    else setTimeout(()=>requestAnimationFrame(quadro), 500);
  }
  const quadroOriginal = quadro;
  quadro = function(){ if (!cv.offsetParent && getComputedStyle(cv).position !== "fixed"){ setTimeout(()=>requestAnimationFrame(quadro), 400); return; } quadroOriginal(); };
  requestAnimationFrame(quadro);
}
animarNucleo(document.getElementById("n-canvas"));
animarNucleo(document.getElementById("b-canvas"));

/* mapa da memória (grafo com física simples) */
function desenharMapa(dados){
  const cv = document.getElementById("n-mapa"), ctx = cv.getContext("2d");
  const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
  cv.width = W*dpr; cv.height = H*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
  const nos = dados.nos.slice(0,22).map((n,i)=>({...n, x:W/2+Math.cos(i*2.4)*W*.3, y:H/2+Math.sin(i*2.4)*H*.32, vx:0, vy:0}));
  const idx = Object.fromEntries(nos.map(n=>[n.id,n]));
  const arestas = dados.arestas.filter(a=>idx[a.a]&&idx[a.b]);
  nucleo.mapa = {nos};
  if (!nos.length){ ctx.fillStyle = "#A89A80"; ctx.font = "13px sans-serif"; ctx.fillText("Anote algo para o mapa ganhar vida.", 10, 24); return; }
  for (let passo=0; passo<260; passo++){
    nos.forEach(a => nos.forEach(b => { if (a===b) return; const dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+.01, f=900/d2; a.vx+=dx*f*.02; a.vy+=dy*f*.02; }));
    arestas.forEach(e => { const a=idx[e.a], b=idx[e.b], dx=b.x-a.x, dy=b.y-a.y, d=Math.hypot(dx,dy)||1, f=(d-70)*.012; a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f; });
    nos.forEach(n => { n.vx+=(W/2-n.x)*.004; n.vy+=(H/2-n.y)*.006; n.x+=n.vx; n.y+=n.vy; n.vx*=.6; n.vy*=.6;
      n.x=Math.max(30,Math.min(W-30,n.x)); n.y=Math.max(16,Math.min(H-16,n.y)); });
  }
  ctx.clearRect(0,0,W,H);
  arestas.forEach(e => { const a=idx[e.a], b=idx[e.b]; ctx.strokeStyle=`rgba(217,168,69,${Math.min(.15+e.peso*.08,.6)})`; ctx.lineWidth=1+Math.min(e.peso,4)*.4;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); });
  nos.forEach(n => {
    const proj = n.tipo === "projeto", r = proj ? 7+Math.min(n.peso,8) : 3+Math.min(n.peso,6)*.6;
    ctx.beginPath(); ctx.arc(n.x,n.y,r,0,Math.PI*2);
    ctx.fillStyle = proj ? "#D9A845" : "#F1E7D2"; ctx.shadowColor = proj ? "rgba(255,207,110,.8)" : "transparent"; ctx.shadowBlur = proj ? 14 : 0; ctx.fill(); ctx.shadowBlur = 0;
    ctx.fillStyle = proj ? "#FFE3A3" : "#BFB194"; ctx.font = `${proj?600:400} ${proj?12:11}px "Segoe UI",sans-serif`;
    const rot = n.id.length > 18 ? n.id.slice(0,17)+"…" : n.id;
    const esquerda = n.x > W*.62; ctx.textAlign = esquerda ? "right" : "left";
    ctx.fillText(rot, esquerda ? n.x - r - 4 : n.x + r + 4, n.y + 4); ctx.textAlign = "left";
    n.r = r;
  });
}
document.getElementById("n-mapa").addEventListener("click", ev => {
  if (!nucleo.mapa) return;
  const r = ev.currentTarget.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
  const no = nucleo.mapa.nos.find(n => Math.hypot(n.x-x, n.y-y) < Math.max(n.r+6, 12));
  if (no) pedir(no.tipo === "projeto" ? `o que tenho sobre ${no.id}` : `o que falei com ${no.id}`);
});

async function carregarNucleo(){
  if (!nucleo.iniciado){
    nucleo.iniciado = true;
    const nome = estado.cfg && estado.cfg.nome ? estado.cfg.nome : "";
    document.getElementById("n-feed").append(h("p",{class:"g-vazio"}, "As conversas desta sessão aparecem aqui."));
    const sugestoes = ["minhas pendências","o que tenho hoje?","quanto falta pagar este mês?","prepara minha próxima reunião",
      "alguma novidade de segurança importante?","verifica se tem atualizações","como está o computador?","organiza: …","preciso decidir entre…","ideia: …","me lembra de… amanhã às 9h","bom dia (briefing narrado)"];
    document.getElementById("n-chips").replaceChildren(...sugestoes.map(s => h("button",{onclick:()=>{
      if (s.includes("…")){ const i = document.getElementById("n-input"); i.value = s.replace("…",""); i.focus(); }
      else if (s.startsWith("bom dia")) iniciarBriefing();
      else pedir(s);
    }}, s)));
  }
  carregarFoco();
  try {
    const info = await api("/api/cerebro/estado");
    nucleo.info = info;
    document.getElementById("b-lembretes").textContent = info.lembretes.length || "";
    document.getElementById("b-novidades").textContent = info.artigos.length || "";
    document.getElementById("n-envios-mes").textContent = info.envios_mes;
    document.getElementById("n-aprendizados").textContent = info.aprendizados;
    const ia = info.ia, caixaIA = document.getElementById("n-ia");
    caixaIA.classList.toggle("on", !!ia.chat_ok);
    const vs = info.voz_status || {};
    const falta = !ia.chat_ok || !ia.emb_ok || !vs.ouvir || !vs.falar;
    caixaIA.replaceChildren(h("i"), h("span",{},
      ia.chat_ok ? [h("b",{}, `IA local ativa: ${ia.modelo}`), ia.emb_ok ? "" : ". Busca por significado indisponível.",
                    info.vetores_pendentes ? ` Indexando ${info.vetores_pendentes} item(ns)…` : ""]
                 : [h("b",{},"IA local indisponível. "), ia.motivo || "", " O Núcleo segue funcionando com regras e busca."],
      h("br"), `Voz: ${vs.ouvir_desc || "reconhecimento não instalado"}; ${vs.falar || "fala pelo Windows"}.`,
      falta ? [h("br"), h("button",{class:"n-mini", onclick:abrirInstalador}, "Instalar o que falta")] : null,
      vs.ouvir ? [h("br"), h("button",{class:"n-mini"+(escutaContinuaLigada() ? " feito" : ""), onclick:alternarEscutaContinua},
        escutaContinuaLigada() ? "Escuta contínua ligada" : `Ligar escuta contínua (“${(ajustes && ajustes.assistente.palavra_ativacao) || nomeAssist()}” ou “bom dia”)`)] : null,
      (() => { const at = info.atualizacoes || {}; if (!at.quando) return null;
        const n = (at.programas || []).length + (at.windows || []).length;
        return [h("br"), n ? `Atualizações: ${n} disponível(is), verificado ${at.quando.slice(8,10)}/${at.quando.slice(5,7)} às ${at.quando.slice(11,16)}. `
                           : `Tudo atualizado (${at.quando.slice(8,10)}/${at.quando.slice(5,7)}). `,
                n ? h("button",{class:"n-mini", onclick:()=>pedir("verifica se tem atualizações")}, "Ver e instalar") : null]; })()));
    document.getElementById("n-conversa").disabled = !vs.ouvir;
    document.getElementById("b-status").classList.toggle("off", falta);
    const fontesOk = info.fontes_ultima ? `atualizadas ${info.fontes_ultima.slice(8,10)}/${info.fontes_ultima.slice(5,7)} às ${info.fontes_ultima.slice(11,16)}` : "ainda não coletadas";
    document.getElementById("n-novidades-titulo").textContent = `Novidades da internet, ${fontesOk}` + (info.fontes_com_erro ? ` (${info.fontes_com_erro} com erro)` : "");
    document.getElementById("n-novidades").replaceChildren(...(info.artigos.length ? info.artigos.map(a => h("li",{onclick:ev=>ev.currentTarget.classList.toggle("aberto")},
      h("span",{}, a.titulo), h("small",{style:"grid-column:1"}, `${a.fonte || "internet"}, ${(a.publicado || a.coletado_em).slice(8,10)}/${(a.publicado || a.coletado_em).slice(5,7)}`),
      h("span",{class:"res"}, a.resumo || "Resumo pendente: a IA local resume na próxima rodada.")))
      : [h("li",{}, h("small",{}, "As fontes são baixadas em segundo plano. Configure em Fontes e envios."))]));
    document.getElementById("n-local").textContent = nucleo.locais;
    const mic = document.getElementById("n-mic");
    mic.disabled = !info.voz; mic.title = info.voz ? "Segurar para falar (transcrição local)" : (info.voz_motivo || "Voz local indisponível");
    const hoje = hojeISO();
    document.getElementById("n-lembretes").replaceChildren(...(info.lembretes.length ? info.lembretes.map(l => h("li",{class: l.data && l.data < hoje ? "atraso" : ""},
      h("button",{class:"ck","aria-label":"Concluir lembrete", title:"Concluir", onclick:async()=>{ await api(`/api/cerebro/lembretes/${l.id}/feito`,{method:"POST",body:"{}"}); avisar("Lembrete concluído."); carregarNucleo(); }}),
      h("span",{}, l.texto), h("small",{}, l.data ? `${ddmm(l.data)}${l.hora ? " às "+l.hora : ""}` : "sem data"))) : [h("li",{}, h("span"), h("small",{},"Nenhum lembrete aberto."))]));
    document.getElementById("n-notas").replaceChildren(...(info.notas.length ? info.notas.map(n => h("li",{},
      h("span",{style:"color:var(--n-latao);font-size:11px;padding-top:2px"}, n.tipo),
      h("span",{}, n.texto.length > 110 ? n.texto.slice(0,109)+"…" : n.texto),
      h("small",{}, [n.projeto, ...(n.pessoas||[])].filter(Boolean).join(", ") || " "))) : [h("li",{}, h("span"), h("small",{},"Nada anotado ainda."))]));
    desenharMapa(await api("/api/cerebro/mapa"));
  } catch(err){ avisar(err.message); }
}

function rolarFeed(){ const f = document.getElementById("n-feed"); f.scrollTop = f.scrollHeight; }
/* resposta em fluxo: o texto aparece enquanto a IA escreve; no modo voz, cada frase já é falada */
async function pedir(texto, opcoes = {}){
  texto = (texto || "").trim(); if (!texto) return;
  const voz = !!opcoes.voz;
  const feed = document.getElementById("n-feed");
  feed.append(h("div",{class:"n-eu"}, texto)); rolarFeed();
  document.getElementById("n-input").value = "";
  estadoNucleo("analisando");
  palcoPergunta(texto);
  if (voz) legenda("Você", texto);
  let vivo = null, pVivo = null, bruto = "", buffer = "";
  if (voz) interromperFala();
  const g = fala.geracao;
  const finalizar = r => {
    nucleo.locais++; document.getElementById("n-local").textContent = nucleo.locais;
    if (r.tipo === "briefing"){ if (vivo) vivo.remove(); feed.append(h("div",{class:"n-resp"}, h("span",{class:"selo"}, h("i"), "Briefing"), h("p",{}, "Abrindo o briefing do dia."))); rolarFeed(); iniciarBriefing(); return; }
    const cartao = cartaoResposta(r, {semDigitacao: !!vivo});
    if (vivo) vivo.replaceWith(cartao); else feed.append(cartao);
    palcoFinal(r, !!vivo);
    if (!voz) legenda("", "");
    rolarFeed(); aplicarNivel(r);
    if (r.tipo === "nota" || r.acao) carregarNucleo();
    if (voz){ if (vivo){ if (buffer.trim()) enfileirarFala(buffer, g); } else falarCartao(r); }
    if (!filaFala.tocando) estadoNucleo(r.acao ? "confirmar" : estadoOcioso());
  };
  try {
    const resp = await fetch("/api/cerebro/perguntar-fluxo",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({texto, voz})});
    if (!resp.ok){ const d = await resp.json().catch(()=>({})); throw new Error(d.erro || "Falha na comunicação com o aplicativo."); }
    const leitor = resp.body.getReader(), dec = new TextDecoder(); let resto = "";
    for (;;){
      const {value, done} = await leitor.read(); if (done) break;
      resto += dec.decode(value, {stream:true});
      let i;
      while ((i = resto.indexOf("\n")) >= 0){
        const linha = resto.slice(0, i); resto = resto.slice(i + 1);
        if (!linha.trim()) continue;
        const ev = JSON.parse(linha);
        if (ev.evento === "inicio"){
          pVivo = h("div",{class:"txt-vivo"});
          const rotuloVivo = ev.origem === "nuvem" ? `${ev.modelo} (automático${ev.sem_dados_pessoais ? ", sem dados seus" : ""}), escrevendo…` : `IA local (${ev.modelo}), escrevendo…`;
          vivo = h("div",{class:"n-resp ao-vivo","data-nivel":ev.origem === "nuvem" ? "nuvem" : "normal"}, h("span",{class:"selo"}, h("i"), rotuloVivo), pVivo);
          if (ev.origem === "nuvem"){ definirHumor("nuvem", 6000); }
          feed.append(vivo); rolarFeed(); emitirOnda(humor.base); palcoAoVivo(rotuloVivo);
        } else if (ev.evento === "texto"){
          bruto += ev.texto; pVivo.textContent = bruto; rolarFeed(); palcoTexto(bruto);
          if (voz){ buffer += ev.texto;
            const m = buffer.match(/^([\s\S]*?[.!?…:])(\s+|$)/);
            if (m && m[1].length > 18){ enfileirarFala(m[1], g); buffer = buffer.slice(m[0].length); } }
        } else if (ev.evento === "fim") finalizar(ev.resposta);
        else if (ev.evento === "erro") throw new Error(ev.erro);
      }
    }
  } catch(err){
    if (vivo) vivo.remove();
    const erro = {tipo:"erro", titulo:err.message, linhas:[], itens:[], local:true};
    feed.append(cartaoResposta(erro)); palcoFinal(erro, false); estadoNucleo(estadoOcioso());
  }
}
function cartaoResposta(r, opc = {}){
  const selo = r.tipo === "erro" ? h("span",{class:"selo"}, h("i",{style:"background:var(--n-brasa);box-shadow:none"}), "Aviso")
    : r.tipo === "ia_local" ? h("span",{class:"selo"}, h("i"), `IA local (${r.modelo}), sem internet`)
    : r.local ? h("span",{class:"selo"}, h("i"), "Respondido localmente")
    : h("span",{class:"selo"}, h("i"), r.automatico
        ? `${r.provedor} (automático)${r.envio.sem_dados_pessoais ? ", sem nenhum dado seu" : `, ${r.envio.mascarados} dado(s) mascarado(s)`}`
        : `Resposta do ${r.provedor || "Claude"}. Enviado: ${r.envio.trechos} trecho(s), ${r.envio.caracteres} caracteres, ${r.envio.mascarados} dado(s) mascarado(s)`);
  let itens = r.itens.length ? h("div",{class:"n-itens"}, r.itens.map((i,k) => h("div",{class:"n-item"+(i.alerta?" alerta":""), style:`--i:${k}`},
    h("b",{}, i.titulo), i.valor ? h("span",{class:"v"}, i.valor) : h("span"),
    i.meta ? h("small",{}, i.meta) : null, i.trecho ? h("span",{class:"tr"}, i.trecho) : null))) : null;
  if (itens && r.fontes_recolhidas){
    itens.style.display = "none";
    const lista = itens;
    itens = h("div",{}, h("button",{class:"n-fontes-toggle", onclick:ev=>{ const ab = lista.style.display === "none";
      lista.style.display = ab ? "grid" : "none"; ev.target.textContent = ab ? "Ocultar fontes" : `Ver ${r.itens.length} fonte(s) usadas`; }},
      `Ver ${r.itens.length} fonte(s) usadas`), lista);
  }
  const botoes = h("div",{class:"n-botoes"});
  if (r.acao && r.acao.tipo === "ferramenta"){
    const concluir = x => { document.getElementById("n-feed").append(cartaoResposta(x)); rolarFeed(); aplicarNivel(x); estadoNucleo(estadoOcioso()); if (conversa.ativa) falarCartao(x); };
    const confirmar = async (ev, lembrar) => { ev.target.disabled = true;
      try { const x = await api("/api/acoes/confirmar",{method:"POST",body:JSON.stringify({token:r.acao.token, lembrar})});
        ev.target.closest(".n-botoes").remove(); concluir(x);
        if (x.ics) document.querySelector("#n-feed .n-resp:last-child")?.append(h("a",{class:"n-btn", href:x.ics, download:""}, "Levar para o Google/Outlook (.ics)")); }
      catch(err){ avisar(err.message); ev.target.disabled = false; } };
    const recusar = async (ev, nunca) => { try { const x = await api("/api/acoes/recusar",{method:"POST",body:JSON.stringify({token:r.acao.token, nunca})});
      ev.target.closest(".n-botoes").remove(); concluir(x); } catch(err){ avisar(err.message); } };
    if (r.pergunta_permissao && r.acao.pode_lembrar){
      botoes.append(h("button",{class:"n-btn forte", onclick:ev=>confirmar(ev, true)}, "Fazer e não perguntar mais"));
      botoes.append(h("button",{class:"n-btn", onclick:ev=>confirmar(ev, false)}, "Fazer só agora"));
      botoes.append(h("button",{class:"n-btn", onclick:ev=>recusar(ev, false)}, "Agora não"));
      botoes.append(h("button",{class:"n-btn perigo", onclick:ev=>recusar(ev, true)}, "Nunca"));
    } else {
      botoes.append(h("button",{class:"n-btn forte", onclick:ev=>confirmar(ev, false)}, r.acao.rotulo || "Executar"));
      botoes.append(h("button",{class:"n-btn", onclick:ev=>recusar(ev, false)}, "Cancelar"));
    }
  } else if (r.acao && r.pergunta_permissao){
    const concluir = x => { const res = {tipo:"acao_resultado", titulo:x.mensagem, linhas:[], itens:[], local:true, ok:true, ics:x.ics, origem:"nucleo"};
      document.getElementById("n-feed").append(cartaoResposta(res)); rolarFeed(); aplicarNivel(res); palcoFinal(res, false);
      estadoNucleo(estadoOcioso()); carregarNucleo(); acompanharSilencioso(); if (conversa.ativa) falarCartao(res); };
    const fazer = async (ev, lembrar) => { ev.target.disabled = true;
      try { const x = await api("/api/cerebro/acao",{method:"POST",body:JSON.stringify({tipo:r.acao.tipo, dados:r.acao.dados, lembrar})});
        ev.target.closest(".n-botoes").remove(); concluir(x); }
      catch(err){ avisar(err.message); ev.target.disabled = false; } };
    const recusar = async (ev, nunca) => {
      try { const x = await api("/api/cerebro/recusar",{method:"POST",body:JSON.stringify({tipo:r.acao.tipo, nunca})});
        ev.target.closest(".n-botoes").remove(); concluir({...x, ok:true}); } catch(err){ avisar(err.message); } };
    if (r.acao.pode_lembrar) botoes.append(h("button",{class:"n-btn forte", onclick:ev=>fazer(ev, true)}, "Sim, e não precisa perguntar mais"));
    botoes.append(h("button",{class:"n-btn" + (r.acao.pode_lembrar ? "" : " forte"), onclick:ev=>fazer(ev, false)}, "Sim, só desta vez"));
    botoes.append(h("button",{class:"n-btn", onclick:ev=>recusar(ev, false)}, "Agora não"));
    botoes.append(h("button",{class:"n-btn perigo", onclick:ev=>recusar(ev, true)}, "Nunca"));
  } else if (r.acao){
    botoes.append(h("button",{class:"n-btn forte", onclick:async ev=>{
      ev.target.disabled = true;
      try { const x = await api("/api/cerebro/acao",{method:"POST",body:JSON.stringify({tipo:r.acao.tipo, dados:r.acao.dados})});
        ev.target.textContent = x.mensagem; avisar(x.mensagem); estadoNucleo("espera"); carregarNucleo(); acompanharSilencioso();
        definirHumor("sucesso", 5000); emitirOnda("sucesso");
        if (x.ics) ev.target.closest(".n-botoes").append(h("a",{class:"n-btn", href:x.ics, download:""}, "Levar para o Google/Outlook (.ics)")); }
      catch(err){ avisar(err.message); ev.target.disabled = false; }
    }}, r.acao.rotulo + (r.acao.descricao ? ` (${r.acao.descricao})` : "")));
    if (r.tipo === "confirmar") botoes.append(h("button",{class:"n-btn", onclick:ev=>{ ev.target.closest(".n-botoes").remove(); estadoNucleo("espera"); }}, "Descartar"));
  }
  if (r.ics && !r.acao) botoes.append(h("a",{class:"n-btn", href:r.ics, download:""}, "Levar para o Google/Outlook (.ics)"));
  if (r.pode_enviar) botoes.append(h("button",{class:"n-btn brasa", onclick:()=>prepararEnvio(r.pergunta, r.contexto_ids || [], !!r.web)},
    r.web ? "Pesquisar com o Claude" : r.tipo === "sem_resultado" ? "Perguntar ao Claude" : "Aprofundar com o Claude"));
  if (temVozLocal()) botoes.append(h("button",{class:"n-btn", onclick:()=>falarCartao(r)}, "Ouvir"));
  const aprender = r.conversa_id ? linhaAprender(r.conversa_id) : null;
  const risco = r.risco ? h("span",{class:"n-risco "+r.risco}, r.risco === "alto" ? "risco alto: confirme na tela" : "risco médio: confirme por clique ou dizendo “sim”") : null;
  if (r.tipo === "acao_resultado"){
    const saida = h("pre",{class:"n-saida"}, r.linhas.join("\n"));
    const titulo = h("h3",{}, r.titulo);
    const doNucleo = r.origem === "nucleo";
    const corpo = doNucleo ? r.linhas.map(l => h("p",{}, l)) : (r.linhas.length ? [saida] : []);
    const convite = r.ics ? h("div",{class:"n-botoes"}, h("a",{class:"n-btn", href:r.ics, download:""}, "Levar para o Google/Outlook (.ics)")) : null;
    const cartao = h("div",{class:"n-resp"+(r.ok === false ? " falhou" : ""), "data-nivel":r.nivel || (r.ok === false ? "normal" : "sucesso")},
      h("span",{class:"selo"}, h("i"), doNucleo ? "Feito pelo Núcleo" : "Ação no computador"),
      titulo, ...corpo, convite, aprender);
    if (r.tarefa){
      (async function acompanhar(){
        try { const t = await api(`/api/acoes/tarefa/${r.tarefa}`);
          titulo.textContent = t.titulo;
          const texto = t.linhas.length ? t.linhas.join("\n") : (t.estado === "rodando" ? "Em andamento…" : "");
          saida.textContent = texto;
          if (texto && !saida.isConnected) titulo.after(saida);
          if (!texto) saida.remove();
          if (t.estado === "rodando") setTimeout(acompanhar, 2000);
          else { if (t.estado === "erro") cartao.classList.add("falhou"); carregarNucleo();
            if (conversa.ativa) falar(t.titulo); }
        } catch(err){ saida.textContent = err.message; }
      })();
    }
    return cartao;
  }
  if (r.abrir) botoes.append(h("button",{class:"n-btn", onclick:()=>{ if (r.abrir.tela === "mente"){ if (r.abrir.aba === "decisoes") mt.decisao = r.abrir.id; irPara("mente"); carregarMente(r.abrir.aba); } else irPara(r.abrir.tela); }}, ({mente:"Abrir em Mente", pessoas:"Abrir em Pessoas", emails:"Abrir em E-mails", financeiro:"Abrir no Financeiro"})[r.abrir.tela] || "Abrir"));
  const conf = r.confianca ? h("span",{class:"n-conf "+r.confianca.nivel, title:r.confianca.motivo}, `confiança ${({alta:"alta",media:"média",baixa:"baixa"})[r.confianca.nivel]}`) : null;
  const linhasEl = r.linhas.map(l => { const p = h("p",{}); if (["ia_local","claude"].includes(r.tipo) && !opc.semDigitacao) revelarTexto(p, l); else p.textContent = l; return p; });
  const tempo = r.tempos && r.tempos.total ? h("span",{class:"n-tempo", title:"Tempo até começar a responder e tempo total"},
    (r.tempos.primeiro ? `${r.tempos.primeiro.toFixed(1).replace(".",",")} s até começar · ` : "") + `${r.tempos.total.toFixed(1).replace(".",",")} s`) : null;
  const seloFinal = (conf || tempo) ? h("span",{class:"selo"}, ...selo.childNodes, conf, tempo) : selo;
  return h("div",{class:"n-resp"+(r.local?"":" claude"), "data-nivel":r.nivel || "normal"}, seloFinal, r.titulo ? h("h3",{}, r.titulo, risco) : null,
    ...linhasEl, itens, botoes.children.length ? botoes : null, aprender);
}
function linhaAprender(id){
  const caixa = h("div",{class:"n-aprender"});
  const util = h("button",{class:"n-mini", onclick:async()=>{
    try { await api(`/api/cerebro/conversas/${id}/avaliar`,{method:"POST",body:JSON.stringify({util:true})});
      util.textContent = "Marcado como útil"; util.classList.add("feito"); } catch(err){ avisar(err.message); } }}, "Útil");
  const ruim = h("button",{class:"n-mini", onclick:async()=>{
    try { await api(`/api/cerebro/conversas/${id}/avaliar`,{method:"POST",body:JSON.stringify({util:false})});
      ruim.textContent = "Não será usado de novo"; ruim.classList.add("feito"); } catch(err){ avisar(err.message); } }}, "Não ajudou");
  const corr = h("button",{class:"n-mini", onclick:()=>{
    const campo = h("textarea",{placeholder:"Escreva a informação correta. O Núcleo passa a seguir isso."});
    const form = h("div",{class:"n-corrigir"}, campo, h("div",{class:"n-botoes"},
      h("button",{class:"n-btn forte", onclick:async ev=>{
        try { const x = await api(`/api/cerebro/conversas/${id}/corrigir`,{method:"POST",body:JSON.stringify({texto:campo.value})});
          form.replaceWith(h("span",{class:"rot"}, x.mensagem)); carregarNucleo(); } catch(err){ avisar(err.message); } }}, "Ensinar"),
      h("button",{class:"n-btn", onclick:()=>form.remove()}, "Cancelar")));
    caixa.append(form); campo.focus(); }}, "Corrigir");
  caixa.append(h("span",{class:"rot"},`Isto ajuda ${nomeAssist()} a aprender:`), util, ruim, corr);
  return caixa;
}

/* envio ao Claude: sempre com prévia e confirmação */
async function prepararEnvio(pergunta, contexto, web=false){
  const modal = document.getElementById("n-modal"), caixa = document.getElementById("n-modal-caixa");
  const fechar = () => { modal.classList.remove("aberto"); estadoNucleo("espera"); };
  if (nucleo.info && !nucleo.info.chave){
    caixa.replaceChildren(h("h2",{id:"n-modal-titulo"},"Falta configurar a chave da API"),
      h("p",{},"Faça isto uma única vez:"),
      h("ol",{},
        h("li",{},"Acesse console.anthropic.com e entre ou crie sua conta."),
        h("li",{},"Em Billing, adicione um cartão e um crédito inicial. A cobrança é por uso, separada da assinatura do Claude."),
        h("li",{},"Em API Keys, clique em Create Key, dê o nome Núcleo e copie a chave, que começa com sk-ant-."),
        h("li",{},"Feche o app. No terminal, dentro da pasta do app, rode ", h("code",{},"python app.py --salvar-chave-claude"), " e cole a chave. Ela fica no cofre do sistema."),
        h("li",{},"Abra o app de novo e repita a pergunta.")),
      h("div",{class:"n-botoes"}, h("button",{class:"n-btn forte", onclick:fechar},"Entendi")));
    modal.classList.add("aberto"); return;
  }
  estadoNucleo("confirmar");
  let prev;
  try { prev = await api("/api/cerebro/preparar-envio",{method:"POST",body:JSON.stringify({pergunta, contexto_ids:contexto, web})}); }
  catch(err){ avisar(err.message); estadoNucleo("espera"); return; }
  caixa.replaceChildren(
    h("h2",{id:"n-modal-titulo"}, prev.web ? "Pesquisar na web com o Claude?" : "Enviar ao Claude?"),
    h("p",{}, `Só o texto abaixo sai deste computador: ${prev.trechos} trecho(s), ${prev.caracteres} caracteres. `
      + (prev.mascarados ? `${prev.mascarados} dado(s) sensível(is) foram mascarados e voltam ao normal só na resposta, aqui no app.` : "Nenhum dado sensível detectado.")),
    h("pre",{}, prev.previa),
    h("p",{style:"margin-top:12px"}, `Modelo: ${prev.modelo}.` + (prev.web ? " O Claude fará até 3 buscas na web com esse termo." : "") + " O envio fica registrado no histórico."),
    h("div",{class:"n-botoes"},
      h("button",{class:"n-btn forte", onclick:async ev=>{
        ev.target.disabled = true; modal.classList.remove("aberto"); estadoNucleo("claude");
        try { const r = await api("/api/cerebro/enviar",{method:"POST",body:JSON.stringify({token:prev.token})});
          document.getElementById("n-feed").append(cartaoResposta(r)); rolarFeed(); aplicarNivel(r); carregarNucleo(); }
        catch(err){ document.getElementById("n-feed").append(cartaoResposta({tipo:"erro",titulo:err.message,linhas:[],itens:[],local:true})); rolarFeed(); }
        estadoNucleo("espera");
      }}, "Enviar este texto"),
      h("button",{class:"n-btn", onclick:fechar},"Cancelar, manter local")));
  modal.classList.add("aberto");
}
document.getElementById("n-modal").addEventListener("click", ev => { if (ev.target.id === "n-modal"){ ev.currentTarget.classList.remove("aberto"); estadoNucleo("espera"); } });

/* voz: grava no navegador, transcreve no computador (Vosk) */
async function alternarGravacao(){
  const btn = document.getElementById("n-mic");
  if (nucleo.gravando){ return pararGravacao(); }
  try {
    const fluxo = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1, echoCancellation:true, noiseSuppression:true}});
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const fonte = ac.createMediaStreamSource(fluxo), proc = ac.createScriptProcessor(4096,1,1);
    const partes = [];
    proc.onaudioprocess = e => { const d = e.inputBuffer.getChannelData(0); partes.push(new Float32Array(d));
      let s = 0; for (let i=0;i<d.length;i+=8) s += d[i]*d[i]; nucleo.nivel = Math.min(.5, Math.sqrt(s/(d.length/8))*2); };
    fonte.connect(proc); proc.connect(ac.destination);
    nucleo.gravando = {fluxo, ac, proc, partes, inicio:Date.now(), limite:setTimeout(pararGravacao, 60000)};
    btn.classList.add("gravando"); btn.setAttribute("aria-label","Parar e transcrever"); estadoNucleo("ouvindo");
  } catch(err){ avisar("Microfone indisponível: " + err.message); }
}
async function pararGravacao(){
  const g = nucleo.gravando; if (!g) return;
  nucleo.gravando = null; clearTimeout(g.limite); nucleo.nivel = 0;
  g.proc.disconnect(); g.fluxo.getTracks().forEach(t => t.stop());
  const btn = document.getElementById("n-mic"); btn.classList.remove("gravando"); btn.setAttribute("aria-label","Falar");
  const taxa = g.ac.sampleRate; g.ac.close();
  const total = g.partes.reduce((n,p)=>n+p.length,0), junto = new Float32Array(total);
  let o = 0; g.partes.forEach(p => { junto.set(p,o); o += p.length; });
  const razao = taxa/16000, n = Math.floor(total/razao), pcm = new Int16Array(n);
  for (let i=0;i<n;i++){ const ini = Math.floor(i*razao), fim = Math.min(total, Math.floor((i+1)*razao)); let s = 0;
    for (let k=ini;k<fim;k++) s += junto[k]; const v = Math.max(-1, Math.min(1, s/Math.max(1,fim-ini))); pcm[i] = v < 0 ? v*0x8000 : v*0x7fff; }
  estadoNucleo("transcrevendo");
  try {
    const r = await fetch("/api/voz",{method:"POST",headers:{"Content-Type":"application/octet-stream"},body:pcm.buffer});
    const d = await r.json(); if (!r.ok) throw new Error(d.erro || "Falha na transcrição.");
    if (!d.texto){ avisar("Não entendi o áudio. Tente de novo, mais perto do microfone."); estadoNucleo("espera"); return; }
    pedir(d.texto);
  } catch(err){ avisar(err.message); estadoNucleo("espera"); }
}
document.getElementById("n-mic").addEventListener("click", alternarGravacao);

/* fala: Piper no computador; sem Piper, só vozes instaladas no Windows */
const fala = {ac:null, fonte:null, analisador:null, geracao:0};
function vozLocal(){ return "speechSynthesis" in window ? speechSynthesis.getVoices().find(v => v.localService && v.lang.toLowerCase().startsWith("pt")) : null; }
function temPiper(){ return !!(nucleo.info && nucleo.info.voz_status && nucleo.info.voz_status.falar); }
function temVozLocal(){ return temPiper() || !!vozLocal(); }
function dividirFrases(t){
  const partes = String(t||"").split(/(?<=[.!?…])\s+|\n+/).map(x=>x.trim()).filter(Boolean), saida = [];
  let atual = ""; partes.forEach(p => { if ((atual + " " + p).length < 200) atual = (atual + " " + p).trim(); else { if (atual) saida.push(atual); atual = p; } });
  if (atual) saida.push(atual); return saida;
}
function interromperFala(){
  fala.geracao++; if (typeof filaFala !== "undefined") filaFala.itens = [];
  if (fala.fonte){ try { fala.fonte.onended = null; fala.fonte.stop(); } catch(e){} fala.fonte = null; }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  nucleo.nivel = 0;
}
async function baixarAudio(texto){
  const r = await fetch("/api/voz/falar",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({texto})});
  if (!r.ok){ const d = await r.json().catch(()=>({})); throw new Error(d.erro || "Falha ao gerar a voz."); }
  const dados = await r.arrayBuffer();
  if (!dados.byteLength) return null;
  return await fala.ac.decodeAudioData(dados);
}
function tocar(buffer, g){
  return new Promise(ok => {
    if (!buffer || g !== fala.geracao) return ok();
    const src = fala.ac.createBufferSource(); src.buffer = buffer;
    src.connect(fala.analisador); fala.fonte = src; src.onended = () => { fala.fonte = null; ok(); };
    src.start();
    const dados = new Uint8Array(fala.analisador.fftSize);
    (function medir(){ if (fala.fonte !== src) return; fala.analisador.getByteTimeDomainData(dados);
      let s = 0; for (let i=0;i<dados.length;i+=4){ const v = (dados[i]-128)/128; s += v*v; }
      nucleo.nivel = Math.min(.45, Math.sqrt(s/(dados.length/4))*1.6); requestAnimationFrame(medir); })();
  });
}
const filaFala = {itens:[], tocando:false};
function garantirAudio(){
  if (!fala.ac){ fala.ac = new (window.AudioContext || window.webkitAudioContext)(); fala.analisador = fala.ac.createAnalyser(); fala.analisador.fftSize = 1024; fala.analisador.connect(fala.ac.destination); }
  if (fala.ac.state === "suspended") fala.ac.resume().catch(()=>{});
}
function enfileirarFala(frase, g){
  frase = (frase || "").trim(); if (!frase || g !== fala.geracao) return;
  if (!temPiper()){
    const v = vozLocal(); if (!v) return;
    const u = new SpeechSynthesisUtterance(frase); u.voice = v; u.lang = v.lang; u.rate = 1.05; speechSynthesis.speak(u); return;
  }
  garantirAudio();
  filaFala.itens.push({g, frase, audio: baixarAudio(frase)});
  if (!filaFala.tocando) tocarFila();
}
async function tocarFila(){
  filaFala.tocando = true; estadoNucleo("falando");
  while (filaFala.itens.length){
    const it = filaFala.itens.shift();
    if (it.g !== fala.geracao) continue;
    try { const buf = await it.audio; if (it.g === fala.geracao){ legenda(nomeAssist(), it.frase); await tocar(buf, it.g); } } catch(e){}
  }
  filaFala.tocando = false; nucleo.nivel = 0; estadoNucleo(estadoOcioso()); legenda("", "");
}
async function falar(texto){
  interromperFala();
  const g = fala.geracao;
  legenda(nomeAssist(), texto.length > 160 ? texto.slice(0, 157) + "…" : texto);
  setTimeout(() => { if (g === fala.geracao && !filaFala.tocando) legenda("", ""); }, Math.max(4000, texto.length * 70));
  if (!temPiper()){
    const v = vozLocal(); if (!v){ avisar("Nenhuma voz instalada. Use o instalador para baixar a voz Piper."); return; }
    const u = new SpeechSynthesisUtterance(texto); u.voice = v; u.lang = v.lang; u.rate = 1.05;
    estadoNucleo("falando"); u.onend = () => { if (g === fala.geracao) estadoNucleo(estadoOcioso()); };
    speechSynthesis.speak(u); return;
  }
  if (!fala.ac){ fala.ac = new (window.AudioContext || window.webkitAudioContext)(); fala.analisador = fala.ac.createAnalyser(); fala.analisador.fftSize = 1024; fala.analisador.connect(fala.ac.destination); }
  if (fala.ac.state === "suspended") await fala.ac.resume();
  const frases = dividirFrases(texto); if (!frases.length) return;
  estadoNucleo("falando");
  try {
    let proxima = baixarAudio(frases[0]);
    for (let i = 0; i < frases.length; i++){
      const buf = await proxima;
      if (g !== fala.geracao) return;
      if (i + 1 < frases.length) proxima = baixarAudio(frases[i+1]);   // gera a próxima enquanto esta toca
      await tocar(buf, g);
      if (g !== fala.geracao) return;
    }
  } catch(err){ avisar(err.message); }
  if (g === fala.geracao){ nucleo.nivel = 0; estadoNucleo(estadoOcioso()); }
}
async function falarCartao(r){
  try { const d = await api("/api/voz/fala-de",{method:"POST",body:JSON.stringify(r)}); falar(d.fala); } catch(err){ avisar(err.message); }
}
function lerResumo(){
  const r = estado.cfg && estado.cfg.resumo; if (!r){ avisar("Ainda não há resumo do dia."); return; }
  const partes = [`Bom dia${r.nome ? ", "+r.nome : ""}. Hoje é ${r.data_longa}.`];
  r.tres.forEach((t,i) => partes.push(`${["Primeiro","Segundo","Terceiro"][i]}: ${t.titulo}. ${t.porque}. ${t.acao}`));
  if (r.compromissos.length) partes.push("Na agenda: " + r.compromissos.map(c => `${c.hora}, ${c.titulo}`).join("; ") + ".");
  partes.push(`${r.resposta.length} e-mails pedem resposta e ${r.esperar} podem esperar.`);
  falar(partes.join(" "));
}

/* modo conversa: escuta contínua, detecta quando você fala e quando para */
function estadoOcioso(){
  if (!conversa.ativa) return "espera";
  return conversa.sentinela && Date.now() > (conversa.acordadoAte || 0) ? "sentinela" : "conversa";
}
const conversa = {ativa:false, sentinela:false, acordadoAte:0, ac:null, fluxo:null, proc:null, ruido:.008, falando:false, voz:0, silencio:0, buffer:[], pre:[], ocupado:false, taxa:48000};
function paraPCM16(partes, taxa){
  const total = partes.reduce((n,p)=>n+p.length,0), junto = new Float32Array(total);
  let o = 0; partes.forEach(p => { junto.set(p,o); o += p.length; });
  const razao = taxa/16000, n = Math.floor(total/razao), pcm = new Int16Array(n);
  for (let i=0;i<n;i++){ const a = Math.floor(i*razao), b = Math.min(total, Math.floor((i+1)*razao)); let s = 0;
    for (let k=a;k<b;k++) s += junto[k]; const v = Math.max(-1, Math.min(1, s/Math.max(1,b-a))); pcm[i] = v < 0 ? v*0x8000 : v*0x7fff; }
  return pcm;
}
async function alternarConversa(sentinela=false){
  const btn = document.getElementById("n-conversa");
  if (conversa.ativa){
    conversa.ativa = false; conversa.sentinela = false; interromperFala();
    try { conversa.proc.disconnect(); conversa.fluxo.getTracks().forEach(t=>t.stop()); conversa.ac.close(); } catch(e){}
    btn.classList.remove("conversando"); btn.setAttribute("aria-label","Conversar por voz"); estadoNucleo("espera"); return;
  }
  try {
    conversa.fluxo = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1, echoCancellation:true, noiseSuppression:true, autoGainControl:true}});
  } catch(err){ avisar("Microfone indisponível: " + err.message); return; }
  conversa.ac = new (window.AudioContext || window.webkitAudioContext)(); conversa.taxa = conversa.ac.sampleRate;
  const fonte = conversa.ac.createMediaStreamSource(conversa.fluxo);
  conversa.proc = conversa.ac.createScriptProcessor(2048,1,1);
  const passoMs = 2048 / conversa.taxa * 1000;
  Object.assign(conversa, {ativa:true, sentinela:!!sentinela, acordadoAte:0, falando:false, voz:0, silencio:0, buffer:[], pre:[], ocupado:false, ruido:.008});
  conversa.proc.onaudioprocess = e => {
    if (!conversa.ativa) return;
    const d = new Float32Array(e.inputBuffer.getChannelData(0));
    let s = 0; for (let i=0;i<d.length;i+=4) s += d[i]*d[i];
    const rms = Math.sqrt(s/(d.length/4));
    const tocando = !!fala.fonte || ("speechSynthesis" in window && speechSynthesis.speaking);
    const limiar = Math.max(.012, conversa.ruido*3) * (tocando ? 1.8 : 1);
    if (!conversa.falando){
      if (rms < limiar) conversa.ruido = conversa.ruido*.97 + rms*.03;
      conversa.pre.push(d); if (conversa.pre.length > Math.ceil(350/passoMs)) conversa.pre.shift();
      if (rms > limiar){ conversa.voz += passoMs; } else conversa.voz = 0;
      if (conversa.voz >= (tocando ? 260 : 140) && !conversa.ocupado){
        if (tocando) interromperFala();              // você fala por cima: ele para e escuta
        conversa.falando = true; conversa.silencio = 0; conversa.buffer = conversa.pre.slice(); estadoNucleo("ouvindo");
      }
    } else {
      conversa.buffer.push(d); nucleo.nivel = Math.min(.5, rms*2.5);
      conversa.silencio = rms < limiar*.8 ? conversa.silencio + passoMs : 0;
      const duracao = conversa.buffer.length * passoMs;
      if (conversa.silencio >= 850 || duracao > 30000){
        conversa.falando = false; conversa.voz = 0; nucleo.nivel = 0;
        if (duracao - conversa.silencio > 350) enviarFala(conversa.buffer.slice()); else estadoNucleo(estadoOcioso());
        conversa.buffer = [];
      }
    }
  };
  fonte.connect(conversa.proc); conversa.proc.connect(conversa.ac.destination);
  btn.classList.add("conversando"); btn.setAttribute("aria-label","Encerrar modo conversa"); estadoNucleo(estadoOcioso());
  setInterval(() => { if (conversa.ativa && !conversa.falando && !conversa.ocupado && !fala.fonte && ["conversa","sentinela"].includes(nucleo.estado)) estadoNucleo(estadoOcioso()); }, 3000);
  if (!nucleo.info || !nucleo.info.voz_status || !nucleo.info.voz_status.falar) avisar("Sem a voz Piper, as respostas usam a voz do Windows.");
}
async function enviarFala(partes){
  conversa.ocupado = true; estadoNucleo("transcrevendo");
  try {
    const pcm = paraPCM16(partes, conversa.taxa);
    const cab = {"Content-Type":"application/octet-stream"};
    if (conversa.sentinela && Date.now() > (conversa.acordadoAte || 0)) cab["X-Sentinela"] = "1";
    const r = await fetch("/api/voz/ouvir",{method:"POST",credentials:"same-origin",headers:cab,body:pcm.buffer});
    const d = await r.json(); if (!r.ok) throw new Error(d.erro || "Falha ao processar a fala.");
    if (!d.ouvido || d.ignorado){ estadoNucleo(estadoOcioso()); return; }
    if (conversa.sentinela) conversa.acordadoAte = Date.now() + 40000;
    if (d.briefing){ iniciarBriefing(); return; }
    if (d.so_chamou){ enfileirarFala("Pois não?", fala.geracao); return; }
    await pedir(d.ouvido, {voz: conversa.ativa});
  } catch(err){ avisar(err.message); estadoNucleo(estadoOcioso()); }
  finally { conversa.ocupado = false; }
}
document.getElementById("n-conversa").addEventListener("click", () => alternarConversa(false));
function escutaContinuaLigada(){ try { return localStorage.getItem("escuta_continua") === "1"; } catch(e){ return false; } }
async function alternarEscutaContinua(){
  const ligar = !escutaContinuaLigada();
  try { localStorage.setItem("escuta_continua", ligar ? "1" : "0"); } catch(e){}
  if (conversa.ativa) await alternarConversa();
  if (ligar) await alternarConversa(true);
  carregarNucleo();
}

/* instalador dos componentes locais */
async function abrirInstalador(){
  const caixaLog = h("pre",{style:"max-height:38vh"}), lista = h("ul",{class:"n-check"});
  const botao = h("button",{class:"n-btn forte", onclick:async()=>{ botao.disabled = true; botao.textContent = "Instalando…";
    try { await api("/api/instalar",{method:"POST",body:"{}"}); acompanharInstalacao(); } catch(err){ avisar(err.message); botao.disabled = false; } }}, "Instalar agora");
  const rotulos = {ollama_instalado:"Ollama instalado", ollama_online:"Ollama rodando", modelo_chat:"Modelo de conversa (qwen3:8b)",
    modelo_embedding:"Modelo de busca (bge-m3)", whisper:"Reconhecimento de voz (Whisper)", piper:"Voz em português (Piper)"};
  async function atualizar(){
    const d = await api("/api/instalar");
    lista.replaceChildren(...Object.entries(d.componentes).map(([k,v]) => h("li",{class:v?"ok":""}, rotulos[k] || k)));
    caixaLog.textContent = d.log.join("\n") || "Nada instalado ainda nesta sessão.";
    caixaLog.scrollTop = caixaLog.scrollHeight;
    if (d.rodando){ botao.disabled = true; botao.textContent = "Instalando…"; }
    else { botao.disabled = false; botao.textContent = d.concluido ? "Rodar de novo" : "Instalar agora"; }
    return d;
  }
  async function acompanharInstalacao(){
    const d = await atualizar().catch(()=>null);
    if (d && d.rodando && document.getElementById("n-modal").classList.contains("aberto")) setTimeout(acompanharInstalacao, 1500);
    else if (d && d.concluido) carregarNucleo();
  }
  abrirModal([
    h("h2",{id:"n-modal-titulo"},"Instalar a IA local e a voz"),
    h("p",{}, "Baixa e instala o Ollama, os modelos de IA (cerca de 6,5 GB), o Whisper (cerca de 1,6 GB) e as vozes em português. "
      + "A internet é usada só para baixar. Depois, tudo funciona offline e sem consumo de tokens."),
    lista, caixaLog,
    h("div",{class:"n-botoes",style:"margin-top:12px"}, botao, h("button",{class:"n-btn", onclick:fecharModal}, "Fechar"))
  ]);
  const d = await atualizar(); if (d.rodando) acompanharInstalacao();
}

document.getElementById("n-enviar").addEventListener("click", () => pedir(document.getElementById("n-input").value));
document.getElementById("n-input").addEventListener("keydown", ev => { if (ev.key === "Enter") pedir(ev.target.value); });
document.addEventListener("keydown", ev => {
  if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && ev.key.toLowerCase() === "k"){ ev.preventDefault(); focarAssistente("nucleo"); }
});


/* ---------- modais: conhecimento e fontes ---------- */
function abrirModal(conteudo){
  const modal = document.getElementById("n-modal"), caixa = document.getElementById("n-modal-caixa");
  caixa.replaceChildren(...conteudo); modal.classList.add("aberto");
}
function fecharModal(){ document.getElementById("n-modal").classList.remove("aberto"); estadoNucleo("espera"); }
async function abrirConhecimento(){
  let dados; try { dados = await api("/api/cerebro/conhecimento"); } catch(err){ avisar(err.message); return; }
  const ult = nucleo.info && nucleo.info.ultima_consolidacao ? `Última consolidação: ${nucleo.info.ultima_consolidacao.slice(8,10)}/${nucleo.info.ultima_consolidacao.slice(5,7)} às ${nucleo.info.ultima_consolidacao.slice(11,16)}.` : "Ainda não houve consolidação.";
  const novo = h("input",{class:"n-campo", type:"text", placeholder:"Ex.: Prefiro reuniões depois das 10h. A Paula é a contadora da Auralis."});
  const tabela = h("table",{class:"n-tab-k"}, h("thead",{}, h("tr",{}, h("th",{},"Tópico"), h("th",{},"O que sei"), h("th",{},"Origem"), h("th",{}))));
  const corpo = h("tbody",{});
  dados.itens.forEach(k => {
    const campo = h("textarea",{class:"n-campo", rows:"2", style:"width:100%;resize:vertical"}, k.texto);
    corpo.append(h("tr",{}, h("td",{}, k.topico || ""), h("td",{}, campo),
      h("td",{}, h("span",{class:"n-tag"+(k.fixo?" fixo":"")}, k.origem === "correcao" ? "sua correção" : k.origem === "manual" ? "você" : "aprendido")),
      h("td",{style:"white-space:nowrap"},
        h("button",{class:"n-mini", onclick:async()=>{ try { await api(`/api/cerebro/conhecimento/${k.id}`,{method:"PUT",body:JSON.stringify({texto:campo.value})}); avisar("Atualizado."); } catch(err){ avisar(err.message); } }},"Salvar"), " ",
        h("button",{class:"n-mini", onclick:ev=>{ const tr = ev.target.closest("tr"); tr.style.display = "none";
          avisarDesfazer("Aprendizado apagado.", () => { tr.style.display = ""; }, async () => { await api(`/api/cerebro/conhecimento/${k.id}`,{method:"DELETE"}); tr.remove(); carregarNucleo(); }); }},"Apagar"))));
  });
  if (!dados.itens.length) corpo.append(h("tr",{}, h("td",{colspan:"4",style:"color:var(--n-suave)"},"Nada aprendido ainda. Converse, corrija respostas ou adicione abaixo.")));
  tabela.append(corpo);
  abrirModal([
    h("h2",{id:"n-modal-titulo"},"O que sei sobre você e seu trabalho"),
    h("p",{}, `Tudo aqui fica neste computador e entra nas respostas da IA local. Suas correções têm prioridade. ${ult}`),
    tabela,
    h("div",{class:"n-corrigir",style:"margin-top:14px"}, novo),
    h("div",{class:"n-botoes"},
      h("button",{class:"n-btn forte", onclick:async()=>{ try { await api("/api/cerebro/conhecimento",{method:"POST",body:JSON.stringify({texto:novo.value})}); avisar("Aprendido."); abrirConhecimento(); carregarNucleo(); } catch(err){ avisar(err.message); } }},"Ensinar isto"),
      h("button",{class:"n-btn", onclick:async ev=>{ ev.target.disabled = true; ev.target.textContent = "Consolidando…";
        try { const r = await api("/api/cerebro/consolidar",{method:"POST",body:"{}"}); avisar(r.motivo || `${r.novos} novo(s) aprendizado(s).`); await carregarNucleo(); abrirConhecimento(); }
        catch(err){ avisar(err.message); ev.target.disabled = false; } }},"Consolidar agora"),
      h("button",{class:"n-btn", onclick:fecharModal},"Fechar"))
  ]);
}
async function abrirFontes(){
  let dados; try { dados = await api("/api/cerebro/fontes"); } catch(err){ avisar(err.message); return; }
  const tabela = h("table",{class:"n-tab-k"}, h("thead",{}, h("tr",{}, h("th",{},"Fonte"), h("th",{},"Tema"), h("th",{},"A cada"), h("th",{},"Situação"), h("th",{}))));
  const corpo = h("tbody",{});
  dados.itens.forEach(f => {
    const horas = h("select",{class:"n-campo", onchange:async ev=>{ await api(`/api/cerebro/fontes/${f.id}`,{method:"PUT",body:JSON.stringify({horas:+ev.target.value})}); avisar("Intervalo atualizado."); }},
      [1,3,6,12,24,48,168].map(x => h("option",{value:x, selected:x===f.horas}, x < 24 ? `${x} h` : x === 24 ? "1 dia" : x === 48 ? "2 dias" : "1 semana")));
    const situacao = f.erro ? h("span",{class:"n-tag erro", title:f.erro}, "erro: " + f.erro.slice(0,40))
      : f.ultima ? h("span",{class:"n-tag"}, `${f.ultima.slice(8,10)}/${f.ultima.slice(5,7)} ${f.ultima.slice(11,16)}, ${f.itens} itens`) : h("span",{class:"n-tag"},"aguardando");
    corpo.append(h("tr",{style:f.ativa?"":"opacity:.5"}, h("td",{}, f.nome, h("br"), h("small",{style:"color:var(--n-suave)"}, f.url)), h("td",{}, f.tema || ""), h("td",{}, horas), h("td",{}, situacao),
      h("td",{style:"white-space:nowrap"},
        h("button",{class:"n-mini", onclick:async()=>{ await api(`/api/cerebro/fontes/${f.id}`,{method:"PUT",body:JSON.stringify({ativa:!f.ativa})}); abrirFontes(); }}, f.ativa ? "Pausar" : "Ativar"), " ",
        h("button",{class:"n-mini", onclick:async()=>{ if (!confirm(`Remover ${f.nome}?`)) return; await api(`/api/cerebro/fontes/${f.id}`,{method:"DELETE"}); abrirFontes(); }}, "Remover"))));
  });
  tabela.append(corpo);
  const nome = h("input",{class:"n-campo", placeholder:"Nome"}), url = h("input",{class:"n-campo", placeholder:"https://… (feed RSS ou página)"}),
        tema = h("input",{class:"n-campo", placeholder:"Tema"}), horas = h("select",{class:"n-campo"}, [6,12,24,48].map(x => h("option",{value:x, selected:x===24}, x < 24 ? `${x} h` : x === 24 ? "1 dia" : "2 dias")));
  const envios = (nucleo.info && nucleo.info.envios) || [];
  abrirModal([
    h("h2",{id:"n-modal-titulo"},"Fontes da internet"),
    h("p",{}, "O app baixa estas fontes no intervalo escolhido, resume com a IA local e guarda neste computador. Nenhum dado seu é enviado nesse processo; é só leitura."),
    tabela,
    h("div",{class:"n-form"}, nome, url, tema, horas, h("button",{class:"n-btn forte", onclick:async()=>{
      try { await api("/api/cerebro/fontes",{method:"POST",body:JSON.stringify({nome:nome.value, url:url.value, tema:tema.value, horas:+horas.value})}); avisar("Fonte adicionada."); abrirFontes(); }
      catch(err){ avisar(err.message); } }}, "Adicionar")),
    h("div",{class:"n-botoes",style:"margin-top:12px"},
      h("button",{class:"n-btn", onclick:async()=>{ const r = await api("/api/cerebro/fontes/atualizar",{method:"POST",body:"{}"}); avisar(r.mensagem); }}, "Atualizar todas agora"),
      h("button",{class:"n-btn", onclick:fecharModal}, "Fechar")),
    h("h2",{style:"margin-top:22px;font-size:18px"},"Histórico de envios ao Claude"),
    envios.length ? h("ul",{class:"n-lista"}, envios.map(e => h("li",{style:"grid-template-columns:1fr"}, h("span",{}, e.pergunta),
      h("small",{style:"grid-column:1"}, `${e.quando.slice(8,10)}/${e.quando.slice(5,7)} ${e.quando.slice(11,16)}, ${e.trechos} trecho(s), ${e.caracteres} caracteres, ${e.mascarados} dado(s) mascarado(s)`))))
      : h("p",{}, "Nenhum envio. Tudo ficou neste computador.")
  ]);
}

async function abrirAcoes(){
  let d; try { d = await api("/api/acoes"); } catch(err){ avisar(err.message); return; }
  const rotRisco = {baixo:"executa na hora", medio:"pede confirmação", alto:"só com clique na tela"};
  abrirModal([
    h("h2",{id:"n-modal-titulo"},"Ações no computador"),
    h("p",{}, "O que o Núcleo pode fazer por você, por texto ou voz. Scripts novos e ações desligadas ficam em “acoes” no config.json."),
    h("table",{class:"n-tab-k"}, h("thead",{}, h("tr",{}, h("th",{},"Ação"), h("th",{},"O que faz"), h("th",{},"Segurança"))),
      h("tbody",{}, d.catalogo.map(a => h("tr",{}, h("td",{}, a.nome.replace("script:","script ").replace(/_/g," ")), h("td",{}, a.descricao),
        h("td",{}, h("span",{class:"n-risco "+a.risco, style:"margin:0"}, rotRisco[a.risco])))))),
    h("h2",{style:"margin-top:20px;font-size:18px"},"Histórico"),
    d.historico.length ? h("ul",{class:"n-lista"}, d.historico.map(x => h("li",{style:"grid-template-columns:1fr"},
      h("span",{}, `${x.ok ? "OK" : "Falhou"}: ${x.ferramenta.replace("script:","script ").replace(/_/g," ")}`
        + (x.parametros && x.parametros !== "{}" ? ` ${x.parametros}` : "")),
      h("small",{style:"grid-column:1"}, `${x.quando.slice(8,10)}/${x.quando.slice(5,7)} ${x.quando.slice(11,16)}, ${x.origem}. ${(x.resultado || "").split("\n")[0]}`))))
      : h("p",{}, "Nenhuma ação executada ainda."),
    h("div",{class:"n-botoes",style:"margin-top:12px"}, h("button",{class:"n-btn", onclick:fecharModal}, "Fechar"))
  ]);
}
document.getElementById("n-abrir-acoes").addEventListener("click", abrirAcoes);
document.getElementById("n-abrir-conhecimento").addEventListener("click", abrirConhecimento);
document.getElementById("n-abrir-fontes").addEventListener("click", abrirFontes);

function alternarPaineis(){
  const col = document.querySelector(".n-col.direita");
  const abrir = !col.classList.contains("aberta");
  col.classList.toggle("aberta", abrir);
  document.getElementById("n-paineis").textContent = abrir ? "Fechar painéis" : "Painéis";
  if (abrir) api("/api/cerebro/mapa").then(desenharMapa).catch(()=>{});
}
