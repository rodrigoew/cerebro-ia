"""
Day trade com disciplina: plano de risco, dimensionamento de posição e diário de operações com estatísticas.

O Núcleo NÃO envia ordens à corretora. Ele ajuda a planejar, registrar, medir e parar na hora certa:
  plano(app, dados)            lê ou ajusta o plano (capital, risco por operação, limite de perda diário, meta)
  dimensionar(...)             quantos contratos/ações operar para respeitar o risco
  registrar(app, operacao)     grava uma operação no diário e avisa se o limite do dia foi atingido
  desempenho(app, dias)        taxa de acerto, payoff, expectativa, drawdown, resultado por setup, IR estimado
"""
from __future__ import annotations

import datetime as dt
import math

# valor financeiro de 1 ponto por contrato e variação mínima (B3)
CONTRATOS = {
    "WIN": {"nome": "Mini Ibovespa", "ponto": 0.20, "tick": 5.0},
    "WDO": {"nome": "Mini dólar", "ponto": 10.0, "tick": 0.5},
    "IND": {"nome": "Ibovespa cheio", "ponto": 1.00, "tick": 5.0},
    "DOL": {"nome": "Dólar cheio", "ponto": 50.0, "tick": 0.5},
}
PLANO_PADRAO = {"capital": 0.0, "risco_pct": 1.0, "perda_diaria_pct": 3.0, "meta_diaria_pct": 0.0, "max_operacoes_dia": 5,
                "custo_por_contrato": 0.0}


def _br(v: float) -> str:
    return ("-" if v < 0 else "") + "R$ " + f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ativo(codigo: str) -> tuple[str, dict | None]:
    c = (codigo or "").upper().strip()
    raiz = c[:3]
    return c, CONTRATOS.get(raiz)


def _tabela(app) -> None:
    app.memoria.x("""CREATE TABLE IF NOT EXISTS trade_operacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ativo TEXT, lado TEXT, quantidade REAL, entrada REAL, saida REAL,
        stop REAL, resultado REAL, custos REAL, setup TEXT, nota TEXT, criado_em TEXT)""")


def plano(app, dados: dict | None = None) -> str:
    p = {**PLANO_PADRAO, **app.cfg.get("trade", {})}
    if dados:
        for k in PLANO_PADRAO:
            if dados.get(k) not in (None, ""):
                p[k] = float(dados[k])
        app.cfg["trade"] = p
        try:
            app.salvar_config()
        except Exception:
            pass
    if not p["capital"]:
        return ("Ainda não há plano de trade. Pergunte ao usuário: capital destinado ao trade, risco por operação "
                "(sugestão comum: 0,5% a 1%), limite de perda diário (ex.: 2% a 3%) e máximo de operações por dia.")
    return (f"Plano: capital {_br(p['capital'])}; risco por operação {p['risco_pct']:g}% ({_br(p['capital'] * p['risco_pct'] / 100)}); "
            f"limite de perda diário {p['perda_diaria_pct']:g}% ({_br(p['capital'] * p['perda_diaria_pct'] / 100)}); "
            + (f"meta diária {p['meta_diaria_pct']:g}%; " if p["meta_diaria_pct"] else "")
            + f"máximo de {int(p['max_operacoes_dia'])} operações por dia; custo por contrato {_br(p['custo_por_contrato'])}.")


def dimensionar(app, ativo: str, stop: float, capital: float = 0, risco_pct: float = 0, preco: float = 0) -> str:
    p = {**PLANO_PADRAO, **app.cfg.get("trade", {})}
    capital = float(capital or p["capital"] or 0)
    risco_pct = float(risco_pct or p["risco_pct"] or 1)
    if capital <= 0:
        return "Preciso do capital (ou de um plano de trade) para dimensionar."
    risco_rs = capital * risco_pct / 100
    codigo, ct = _ativo(ativo)
    stop = abs(float(stop))
    if ct:
        if stop <= 0:
            return "Informe a distância do stop em pontos."
        perda_por_contrato = stop * ct["ponto"] + p["custo_por_contrato"]
        n = math.floor(risco_rs / perda_por_contrato)
        if n < 1:
            return (f"Com {_br(capital)} e risco de {risco_pct:g}% ({_br(risco_rs)}), um stop de {stop:g} pontos no {ct['nome']} "
                    f"custa {_br(perda_por_contrato)} por contrato: maior que o risco permitido. Diminua o stop ou não opere.")
        return (f"{ct['nome']} ({codigo}): stop de {stop:g} pontos = {_br(stop * ct['ponto'])} por contrato. Risco permitido "
                f"{_br(risco_rs)} ({risco_pct:g}% de {_br(capital)}) → até {n} contrato(s); perda máxima se o stop for atingido: "
                f"{_br(n * perda_por_contrato)}. Cada ponto vale {_br(n * ct['ponto'])} nessa posição.")
    # ações: stop em reais por ação
    if stop <= 0:
        return "Para ações, informe a distância do stop em reais por ação."
    qtd = math.floor(risco_rs / stop)
    if preco:
        qtd = min(qtd, math.floor(capital / float(preco)))
    lote = qtd if qtd < 100 else qtd - qtd % 100
    return (f"{codigo or 'Ação'}: stop de {_br(stop)} por ação; risco permitido {_br(risco_rs)} → até {qtd} ações "
            f"(em lote-padrão: {lote}); perda máxima {_br(qtd * stop)}" + (f"; capital usado {_br(qtd * float(preco))}." if preco else "."))


def _resultado(ativo: str, lado: str, qtd: float, entrada: float, saida: float) -> float:
    _, ct = _ativo(ativo)
    sinal = 1 if lado.startswith("c") else -1          # compra ganha na alta; venda ganha na queda
    pontos = (saida - entrada) * sinal
    return pontos * qtd * (ct["ponto"] if ct else 1)


