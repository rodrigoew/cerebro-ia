"""
Calculadora de finanças para empresas e projetos: VPL, TIR, payback, ponto de equilíbrio, parcela (tabela Price),
margem e markup. Tudo em reais e com taxas em % ao período.
"""
from __future__ import annotations


def _br(v: float) -> str:
    return ("-" if v < 0 else "") + "R$ " + f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _vpl(taxa: float, fluxos: list[float]) -> float:
    return sum(f / (1 + taxa) ** t for t, f in enumerate(fluxos))


def _tir(fluxos: list[float]) -> float | None:
    if not (any(f < 0 for f in fluxos) and any(f > 0 for f in fluxos)):
        return None
    baixo, alto = -0.9999, 10.0
    vb = _vpl(baixo, fluxos)
    for _ in range(300):                       # bisseção: robusta para fluxos convencionais
        meio = (baixo + alto) / 2
        vm = _vpl(meio, fluxos)
        if abs(vm) < 1e-7:
            break
        if (vm > 0) == (vb > 0):
            baixo, vb = meio, vm
        else:
            alto = meio
    return meio


def calcular(operacao: str, d: dict) -> str:
    op = (operacao or "").lower()
    try:
        if op in ("vpl", "tir", "payback"):
            fluxos = [float(x) for x in d.get("fluxos") or []]
            if len(fluxos) < 2:
                return "Informe os fluxos de caixa por período, começando pelo investimento negativo (ex.: [-10000, 3000, 4000, 5000])."
            taxa = float(d.get("taxa") or 0) / 100
            partes = []
            if op == "vpl" or d.get("tudo"):
                partes.append(f"VPL a {taxa * 100:g}% por período: {_br(_vpl(taxa, fluxos))}")
            tir = _tir(fluxos)
            partes.append(f"TIR: {tir * 100:.2f}% por período" if tir is not None else "TIR: não existe para esses fluxos")
            acum, pb = 0.0, None
            for t, f in enumerate(fluxos):
                anterior = acum
                acum += f
                if t and anterior < 0 <= acum:
                    pb = t - 1 + (-anterior / f)
                    break
            partes.append(f"Payback simples: {pb:.2f} períodos" if pb is not None else "Payback: o investimento não se paga nesse horizonte")
            if op == "vpl":
                partes.append("VPL positivo = o projeto rende mais que a taxa exigida" if _vpl(taxa, fluxos) > 0 else
                              "VPL negativo = rende menos que a taxa exigida")
            return "; ".join(partes) + "."
        if op in ("ponto_equilibrio", "equilibrio"):
            cf, preco, cv = float(d["custos_fixos"]), float(d["preco"]), float(d["custo_variavel"])
            mc = preco - cv
            if mc <= 0:
                return "Preço menor ou igual ao custo variável: não há ponto de equilíbrio (cada venda dá prejuízo)."
            q = cf / mc
            qtxt = f"{q:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return (f"Margem de contribuição: {_br(mc)} por unidade ({mc / preco:.1%}). Ponto de equilíbrio: {qtxt} unidades "
                    f"por período ({_br(q * preco)} de faturamento).")
        if op in ("parcela", "price", "financiamento"):
            pv, i, n = float(d["valor"]), float(d["taxa"]) / 100, int(d["periodos"])
            pmt = pv / n if i == 0 else pv * i / (1 - (1 + i) ** -n)
            return (f"Parcela (Price): {_br(pmt)} em {n} vezes a {i * 100:g}% por período; total pago {_br(pmt * n)}; "
                    f"juros {_br(pmt * n - pv)}.")
        if op in ("margem", "markup"):
            custo, preco = float(d.get("custo") or 0), float(d.get("preco") or 0)
            if op == "markup" and d.get("margem_desejada") not in (None, ""):
                m = float(d["margem_desejada"]) / 100
                p = custo / (1 - m)
                return f"Para margem de {m:.0%} sobre o preço, venda por {_br(p)} (markup de {(p / custo - 1):.1%} sobre o custo)."
            return f"Margem sobre o preço: {(preco - custo) / preco:.1%}; markup sobre o custo: {(preco - custo) / custo:.1%}; lucro bruto {_br(preco - custo)}."
        return "Operações: vpl, tir, payback, ponto_equilibrio, parcela, margem, markup."
    except (KeyError, ValueError, ZeroDivisionError) as erro:
        return f"Faltou ou veio inválido algum dado ({erro})."
