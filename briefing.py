"""
Briefing narrado ("bom dia"): monta um roteiro de falas, cada uma com o
cartão que aparece na tela enquanto ela é dita.

Tudo vem de dados reais já guardados no computador (resumo do dia, agenda,
financeiro, lembretes, atualizações, notícias resumidas pela IA local).
As frases são montadas por modelos de texto, não pela IA, para nunca
inventar números, datas ou nomes. A única consulta externa é o clima
(Open-Meteo, gratuito e sem chave), que recebe apenas as coordenadas da cidade.
"""
from __future__ import annotations

import re

import datetime as dt
import json
import time
import urllib.parse
import urllib.request

CLIMA_WMO = {0: "céu limpo", 1: "poucas nuvens", 2: "parcialmente nublado", 3: "nublado", 45: "neblina", 48: "neblina",
             51: "garoa fraca", 53: "garoa", 55: "garoa forte", 61: "chuva fraca", 63: "chuva", 65: "chuva forte",
             66: "chuva congelante", 67: "chuva congelante", 71: "neve fraca", 73: "neve", 75: "neve forte",
             80: "pancadas de chuva", 81: "pancadas de chuva", 82: "pancadas fortes", 95: "trovoadas",
             96: "trovoadas com granizo", 99: "trovoadas com granizo"}
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]

_cache_clima: dict = {}


def _num(v: float) -> str:
    return f"{v:.1f}".replace(".", ",").replace(",0", "")

BLOCOS_PADRAO = [
    {"id": "desde_ontem", "nome": "O que mudou desde ontem", "ativo": True},
    {"id": "clima", "nome": "Clima", "ativo": True},
    {"id": "agenda", "nome": "Agenda do dia", "ativo": True},
    {"id": "atencao", "nome": "E-mails que pedem atenção", "ativo": True},
    {"id": "compromissos", "nome": "Compromissos e promessas", "ativo": True},
    {"id": "financeiro", "nome": "Vencimentos do financeiro", "ativo": True},
    {"id": "lembretes", "nome": "Lembretes", "ativo": True},
    {"id": "sistema", "nome": "Atualizações do computador", "ativo": True},
    {"id": "noticias", "nome": "Notícias", "ativo": True},
    {"id": "fechamento", "nome": "Fechamento com o foco do dia", "ativo": True},
]


def locais_clima(cfg: dict) -> list[dict]:
    """Aceita o formato antigo (uma cidade) e o novo (lista de locais)."""
    c = cfg.get("clima", {})
    if c.get("locais"):
        return [l for l in c["locais"] if l.get("latitude") is not None and l.get("longitude") is not None]
    if c.get("latitude") is not None:
        return [{"cidade": c.get("cidade", ""), "latitude": c["latitude"], "longitude": c["longitude"],
                 "mostrar": ["hoje"]}]
    return []


def clima_local(cfg: dict, local: dict) -> dict | None:
    chave = (round(float(local["latitude"]), 3), round(float(local["longitude"]), 3))
    em_cache = _cache_clima.get(chave)
    if em_cache and time.time() - em_cache[0] < 1800:
        return {**em_cache[1], "cidade": local.get("cidade", "")}
    params = urllib.parse.urlencode({
        "latitude": local["latitude"], "longitude": local["longitude"], "timezone": cfg.get("fuso", "America/Sao_Paulo"),
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "forecast_days": 5})
    try:
        with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{params}", timeout=10) as r:
            d = json.loads(r.read())
        atual, dia = d["current"], d["daily"]
        dias = []
        for i, data in enumerate(dia["time"]):
            dias.append({"data": data, "minima": dia["temperature_2m_min"][i], "maxima": dia["temperature_2m_max"][i],
                         "chuva": (dia.get("precipitation_probability_max") or [None] * 9)[i],
                         "descricao": CLIMA_WMO.get(dia["weather_code"][i], "")})
        dados = {"agora": atual["temperature_2m"], "umidade": atual.get("relative_humidity_2m"),
                 "vento": atual.get("wind_speed_10m"), "minima": dias[0]["minima"], "maxima": dias[0]["maxima"],
                 "chuva": dias[0]["chuva"], "descricao": dias[0]["descricao"], "dias": dias}
        _cache_clima[chave] = (time.time(), dados)
        return {**dados, "cidade": local.get("cidade", "")}
    except Exception:
        return None


