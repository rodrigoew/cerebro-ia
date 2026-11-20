"""
Ferramentas de conhecimento verificável do Núcleo:

  wikipedia(consulta)      resumo da Wikipédia em português, com o link da fonte
  matematica(...)          matemática exata (sympy): resolver, derivar, integrar, simplificar, limite, avaliar
  converter(valor, de, para)  conversão de unidades (comprimento, massa, tempo, temperatura, velocidade, área,
                              volume, dados, energia, pressão)
  massa_molar(formula)     química: massa molar a partir da fórmula (ex.: H2SO4, Ca(OH)2, CuSO4·5H2O)
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Nucleo/1.0 (assistente pessoal; contato local)", "Accept": "application/json"}


# ------------------------------------------------------------------ Wikipédia
def _get(url: str, timeout: int = 8):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read())


def wikipedia(consulta: str, idioma: str = "pt") -> str:
    consulta = (consulta or "").strip()
    if not consulta:
        return "O que devo procurar na Wikipédia?"
    base = f"https://{idioma}.wikipedia.org"
    try:
        busca = _get(f"{base}/w/rest.php/v1/search/page?q={urllib.parse.quote(consulta)}&limit=3")
        paginas = busca.get("pages") or []
        if not paginas:
            return f"A Wikipédia não tem um artigo para “{consulta}”."
        saida = []
        for i, p in enumerate(paginas[:2]):
            chave = p.get("key") or p.get("title", "").replace(" ", "_")
            try:
                resumo = _get(f"{base}/api/rest_v1/page/summary/{urllib.parse.quote(chave)}")
            except Exception:
                resumo = {}
            texto = (resumo.get("extract") or re.sub(r"<[^>]+>", "", p.get("excerpt") or "")).strip()
            link = ((resumo.get("content_urls") or {}).get("desktop") or {}).get("page") or f"{base}/wiki/{urllib.parse.quote(chave)}"
            if texto:
                saida.append(f"{resumo.get('title') or p.get('title')}: {texto[:1500] if i == 0 else texto[:400]}\nFonte: {link}")
        return "\n\n".join(saida) or f"Não achei um resumo para “{consulta}”."
    except Exception as erro:
        return f"Não consegui consultar a Wikipédia agora ({type(erro).__name__}). Use a pesquisa na web."


# ------------------------------------------------------------------ matemática exata
def _sympy():
    try:
        import sympy
        return sympy
    except ImportError:
        return None


def _preparar(expr: str) -> str:
    e = str(expr or "")
    e = e.replace("^", "**").replace("×", "*").replace("÷", "/").replace("√", "sqrt").replace("π", "pi")
    e = re.sub(r"\bsen\b", "sin", e)
    e = re.sub(r"\btg\b", "tan", e)
    e = re.sub(r"\bln\b", "log", e)
    return e


def matematica(operacao: str, expressao: str, variavel: str = "x", ponto: str = "") -> str:
    sp = _sympy()
    if sp is None:
        return "A biblioteca de matemática (sympy) não está instalada; rode: pip install -r requirements.txt"
    op = (operacao or "").lower().strip()
    try:
        from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application, parse_expr,
                                                standard_transformations)
        trans = standard_transformations + (implicit_multiplication_application, convert_xor)
        x = sp.Symbol(variavel or "x")
        loc = {variavel or "x": x, "e": sp.E, "pi": sp.pi}

        def p(t):
            return parse_expr(_preparar(t), local_dict=loc, transformations=trans, evaluate=True)

        if op in ("resolver", "equacao", "equação", "raizes", "raízes"):
            partes = [s for s in re.split(r";|\n", expressao) if s.strip()]
            eqs = []
            for parte in partes:
                if "=" in parte:
                    esq, dir_ = parte.split("=", 1)
                    eqs.append(sp.Eq(p(esq), p(dir_)))
                else:
                    eqs.append(sp.Eq(p(parte), 0))
            simbolos = sorted(set().union(*[e.free_symbols for e in eqs]), key=lambda s: s.name)
            sol = sp.solve(eqs if len(eqs) > 1 else eqs[0], simbolos if len(eqs) > 1 else (x if x in simbolos else simbolos[0]), dict=len(eqs) > 1)
            aprox = ""
            try:
                if isinstance(sol, list) and sol and not isinstance(sol[0], dict):
                    aprox = " ≈ " + ", ".join(f"{complex(sp.N(s)).real:.6g}" if sp.im(sp.N(s)) == 0 else str(sp.N(s, 6)) for s in sol)
            except Exception:
                pass
            return f"Solução: {sol}{aprox}"
        if op in ("derivar", "derivada"):
            return f"d/d{x} [{expressao}] = {sp.simplify(sp.diff(p(expressao), x))}"
        if op in ("integrar", "integral"):
            if ponto and ":" in ponto:
                a, b = ponto.split(":", 1)
                r = sp.integrate(p(expressao), (x, p(a), p(b)))
                return f"∫ de {a} a {b} de {expressao} d{x} = {sp.simplify(r)} ≈ {sp.N(r, 8)}"
            return f"∫ {expressao} d{x} = {sp.integrate(p(expressao), x)} + C"
        if op in ("limite", "lim"):
            alvo = p(ponto or "0") if ponto not in ("oo", "inf", "infinito") else sp.oo
            return f"lim {x}→{ponto or 0} de {expressao} = {sp.limit(p(expressao), x, alvo)}"
        if op in ("fatorar",):
            return f"{sp.factor(p(expressao))}"
        if op in ("expandir",):
            return f"{sp.expand(p(expressao))}"
        if op in ("simplificar",):
            return f"{sp.simplify(p(expressao))}"
        if op in ("avaliar", "calcular", "valor"):
            v = p(expressao)
            return f"{expressao} = {sp.nsimplify(v) if v.is_rational else v} ≈ {sp.N(v, 12)}"
        return "Operação não reconhecida. Use: resolver, derivar, integrar, limite, fatorar, expandir, simplificar ou avaliar."
    except Exception as erro:
        return f"Não consegui processar a expressão ({type(erro).__name__}: {str(erro)[:120]}). Escreva como 2*x^2 + 3*x - 5 = 0."


# ------------------------------------------------------------------ unidades
_UNID = {
    # comprimento (metro)
    "mm": ("comprimento", 1e-3), "cm": ("comprimento", 1e-2), "m": ("comprimento", 1), "km": ("comprimento", 1e3),
    "pol": ("comprimento", 0.0254), "polegada": ("comprimento", 0.0254), "in": ("comprimento", 0.0254),
    "pe": ("comprimento", 0.3048), "pé": ("comprimento", 0.3048), "ft": ("comprimento", 0.3048), "jarda": ("comprimento", 0.9144),
    "milha": ("comprimento", 1609.344), "mi": ("comprimento", 1609.344), "milha nautica": ("comprimento", 1852),
    # massa (kg)
    "mg": ("massa", 1e-6), "g": ("massa", 1e-3), "kg": ("massa", 1), "t": ("massa", 1000), "tonelada": ("massa", 1000),
    "lb": ("massa", 0.45359237), "libra": ("massa", 0.45359237), "oz": ("massa", 0.028349523125), "onca": ("massa", 0.028349523125),
    # tempo (s)
    "ms": ("tempo", 1e-3), "s": ("tempo", 1), "min": ("tempo", 60), "h": ("tempo", 3600), "dia": ("tempo", 86400),
    "semana": ("tempo", 604800), "ano": ("tempo", 31557600),
    # velocidade (m/s)
    "m/s": ("velocidade", 1), "km/h": ("velocidade", 1 / 3.6), "mph": ("velocidade", 0.44704), "no": ("velocidade", 1852 / 3600),
    "nó": ("velocidade", 1852 / 3600),
    # área (m²)
    "m2": ("area", 1), "m²": ("area", 1), "km2": ("area", 1e6), "km²": ("area", 1e6), "cm2": ("area", 1e-4), "ha": ("area", 1e4),
    "hectare": ("area", 1e4), "alqueire mineiro": ("area", 48400), "acre": ("area", 4046.8564224),
    # volume (litro)
    "ml": ("volume", 1e-3), "l": ("volume", 1), "litro": ("volume", 1), "m3": ("volume", 1000), "m³": ("volume", 1000),
    "galao": ("volume", 3.785411784), "galão": ("volume", 3.785411784), "cm3": ("volume", 1e-3), "cc": ("volume", 1e-3),
    # dados (byte)
    "b": ("dados", 1), "byte": ("dados", 1), "kb": ("dados", 1e3), "mb": ("dados", 1e6), "gb": ("dados", 1e9), "tb": ("dados", 1e12),
    "kib": ("dados", 1024), "mib": ("dados", 1024 ** 2), "gib": ("dados", 1024 ** 3), "tib": ("dados", 1024 ** 4),
    # energia (joule)
    "j": ("energia", 1), "kj": ("energia", 1e3), "cal": ("energia", 4.184), "kcal": ("energia", 4184), "wh": ("energia", 3600),
    "kwh": ("energia", 3.6e6),
    # potência (watt)
    "w": ("potencia", 1), "kw": ("potencia", 1e3), "cv": ("potencia", 735.49875), "hp": ("potencia", 745.6998716),
    # pressão (pascal)
    "pa": ("pressao", 1), "kpa": ("pressao", 1e3), "bar": ("pressao", 1e5), "psi": ("pressao", 6894.757293168), "atm": ("pressao", 101325),
}


def converter(valor: float, de: str, para: str) -> str:
    a, b = (de or "").strip().lower(), (para or "").strip().lower()
    temps = {"c": "c", "°c": "c", "celsius": "c", "f": "f", "°f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}
    if a in temps and b in temps:
        c = {"c": lambda v: v, "f": lambda v: (v - 32) * 5 / 9, "k": lambda v: v - 273.15}[temps[a]](float(valor))
        r = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[temps[b]]
        return f"{valor} {de} = {r:.4g} {para}"
    if a not in _UNID or b not in _UNID:
        return "Unidade desconhecida. Exemplos: km, milha, kg, lb, km/h, mph, l, galão, GB, GiB, kWh, cv, hp, psi, bar, °C, °F."
    if _UNID[a][0] != _UNID[b][0]:
        return f"Não dá para converter {_UNID[a][0]} em {_UNID[b][0]}."
    r = float(valor) * _UNID[a][1] / _UNID[b][1]
    return f"{valor} {de} = {r:.6g} {para}"


# ------------------------------------------------------------------ química
MASSAS = {  # massas atômicas padrão (IUPAC, arredondadas)
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998,
    "Ne": 20.180, "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45, "Ar": 39.948,
    "K": 39.098, "Ca": 40.078, "Sc": 44.956, "Ti": 47.867, "V": 50.942, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845,
    "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ga": 69.723, "Ge": 72.630, "As": 74.922, "Se": 78.971,
    "Br": 79.904, "Kr": 83.798, "Rb": 85.468, "Sr": 87.62, "Y": 88.906, "Zr": 91.224, "Nb": 92.906, "Mo": 95.95,
    "Ru": 101.07, "Rh": 102.91, "Pd": 106.42, "Ag": 107.87, "Cd": 112.41, "In": 114.82, "Sn": 118.71, "Sb": 121.76,
    "Te": 127.60, "I": 126.90, "Xe": 131.29, "Cs": 132.91, "Ba": 137.33, "La": 138.91, "Ce": 140.12, "Nd": 144.24,
    "W": 183.84, "Pt": 195.08, "Au": 196.97, "Hg": 200.59, "Pb": 207.2, "Bi": 208.98, "Rn": 222.0, "Ra": 226.0,
    "U": 238.03, "Pu": 244.0,
}


def massa_molar(formula: str) -> str:
    f = (formula or "").replace(" ", "").replace("·", ".").replace("•", ".").replace("*", ".")

    def contar(trecho: str) -> dict:
        pilha = [{}]
        i = 0
        while i < len(trecho):
            ch = trecho[i]
            if ch in "([":
                pilha.append({}); i += 1
            elif ch in ")]":
                i += 1
                m = re.match(r"\d+", trecho[i:]); n = int(m.group()) if m else 1; i += len(m.group()) if m else 0
                topo = pilha.pop()
                for k, v in topo.items():
                    pilha[-1][k] = pilha[-1].get(k, 0) + v * n
            else:
                m = re.match(r"([A-Z][a-z]?)(\d*)", trecho[i:])
                if not m:
                    raise ValueError(f"não entendi “{trecho[i:]}”")
                el, n = m.group(1), int(m.group(2) or 1)
                if el not in MASSAS:
                    raise ValueError(f"elemento desconhecido: {el}")
                pilha[-1][el] = pilha[-1].get(el, 0) + n
                i += len(m.group())
        return pilha[0]
    try:
        total_el: dict = {}
        for parte in f.split("."):
            m = re.match(r"(\d+)(.*)", parte)
            mult, corpo = (int(m.group(1)), m.group(2)) if m else (1, parte)
            for k, v in contar(corpo).items():
                total_el[k] = total_el.get(k, 0) + v * mult
        massa = sum(MASSAS[k] * v for k, v in total_el.items())
        detalhe = " + ".join(f"{k}{v if v > 1 else ''} ({MASSAS[k] * v:.3f})" for k, v in total_el.items())
        return f"Massa molar de {formula} = {massa:.3f} g/mol  [{detalhe}]"
    except Exception as erro:
        return f"Não consegui ler a fórmula ({erro}). Use maiúsculas certas: H2SO4, Ca(OH)2, CuSO4·5H2O."
