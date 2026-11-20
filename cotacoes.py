"""
Cotações ao vivo para o Núcleo: moedas (AwesomeAPI), criptomoedas (CoinGecko) e ações/FIIs da B3 (brapi.dev).
Fontes públicas e gratuitas; a brapi pede um token grátis para a maioria dos papéis (cfg["brapi_token"]).
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
import urllib.request

MOEDAS = {"dolar": "USD", "usd": "USD", "euro": "EUR", "eur": "EUR", "libra": "GBP", "gbp": "GBP", "iene": "JPY",
          "peso argentino": "ARS", "peso": "ARS", "franco": "CHF", "dolar canadense": "CAD", "dolar australiano": "AUD",
          "yuan": "CNY", "dolar turismo": "USDT"}
CRIPTO = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum", "eth": "ethereum", "solana": "solana", "sol": "solana",
          "xrp": "ripple", "ripple": "ripple", "cardano": "cardano", "ada": "cardano", "dogecoin": "dogecoin", "doge": "dogecoin",
          "bnb": "binancecoin", "litecoin": "litecoin", "usdt": "tether", "tether": "tether"}


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def _get(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Nucleo)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _br(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def cotacao(pedido: str, cfg: dict | None = None) -> str:
    texto = _norm(pedido or "")
    moedas = sorted({cod for nome, cod in MOEDAS.items() if re.search(rf"\b{re.escape(nome)}\b", texto)} - {"USDT"})
    if "turismo" in texto:
        moedas = sorted(set(moedas) | {"USDT"})
    cripto = sorted({cid for nome, cid in CRIPTO.items() if re.search(rf"\b{re.escape(nome)}\b", texto)})
    acoes = sorted(set(re.findall(r"\b[A-Z]{4}\d{1,2}\b", (pedido or "").upper())))
    if "ibovespa" in texto or "bovespa" in texto:
        acoes.append("^BVSP")
    if not (moedas or cripto or acoes):
        moedas = ["USD", "EUR"]
    linhas = []
    if moedas:
        try:
            pares = ",".join(f"{m}-BRL" for m in moedas)
            dados = _get(f"https://economia.awesomeapi.com.br/json/last/{pares}")
            for v in dados.values():
                linhas.append(f"{v['name']}: R$ {_br(float(v['bid']), 4 if float(v['bid']) < 1 else 2)} "
                              f"(variação no dia {_br(float(v['pctChange']))}%, atualizado {v['create_date']})")
        except Exception as erro:
            linhas.append(f"Moedas: não consegui consultar agora ({type(erro).__name__}).")
    if cripto:
        try:
            dados = _get("https://api.coingecko.com/api/v3/simple/price?ids=" + ",".join(cripto)
                         + "&vs_currencies=brl,usd&include_24hr_change=true")
            for cid in cripto:
                v = dados.get(cid)
                if v:
                    linhas.append(f"{cid.capitalize()}: R$ {_br(v['brl'])} / US$ {_br(v['usd'])} "
                                  f"(24h: {_br(v.get('brl_24h_change') or 0)}%) — CoinGecko")
        except Exception as erro:
            linhas.append(f"Cripto: não consegui consultar agora ({type(erro).__name__}).")
    if acoes:
        token = (cfg or {}).get("brapi_token") or ""
        try:
            url = "https://brapi.dev/api/quote/" + ",".join(urllib.parse.quote(a) for a in acoes) + (f"?token={token}" if token else "")
            dados = _get(url)
            for v in dados.get("results", []):
                linhas.append(f"{v.get('symbol')} ({v.get('shortName') or ''}): R$ {_br(float(v.get('regularMarketPrice') or 0))} "
                              f"(dia {_br(float(v.get('regularMarketChangePercent') or 0))}%) — brapi")
        except Exception:
            linhas.append("Ações: a fonte gratuita (brapi.dev) não respondeu ou pede token para esses papéis "
                          "(dá para cadastrar um token grátis em Ajustes). Use a pesquisa na web para a cotação.")
    return "\n".join(linhas)


def link_rota(destino: str, origem: str = "", modo: str = "driving") -> str:
    modo = modo if modo in ("driving", "walking", "transit", "bicycling") else "driving"
    q = {"api": "1", "destination": destino, "travelmode": modo}
    if origem:
        q["origin"] = origem
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(q)
