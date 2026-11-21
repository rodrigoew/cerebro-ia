"use strict";
/* Acesso rápido fixo. Agenda, legendas e detalhes ficam na aplicação principal. */
(() => {
  const LARGURA = 176, ALTURA = 40;
  const ROTULOS = {espera:"Núcleo", sentinela:"Núcleo", conversa:"Ouvindo", ouvindo:"Ouvindo",
    transcrevendo:"Entendendo", analisando:"Pensando", claude:"Pensando", falando:"Falando", confirmar:"Confirmar"};
  let p = {estado:"espera", tema:"ambar", ativo:false}, falhas = 0, conectado = false, redimensionado = false;
  const $ = id => document.getElementById(id);

  function ajustar() {
    const api = window.pywebview?.api;
    if (!api?.ajustar_indicador || redimensionado) return;
    // O bridge pode ficar disponível depois de o documento carregar.
    Promise.resolve(api.ajustar_indicador(LARGURA, ALTURA)).then(ok => {
      redimensionado = ok === true;
    }).catch(() => {});
  }

  function pintar() {
    document.body.dataset.tema = p.tema === "jarvis" ? "jarvis" : "ambar";
    document.body.dataset.cor = p.cor || "azul";
    document.body.dataset.estado = p.estado;
    document.body.dataset.alerta = p.alerta || p.humor || "normal";
    document.body.dataset.offline = String(falhas >= 3);
    const alerta = p.alerta === "risco" || p.alerta === "atencao";
    const parado = p.estado === "espera" || p.estado === "sentinela";
    const texto = falhas >= 3 ? "Sem conexão" : !conectado ? "Iniciando" : alerta && parado ? "Atenção" : ROTULOS[p.estado] || "Núcleo";
    if ($("estado").textContent !== texto) $("estado").textContent = texto;
    $("capsula").title = [texto, p.alerta_texto || "", p.legenda || "", "Arraste para mover. Detalhes na aplicação Núcleo."].filter(Boolean).join(" — ");
    $("b-falar").setAttribute("aria-pressed", String(!!p.ativo));
    ajustar();
  }

  async function atualizar() {
    try {
      const r = await fetch("/api/presenca", {credentials:"same-origin"});
      if (!r.ok) throw new Error("Presença indisponível");
      p = {...p, ...await r.json()}; falhas = 0; conectado = true;
    } catch (_) { falhas++; }
    pintar();
    setTimeout(atualizar, 1000);
  }

  async function comando(acao) {
    const api = window.pywebview?.api;
    try {
      if (api?.comando) await api.comando(acao);
      else if (acao === "abrir") window.open("/", "_blank", "noopener");
    } catch (_) { $("capsula").title = "Não foi possível executar o atalho. Abra o Núcleo pelo ícone da bandeja."; }
  }
  $("b-falar").addEventListener("click", e => {e.stopPropagation(); comando("conversa");});
  $("b-abrir").addEventListener("click", e => {e.stopPropagation(); comando("abrir");});
  $("identidade").addEventListener("dblclick", () => comando("abrir"));
  window.addEventListener("pywebviewready", ajustar);
  window.__widget = {definir(x) {p = {...p, ...x}; conectado = true; falhas = 0; pintar();}};
  pintar(); atualizar();
})();