def registrar(app, op: dict) -> str:
    _tabela(app)
    p = {**PLANO_PADRAO, **app.cfg.get("trade", {})}
    ativo = str(op.get("ativo") or "").upper().strip()
    lado = "compra" if str(op.get("lado") or "compra").lower().startswith(("c", "l")) else "venda"
    qtd, entrada, saida = float(op.get("quantidade") or 1), float(op["entrada"]), float(op["saida"])
    data = str(op.get("data") or app.agora().date().isoformat())[:10]
    custos = float(op.get("custos") if op.get("custos") not in (None, "") else p["custo_por_contrato"] * qtd * 2)
    bruto = _resultado(ativo, lado, qtd, entrada, saida)
    liquido = bruto - custos
    app.memoria.x("""INSERT INTO trade_operacoes(data, ativo, lado, quantidade, entrada, saida, stop, resultado, custos, setup, nota,
                     criado_em) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data, ativo, lado, qtd, entrada, saida, op.get("stop"), liquido, custos, str(op.get("setup") or "")[:60],
                   str(op.get("nota") or "")[:300], app.agora().isoformat()))
    dia = app.memoria.q("SELECT COUNT(*) n, COALESCE(SUM(resultado),0) r FROM trade_operacoes WHERE data = ?", (data,))[0]
    msg = f"Registrado: {lado} {qtd:g} {ativo} de {entrada:g} a {saida:g} → {_br(liquido)}" + (f" (custos {_br(custos)})" if custos else "") + \
          f". No dia: {dia['n']} operação(ões), {_br(dia['r'])}."
    if p["capital"]:
        limite = p["capital"] * p["perda_diaria_pct"] / 100
        if dia["r"] <= -limite:
            msg += f" ATENÇÃO: limite de perda diário ({_br(limite)}) atingido. Pelo plano, PARE por hoje."
        elif dia["r"] <= -0.7 * limite:
            msg += f" Perto do limite de perda diário ({_br(limite)}): reduza a mão ou pare."
        if p["meta_diaria_pct"] and dia["r"] >= p["capital"] * p["meta_diaria_pct"] / 100:
            msg += " Meta diária batida: considere encerrar o dia e proteger o resultado."
        if dia["n"] >= p["max_operacoes_dia"]:
            msg += f" Máximo de {int(p['max_operacoes_dia'])} operações do dia atingido."
    return msg


def desempenho(app, dias: int = 30) -> str:
    _tabela(app)
    desde = (app.agora().date() - dt.timedelta(days=max(1, int(dias)))).isoformat()
    ops = app.memoria.q("SELECT * FROM trade_operacoes WHERE data >= ? ORDER BY data, id", (desde,))
    if not ops:
        return f"Nenhuma operação registrada nos últimos {dias} dias."
    res = [o["resultado"] for o in ops]
    ganhos, perdas = [r for r in res if r > 0], [r for r in res if r < 0]
    total = sum(res)
    acerto = len(ganhos) / len(res)
    media_g = sum(ganhos) / len(ganhos) if ganhos else 0.0
    media_p = -sum(perdas) / len(perdas) if perdas else 0.0
    payoff = media_g / media_p if media_p else float("inf")
    expect = total / len(res)
    fator = sum(ganhos) / -sum(perdas) if perdas else float("inf")
    pico = acum = dd = 0.0
    seq = pior_seq = 0
    for r in res:
        acum += r
        pico = max(pico, acum)
        dd = min(dd, acum - pico)
        seq = seq + 1 if r < 0 else 0
        pior_seq = max(pior_seq, seq)
    por_setup: dict = {}
    for o in ops:
        s = o["setup"] or "sem setup"
        a = por_setup.setdefault(s, [0, 0.0, 0])
        a[0] += 1; a[1] += o["resultado"]; a[2] += o["resultado"] > 0
    dias_op = {}
    for o in ops:
        dias_op[o["data"]] = dias_op.get(o["data"], 0) + o["resultado"]
    # IR de day trade: 20% sobre o lucro líquido do mês (prejuízo do mês reduz; compensação de meses anteriores fica fora desta estimativa)
    mes = app.agora().strftime("%Y-%m")
    lucro_mes = sum(o["resultado"] for o in ops if o["data"].startswith(mes))
    linhas = [
        f"Últimos {dias} dias: {len(res)} operações em {len(dias_op)} dia(s); resultado líquido {_br(total)}.",
        f"Taxa de acerto {acerto:.0%}; ganho médio {_br(media_g)}; perda média {_br(media_p)}; payoff {payoff:.2f}; "
        f"fator de lucro {fator:.2f}; expectativa por operação {_br(expect)}.",
        f"Maior rebaixamento (drawdown) {_br(dd)}; pior sequência de perdas: {pior_seq}. Dias positivos: "
        f"{sum(1 for v in dias_op.values() if v > 0)} de {len(dias_op)}.",
        "Por setup: " + "; ".join(f"{s}: {a[0]} ops, {_br(a[1])}, acerto {a[2] / a[0]:.0%}" for s, a in
                                   sorted(por_setup.items(), key=lambda x: -x[1][1])),
    ]
    if lucro_mes > 0:
        linhas.append(f"IR estimado do day trade neste mês: {_br(lucro_mes * 0.20)} (20% de {_br(lucro_mes)}; DARF código 6015 até o "
                      "último dia útil do mês seguinte; descontar o 1% retido na fonte e prejuízos anteriores).")
    if expect < 0:
        linhas.append("Expectativa negativa: do jeito atual, quanto mais operar, mais tende a perder. Reveja setups, stops e horários antes de continuar.")
    return "\n".join(linhas)