def clima(cfg: dict) -> dict | None:
    """Compatibilidade: clima do primeiro local."""
    locais = locais_clima(cfg)
    return clima_local(cfg, locais[0]) if locais else None


def frases_clima(c: dict, mostrar: list[str], detalhado: bool = True) -> str:
    partes = []
    if "agora" in mostrar:
        partes.append(f"agora faz {_num(c['agora'])} graus" + (f", {c['descricao']}" if c["descricao"] else ""))
    if "hoje" in mostrar or not mostrar:
        frase = f"a mínima hoje é de {_num(c['minima'])} e a máxima de {_num(c['maxima'])} graus"
        if c["chuva"] is not None and (detalhado or c["chuva"] >= 30):
            frase += f", com {c['chuva']}% de chance de chuva"
        partes.append(frase)
    dias = c.get("dias", [])
    if "amanha" in mostrar and len(dias) > 1:
        a = dias[1]
        frase = f"amanhã, entre {_num(a['minima'])} e {_num(a['maxima'])} graus"
        if a["chuva"] is not None:
            frase += f" e {a['chuva']}% de chance de chuva"
        partes.append(frase)
    if "semana" in mostrar and len(dias) > 2:
        prox = dias[1:5]
        chuvoso = max(prox, key=lambda d: d["chuva"] or 0)
        frase = (f"nos próximos dias, de {_num(min(d['minima'] for d in prox))} a "
                 f"{_num(max(d['maxima'] for d in prox))} graus")
        if (chuvoso["chuva"] or 0) >= 40:
            dia_sem = DIAS[dt.date.fromisoformat(chuvoso["data"]).weekday()].split("-")[0]
            frase += f", com maior chance de chuva na {dia_sem}" if dia_sem not in ("sábado", "domingo") \
                else f", com maior chance de chuva no {dia_sem}"
        partes.append(frase)
    texto = ("Em " + c["cidade"] + ", " if c["cidade"] else "") + "; ".join(partes)
    return texto[0].upper() + texto[1:] + "."


