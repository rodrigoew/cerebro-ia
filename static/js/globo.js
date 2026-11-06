"use strict";
/* Globo 3D ao vivo (God's Eye View) dentro do Núcleo. */
const globoEstado = {url:null, pronto:false};

async function abrirGlobo(texto){
  let d;
  try { d = await api("/api/globo/abrir",{method:"POST",body:JSON.stringify({texto: texto || ""})}); }
  catch(err){ avisar(err.message); return; }
  if (!d.url){ avisar("Globo indisponível."); return; }
  globoEstado.url = d.url;
  mostrarTelaGlobo(d.plano, d.estado);
}

function montarUrlGlobo(plano){
  // o globo lê a câmera, as camadas e o estilo da âncora (#) do endereço
  const partes = [];
  if (plano && plano.coords) partes.push(`@${plano.coords.lat.toFixed(4)},${plano.coords.lon.toFixed(4)},12z`);
  (plano && plano.camadas || []).forEach(c => partes.push("layer=" + c));
  if (plano && plano.estilo) partes.push("style=" + plano.estilo);
  return globoEstado.url + "/" + (partes.length ? "#" + partes.join("&") : "");
}

function mostrarTelaGlobo(plano, estado){
  irPara("globo");
  const alvo = document.getElementById("tela-globo");
  const url = montarUrlGlobo(plano);
  const quadro = h("iframe",{class:"globo-frame", src:url, allow:"microphone; autoplay; fullscreen",
    title:"Globo ao vivo"});
  const aviso = (estado && estado.rodando === false)
    ? h("div",{class:"globo-aviso"}, "Iniciando o globo… isto pode levar alguns segundos na primeira vez. ",
        h("button",{class:"n-btn pequeno", onclick:()=>mostrarTelaGlobo(plano, {rodando:true})}, "Recarregar"))
    : null;
  alvo.replaceChildren(
    h("div",{class:"globo-topo"},
      h("div",{}, h("b",{},"Globo ao vivo"), h("small",{style:"color:var(--suave);margin-left:8px"}, "dados públicos · God's Eye View")),
      h("div",{style:"display:flex;gap:8px"},
        h("button",{class:"n-btn pequeno", onclick:()=>{ const i = alvo.querySelector("iframe"); if (i) i.src = i.src; }},"Recarregar"),
        h("a",{class:"n-btn pequeno", href:url, target:"_blank"},"Abrir em janela"),
        h("button",{class:"n-btn pequeno", onclick:()=>irPara("nucleo")},"Fechar"))),
    aviso, quadro);
  if (estado && estado.rodando === false){        // espera o servidor subir e recarrega uma vez
    let tentativas = 0;
    const t = setInterval(async () => {
      tentativas++;
      try { const e = await api("/api/globo"); if (e.rodando){ clearInterval(t); quadro.src = url; if (aviso) aviso.remove(); } }
      catch(e){}
      if (tentativas > 20) clearInterval(t);
    }, 2000);
  }
}
