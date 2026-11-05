"""
Provedores de IA na nuvem, usados só quando você aprova um envio.

  claude   API da Anthropic (padrão). Único com pesquisa na web integrada.
  openai   qualquer endpoint compatível com OpenAI: a própria OpenAI (GPT),
           OpenRouter, LM Studio, um roteador local (como o FreeLLMAPI, para
           uso pessoal) etc. Configure endereço, modelo e chave em Ajustes.

As mesmas regras valem para todos: prévia do que sai, dados sensíveis
mascarados e confirmação com clique.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SERVICO = "resumo-da-manha"


def _keyring():
    import keyring
    return keyring


def chave(provedor: str) -> str | None:
    env = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(provedor)
    if env and os.environ.get(env):
        return os.environ[env]
    try:
        nome = "anthropic-api-key" if provedor == "claude" else f"nuvem:{provedor}"
        return _keyring().get_password(SERVICO, nome)
    except Exception:
        return None


def salvar_chave(provedor: str, valor: str) -> None:
    valor = valor.strip()
    if not valor:
        raise ValueError("Chave vazia.")
    nome = "anthropic-api-key" if provedor == "claude" else f"nuvem:{provedor}"
    _keyring().set_password(SERVICO, nome, valor)


def ativo(cfg: dict, papel: str = "aprofundar") -> dict:
    """papel "auto": respostas automáticas (ex.: FreeLLMAPI, grátis).
       papel "aprofundar": quando você clica em Aprofundar, com prévia (ex.: Claude, com o crédito do plano Max)."""
    n = cfg.get("nuvem", {})
    if papel == "auto":
        provedor = n.get("provedor_auto") or n.get("provedor", "claude")
    else:
        provedor = n.get("provedor_aprofundar") or n.get("provedor", "claude")
    if provedor == "openai":
        return {"provedor": "openai", "rotulo": n.get("rotulo") or "Provedor compatível com OpenAI",
                "modelo": n.get("modelo_openai", "gpt-4o-mini"), "url": n.get("url_openai", "https://api.openai.com/v1"),
                "web": False, "chave": bool(chave("openai")) or "localhost" in n.get("url_openai", "") or
                "127.0.0.1" in n.get("url_openai", "")}
    return {"provedor": "claude", "rotulo": "Claude", "modelo": cfg.get("claude_api", {}).get("modelo", "claude-sonnet-5-5"),
            "url": "https://api.anthropic.com", "web": True, "chave": bool(chave("claude"))}


def _erro_amigavel(codigo: int, detalhe: str, rotulo: str) -> str:
    if codigo == 401:
        return f"A chave do {rotulo} é inválida. Atualize em Ajustes > Nuvem."
    if codigo == 403:
        return f"A chave do {rotulo} não tem permissão para esse modelo."
    if codigo == 429:
        return f"Limite de uso do {rotulo} atingido. Tente de novo em alguns minutos."
    if codigo == 404 and "model" in detalhe.lower():
        return "Modelo não encontrado. Ajuste o modelo em Ajustes > Nuvem."
    if codigo == 400 and "credit" in detalhe.lower():
        return f"Sem crédito na conta do {rotulo}."
    return f"O {rotulo} recusou o pedido ({codigo})."


def enviar(cfg: dict, sistema: str, conteudo: str, web: bool = False, papel: str = "aprofundar") -> str:
    p = ativo(cfg, papel)
    if p["provedor"] == "claude":
        k = chave("claude")
        if not k:
            raise PermissionError("Chave do Claude não configurada (Ajustes > Nuvem).")
        pedido = {"model": p["modelo"], "max_tokens": 1200, "system": sistema,
                  "messages": [{"role": "user", "content": conteudo}]}
        if web:
            pedido["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(pedido).encode(),
                                     headers={"content-type": "application/json", "x-api-key": k,
                                              "anthropic-version": "2023-06-01"})
        dados = _chamar(req, p["rotulo"])
        return "".join(b.get("text", "") for b in dados.get("content", []) if b.get("type") == "text")
    k = chave("openai") or "sem-chave"
    pedido = {"model": p["modelo"], "max_tokens": 1200,
              "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": conteudo}]}
    req = urllib.request.Request(p["url"].rstrip("/") + "/chat/completions", data=json.dumps(pedido).encode(),
                                 headers={"content-type": "application/json", "authorization": f"Bearer {k}"})
    dados = _chamar(req, p["rotulo"])
    escolhas = dados.get("choices") or [{}]
    return (escolhas[0].get("message") or {}).get("content", "") or ""


def _chamar(req, rotulo: str) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as erro:
        raise RuntimeError(_erro_amigavel(erro.code, erro.read().decode(errors="replace")[:300], rotulo))
    except urllib.error.URLError:
        raise RuntimeError(f"Sem conexão com o {rotulo}. A memória local segue funcionando.")


def testar(cfg: dict, papel: str = "auto") -> dict:
    """Confere se o provedor responde."""
    p = ativo(cfg, papel)
    if p["provedor"] != "openai":
        return {"ok": bool(chave("claude")), "mensagem": "Claude: chave guardada." if chave("claude") else "Claude: falta a chave."}
    k = chave("openai")
    req = urllib.request.Request(p["url"].rstrip("/") + "/models",
                                 headers={"authorization": f"Bearer {k}"} if k else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            dados = json.loads(r.read())
        n = len(dados.get("data", []))
        return {"ok": True, "mensagem": f"{p['rotulo']} respondeu: {n} modelo(s) disponível(is)."}
    except urllib.error.HTTPError as erro:
        return {"ok": False, "mensagem": _erro_amigavel(erro.code, "", p["rotulo"])}
    except Exception:
        return {"ok": False, "mensagem": f"{p['rotulo']} não respondeu em {p['url']}."}


def enviar_fluxo(cfg: dict, sistema: str, conteudo: str, papel: str = "auto"):
    """Como enviar(), mas devolve a resposta aos pedaços (OpenAI-compatível via SSE; Claude por inteiro)."""
    p = ativo(cfg, papel)
    if p["provedor"] == "claude":
        yield enviar(cfg, sistema, conteudo, papel=papel)
        return
    k = chave("openai") or "sem-chave"
    pedido = {"model": p["modelo"], "max_tokens": 1200, "stream": True,
              "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": conteudo}]}
    req = urllib.request.Request(p["url"].rstrip("/") + "/chat/completions", data=json.dumps(pedido).encode(),
                                 headers={"content-type": "application/json", "authorization": f"Bearer {k}",
                                          "accept": "text/event-stream"})
    try:
        resposta = urllib.request.urlopen(req, timeout=90)
    except urllib.error.HTTPError as erro:
        raise RuntimeError(_erro_amigavel(erro.code, erro.read().decode(errors="replace")[:300], p["rotulo"]))
    except urllib.error.URLError:
        raise RuntimeError(f"Sem conexão com o {p['rotulo']}.")
    with resposta:
        tipo = resposta.headers.get("content-type", "")
        if "event-stream" not in tipo:          # servidor ignorou o stream: resposta inteira
            dados = json.loads(resposta.read())
            yield ((dados.get("choices") or [{}])[0].get("message") or {}).get("content", "") or ""
            return
        for linha in resposta:
            linha = linha.decode("utf-8", errors="replace").strip()
            if not linha.startswith("data:"):
                continue
            carga = linha[5:].strip()
            if carga == "[DONE]":
                break
            try:
                pedaco = ((json.loads(carga).get("choices") or [{}])[0].get("delta") or {}).get("content")
            except json.JSONDecodeError:
                continue
            if pedaco:
                yield pedaco