def montar_roteiro(app) -> dict:
    cfg = app.cfg
    b_cfg = cfg.get("briefing", {})
    curto = b_cfg.get("estilo", "completo") == "curto"
    agora = app.agora()
    hoje = agora.date()
    nome = cfg.get("nome", "")
    resumo = app.resumo_salvo() or {}
    gerado = resumo.get("gerado_em", "")
    tres = resumo.get("tres", []) if resumo else []
    seg: list[dict] = []

    def falar(fala: str, cartao: dict | None = None, nivel: str = "normal"):
        if fala.strip():
            seg.append({"fala": fala.strip(), "cartao": cartao, "nivel": nivel})

    def b_desde_ontem():
        saudacao = "Bom dia" if agora.hour < 12 else "Boa tarde" if agora.hour < 18 else "Boa noite"
        desde = (agora - dt.timedelta(days=1)).isoformat()
        novos_aprend = app.memoria.q("SELECT COUNT(*) n FROM conhecimento WHERE atualizado_em >= ?", (desde,))[0]["n"]
        artigos_novos = app.memoria.q("SELECT COUNT(*) n FROM artigos WHERE coletado_em >= ?", (desde,))[0]["n"]
        abertura = b_cfg.get("abertura", "").strip()
        falar(f"{saudacao}{', ' + nome if nome else ''}. Hoje é {DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]}. "
              + (abertura + " " if abertura else "") + ("" if curto else "Revisei o que mudou desde ontem."),
              {"tipo": "desde_ontem", "titulo": "Desde ontem",
               "itens": [f"Resumo atualizado às {gerado[11:16]}" if gerado else "Resumo ainda não gerado hoje",
                         f"{artigos_novos} notícia(s) nova(s) nas suas fontes",
                         f"{novos_aprend} aprendizado(s) novo(s)"]})

    def b_clima():
        for local in locais_clima(cfg):
            c = clima_local(cfg, local)
            if c:
                chuva = max([d.get("chuva") or 0 for d in c.get("dias", [])[:2]] + [c.get("chuva") or 0])
                falar(frases_clima(c, local.get("mostrar", ["hoje"]), not curto),
                      {"tipo": "clima", "titulo": c["cidade"] or "Clima", **c, "mostrar": local.get("mostrar", ["hoje"])},
                      "atencao" if chuva >= 70 else "normal")

    def b_agenda():
        comp = resumo.get("compromissos", []) if gerado[:10] == hoje.isoformat() else []
        if not comp:
            eventos, _ = app.eventos(hoje, hoje + dt.timedelta(days=1))
            comp = [{"hora": "dia todo" if e["dia_inteiro"] else f"{e['inicio']:%H:%M}", "titulo": e["titulo"]}
                    for e in eventos]
        if comp:
            primeiro = next((x for x in comp if x["hora"] != "dia todo"), comp[0])
            texto = f"Você tem {len(comp)} compromisso{'s' if len(comp) > 1 else ''} hoje. O primeiro é {primeiro['titulo']}, " + \
                ("o dia todo." if primeiro["hora"] == "dia todo" else f"às {primeiro['hora']}.")
            if not curto and len(comp) > 1:
                outros = [f"{x['titulo']} às {x['hora']}" for x in comp if x is not primeiro and x["hora"] != "dia todo"][:2]
                if outros:
                    texto += " Depois, " + " e ".join(outros) + "."
            falar(texto, {"tipo": "agenda", "titulo": "Agenda de hoje",
                          "itens": [{"hora": x["hora"], "texto": x["titulo"]} for x in comp[:6]]})
        else:
            falar("Sua agenda está livre hoje.", {"tipo": "agenda", "titulo": "Agenda livre", "itens": []})

    def b_atencao():
        emails = [t for t in tres if t.get("tipo") == "email"]
        resposta = resumo.get("resposta", [])
        if not (emails or resposta):
            if not curto:
                falar("Nenhum e-mail pede sua atenção agora.", None)
            return
        n = len(emails) + len(resposta)
        texto = f"{n} e-mail{'s' if n > 1 else ''} pede{'m' if n > 1 else ''} sua atenção. "
        maximo = 1 if curto else int(b_cfg.get("max_emails", 2))
        for i, e in enumerate(emails[:maximo]):
            texto += ("O principal: " if i == 0 else "Também: ") + f"{e['titulo']}, {e['porque']}. "
        falar(texto, {"tipo": "atencao", "titulo": "Pedem sua atenção",
                      "itens": [{"titulo": e["titulo"], "detalhe": e["porque"]} for e in emails] +
                               [{"titulo": f"{r['de']}: {r['assunto']}", "detalhe": r["conta"]} for r in resposta[:3]]})

    def b_compromissos():
        ps = getattr(app, "pessoas", None)
        if ps is None:
            return
        lista = ps.urgentes(hoje)
        if not lista:
            return
        meus = [c for c in lista if c["direcao"] == "eu_devo"]
        deles = [c for c in lista if c["direcao"] == "me_devem"]
        partes = []
        if meus:
            c = meus[0]
            atraso = c["prazo"] < hoje.isoformat()
            partes.append(f"Você prometeu a {c['pessoa_nome'] or c['pessoa']}: {c['texto']}" + (", e o prazo já passou" if atraso else ""))
        if deles:
            c = deles[0]
            partes.append(f"{c['pessoa_nome'] or c['pessoa']} ficou de: {c['texto']}")
        nivel = "risco" if any(c["prazo"] < hoje.isoformat() for c in meus) else "atencao" if meus else "normal"
        falar(". ".join(partes) + ".", {"tipo": "atencao", "titulo": "Compromissos",
                                        "itens": [{"titulo": c["texto"], "detalhe": ("você → " if c["direcao"] == "eu_devo" else "")
                                                   + (c["pessoa_nome"] or c["pessoa"] or "") + (" → você" if c["direcao"] == "me_devem" else "")
                                                   + f", prazo {c['prazo'][8:10]}/{c['prazo'][5:7]}"} for c in lista[:5]]}, nivel)

    def b_financeiro():
        contas = sorted(app.contas_urgentes(hoje), key=lambda x: -x[0])
        if not contas:
            return
        _, c1 = contas[0]
        texto = f"No financeiro, {c1['titulo'].replace('Pagar: ', 'a conta ').replace('Receber: ', 'o recebimento ')} {c1['porque']}"
        if len(contas) > 1:
            texto += f", e há mais {len(contas) - 1} conta{'s' if len(contas) > 2 else ''} nos próximos dias"
        p1 = contas[0][0]
        falar(texto + ".", {"tipo": "financeiro", "titulo": "Vencimentos",
                            "itens": [{"titulo": t["titulo"], "detalhe": f"{t['porque']}. {t['oque']}"} for _, t in contas[:4]]},
              "risco" if p1 >= 110 else "atencao" if p1 >= 88 else "normal")

    def b_lembretes():
        lembretes = app.memoria.lembretes_abertos(ate=hoje)
        if lembretes:
            resto = len(lembretes) - 1
            falar(f"Você pediu para lembrar: {lembretes[0]['texto']}" +
                  (f", e de mais {resto} coisa{'s' if resto > 1 else ''}" if resto else "") + ".",
                  {"tipo": "lembretes", "titulo": "Lembretes",
                   "itens": [{"titulo": l["texto"], "detalhe": l["hora"] or ""} for l in lembretes[:4]]})

    def b_sistema():
        at = json.loads(app.aprendizado.ler_estado("atualizacoes", "{}") or "{}")
        seg_win = [w for w in at.get("windows", []) if w.get("seguranca")]
        progs = at.get("programas", [])
        if seg_win or len(progs) >= 3:
            partes = []
            if seg_win:
                partes.append(f"{len(seg_win)} atualização{'ões' if len(seg_win) > 1 else ''} de segurança do Windows")
            if progs:
                partes.append(f"{len(progs)} programa{'s' if len(progs) > 1 else ''} para atualizar")
            falar("No computador, há " + " e ".join(partes) + ".",
                  {"tipo": "sistema", "titulo": "Atualizações", "_nivel": "atencao" if seg_win else "normal",
                   "itens": [{"titulo": w["titulo"], "detalhe": "segurança"} for w in seg_win[:2]] +
                            [{"titulo": p["nome"], "detalhe": f"{p['versao']} → {p['disponivel']}"} for p in progs[:3]]})

    def b_noticias():
        temas = b_cfg.get("temas_noticias", ["Segurança", "Microsoft 365", "Tecnologia", "Empreender", "Marketing"])
        maximo = 1 if curto else int(b_cfg.get("noticias", 3))
        escolhidas, usados = [], set()
        for tema in temas:
            if len(escolhidas) >= maximo:
                break
            l = app.memoria.q("""SELECT a.*, f.nome fonte, f.tema FROM artigos a JOIN fontes f ON f.id = a.fonte_id
                                 WHERE f.tema = ? AND a.resumo IS NOT NULL AND a.coletado_em >= ?
                                 ORDER BY COALESCE(a.publicado, a.coletado_em) DESC LIMIT 1""",
                              (tema, (agora - dt.timedelta(days=2)).isoformat()))
            if l and l[0]["id"] not in usados:
                usados.add(l[0]["id"])
                escolhidas.append(l[0])
        for a in escolhidas:
            primeira = (a["resumo"] or "").split(". ")[0].strip().rstrip(".")
            falar(f"Nas notícias de {a['tema'].lower()}: {primeira}." + ("" if curto else f" A informação é de {a['fonte']}."),
                  {"tipo": "noticia", "titulo": a["tema"], "manchete": a["titulo"], "resumo": a["resumo"],
                   "fonte": a["fonte"], "imagem": f"/api/imagem/{a['id']}" if a.get("imagem") else None})

    def b_fechamento():
        personalizado = b_cfg.get("fechamento", "").strip()
        if tres:
            foco = tres[0]["titulo"].replace("Pagar: ", "pagar ").replace("Receber: ", "confirmar ")
            falar(f"Hoje, mantenha o foco no essencial: {foco}." + (f" {personalizado}" if personalizado else ""), None)
        else:
            falar(personalizado or "Nada exige interromper sua manhã. Bom trabalho.", None)

    funcoes = {"desde_ontem": b_desde_ontem, "clima": b_clima, "agenda": b_agenda, "atencao": b_atencao,
               "financeiro": b_financeiro, "compromissos": b_compromissos, "lembretes": b_lembretes, "sistema": b_sistema, "noticias": b_noticias,
               "fechamento": b_fechamento}
    blocos = list(b_cfg.get("blocos") or BLOCOS_PADRAO)
    ids = {x.get("id") for x in blocos}
    for novo in BLOCOS_PADRAO:          # blocos criados em versões novas entram antes do fechamento
        if novo["id"] not in ids:
            pos = next((i for i, x in enumerate(blocos) if x.get("id") == "fechamento"), len(blocos))
            blocos.insert(pos, {"id": novo["id"], "ativo": True})
    for bloco in blocos:
        if bloco.get("ativo", True) and bloco.get("id") in funcoes:
            try:
                funcoes[bloco["id"]]()
            except Exception as erro:
                falar(f"Não consegui montar a parte de {bloco.get('nome', bloco['id']).lower()}.",
                      {"tipo": "desde_ontem", "titulo": "Aviso", "itens": [str(erro)[:160]]})
    if not seg:
        falar("Todos os blocos do briefing estão desligados. Ative algum em Ajustes.", None)
    seg = narracao_natural(app, seg, nome)
    return {"segmentos": seg, "gerado_em": agora.isoformat(), "resumo_de": gerado}


def narracao_natural(app, seg: list[dict], nome: str) -> list[dict]:
    """Reescreve as falas do roteiro como uma narração corrida e humana (uma IA escreve, os dados não mudam).
    Se não houver IA ou ela falhar, mantém as frases prontas."""
    if not seg or not app.cfg.get("briefing", {}).get("narracao_ia", True):
        return seg
    falas = [s["fala"] for s in seg]
    pedido = ("Reescreva cada fala abaixo como um trecho de um briefing matinal narrado em voz alta, em português do Brasil, "
              f"para {nome or 'o usuário'}: natural, caloroso, fluido, com transições entre os assuntos (como um apresentador "
              "pessoal), frases curtas, sem listas e sem emojis. Mantenha todos os fatos, números e nomes; não invente nada; "
              "não junte nem divida itens. Responda só com JSON: {\"falas\": [\"...\"]}, com exatamente "
              f"{len(falas)} itens, na mesma ordem.\n\n" + json.dumps(falas, ensure_ascii=False))
    texto = None
    try:
        import provedores
        n = app.nucleo
        if app.cfg.get("cerebro", {}).get("modo") == "claude" and provedores.chave("claude"):
            texto = _claude_texto(app, pedido)
        elif n._ia_ok():
            d = app.llm.json([{"role": "user", "content": pedido}], "Você escreve narrações de briefing.", max_tokens=1600)
            texto = json.dumps(d, ensure_ascii=False)
    except Exception:
        texto = None
    try:
        novas = json.loads(re.search(r"\{.*\}", texto or "", re.S).group(0))["falas"]
    except Exception:
        return seg
    if len(novas) != len(seg):
        return seg
    for s, f in zip(seg, novas):
        f = str(f).strip()
        if len(f) > 8:
            s["fala"] = f
    return seg


def _claude_texto(app, pedido: str) -> str:
    import provedores
    corpo = {"model": app.cfg.get("cerebro", {}).get("modelo_briefing", "claude-sonnet-5-5"), "max_tokens": 2000,
             "messages": [{"role": "user", "content": pedido}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(corpo).encode(),
                                 headers={"content-type": "application/json", "x-api-key": provedores.chave("claude"),
                                          "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.loads(r.read())
    return "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")


def buscar_cidade(nome: str) -> list[dict]:
    """Geocodificação gratuita do Open-Meteo: só o nome da cidade é enviado."""
    params = urllib.parse.urlencode({"name": nome, "count": 6, "language": "pt", "format": "json"})
    with urllib.request.urlopen(f"https://geocoding-api.open-meteo.com/v1/search?{params}", timeout=10) as r:
        d = json.loads(r.read())
    return [{"cidade": x["name"], "estado": x.get("admin1", ""), "pais": x.get("country", ""),
             "latitude": x["latitude"], "longitude": x["longitude"]} for x in d.get("results", [])]
