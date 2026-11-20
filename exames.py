"""
Histórico de exames de sangue (fica só no banco local do Núcleo).

  registrar(app, data, marcadores)   guarda os valores de um exame
  historico(app, marcador="")        última coleta comparada às faixas de referência + evolução de cada marcador

As faixas abaixo são referências gerais para adultos; cada laboratório tem as suas (vale a do laudo). Elas servem
para organizar e chamar atenção, não para diagnosticar: quem interpreta e decide é o médico.
"""
from __future__ import annotations

import re
import unicodedata

# nome canônico: (apelidos, unidade, mínimo, máximo, observação)  — referência geral para homem adulto
REFERENCIAS = {
    "hemoglobina": (["hb", "hgb"], "g/dL", 13.5, 17.5, ""),
    "hematocrito": (["ht", "hct", "hematócrito"], "%", 40, 50, "acima de 54% aumenta o risco de trombose: procurar o médico"),
    "hemacias": (["eritrocitos", "hemácias", "rbc"], "milhões/µL", 4.5, 5.9, ""),
    "leucocitos": (["leucócitos", "wbc", "glóbulos brancos"], "/µL", 4000, 11000, ""),
    "plaquetas": (["plt"], "/µL", 150000, 450000, ""),
    "glicemia": (["glicose", "glicemia de jejum"], "mg/dL", 70, 99, "100-125 = glicemia alterada; 126+ (confirmada) = diabetes"),
    "hba1c": (["hemoglobina glicada", "glicada", "a1c"], "%", 4.0, 5.6, "5,7-6,4 = pré-diabetes; 6,5+ = diabetes"),
    "colesterol total": (["ct", "colesterol"], "mg/dL", 0, 190, ""),
    "ldl": (["ldl colesterol", "ldl-c"], "mg/dL", 0, 130, "a meta depende do risco cardiovascular (pode ser bem menor)"),
    "hdl": (["hdl colesterol", "hdl-c"], "mg/dL", 40, 999, "anabolizantes costumam derrubar o HDL"),
    "triglicerides": (["triglicérides", "triglicerideos", "tg"], "mg/dL", 0, 150, ""),
    "tgo": (["ast", "aspartato aminotransferase"], "U/L", 0, 40, "treino pesado também eleva"),
    "tgp": (["alt", "alanina aminotransferase"], "U/L", 0, 41, "esteroides orais sobrecarregam o fígado"),
    "gama gt": (["ggt", "gama-gt", "gamaglutamiltransferase"], "U/L", 0, 60, ""),
    "bilirrubina total": (["bilirrubina"], "mg/dL", 0.2, 1.2, ""),
    "creatinina": (["creat"], "mg/dL", 0.7, 1.3, "pessoas muito musculosas têm creatinina mais alta; cistatina C ajuda a separar"),
    "ureia": (["uréia"], "mg/dL", 15, 45, "dieta rica em proteína eleva"),
    "cistatina c": (["cistatina"], "mg/L", 0.5, 1.0, ""),
    "ck": (["cpk", "creatinoquinase", "creatina quinase"], "U/L", 30, 200, "sobe muito após treino intenso; repetir em repouso"),
    "testosterona total": (["testosterona"], "ng/dL", 300, 1000, "com uso de anabolizante o valor reflete o que foi usado"),
    "testosterona livre": ([], "ng/dL", 5, 21, "faixa varia muito por método"),
    "estradiol": (["e2"], "pg/mL", 10, 40, ""),
    "lh": (["hormonio luteinizante"], "mUI/mL", 1.5, 9.3, "baixo/suprimido indica eixo hormonal parado"),
    "fsh": (["hormonio foliculo estimulante"], "mUI/mL", 1.5, 12.4, "suprimido afeta fertilidade"),
    "prolactina": ([], "ng/mL", 2, 18, ""),
    "shbg": ([], "nmol/L", 18, 54, ""),
    "psa total": (["psa"], "ng/mL", 0, 4.0, "a referência muda com a idade"),
    "tsh": ([], "mUI/L", 0.4, 4.5, ""),
    "t4 livre": (["t4l"], "ng/dL", 0.8, 1.8, ""),
    "ferritina": ([], "ng/mL", 30, 400, ""),
    "vitamina d": (["25 oh vitamina d", "25(oh)d", "vit d"], "ng/mL", 20, 100, "30-60 para grupos de risco"),
    "vitamina b12": (["b12"], "pg/mL", 200, 900, ""),
    "pcr ultrassensivel": (["pcr-us", "pcr us", "proteina c reativa"], "mg/L", 0, 1.0, "1-3 risco cardiovascular intermediário; >3 alto"),
    "acido urico": (["ácido úrico"], "mg/dL", 3.4, 7.0, ""),
    "sodio": (["na", "sódio"], "mEq/L", 135, 145, ""),
    "potassio": (["k", "potássio"], "mEq/L", 3.5, 5.1, ""),
}
CRITICOS = {"hematocrito": 54, "hemoglobina": 18.5, "tgp": 200, "tgo": 200, "potassio": 6.0, "glicemia": 250}


def _norm(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9()+ -]", " ", t)).strip()


def canonico(nome: str) -> str:
    n = _norm(nome)
    for chave, (apelidos, *_r) in REFERENCIAS.items():
        if n == _norm(chave) or n in (_norm(a) for a in apelidos):
            return chave
    return n


def _tabela(app) -> None:
    app.memoria.x("""CREATE TABLE IF NOT EXISTS exames (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, marcador TEXT,
                     valor REAL, unidade TEXT, ref_min REAL, ref_max REAL, laboratorio TEXT, criado_em TEXT)""")


def _num(v) -> float:
    return float(str(v).replace(".", "").replace(",", ".") if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", str(v)) else str(v).replace(",", "."))


def registrar(app, data: str, marcadores: list, laboratorio: str = "") -> str:
    _tabela(app)
    data = str(data or app.agora().date().isoformat())[:10]
    salvos, alertas = [], []
    for m in marcadores or []:
        try:
            nome = canonico(m.get("nome", ""))
            valor = _num(m.get("valor"))
        except Exception:
            continue
        ref = REFERENCIAS.get(nome)
        rmin = m.get("ref_min") if m.get("ref_min") not in (None, "") else (ref[2] if ref else None)
        rmax = m.get("ref_max") if m.get("ref_max") not in (None, "") else (ref[3] if ref else None)
        unidade = m.get("unidade") or (ref[1] if ref else "")
        app.memoria.x("DELETE FROM exames WHERE data = ? AND marcador = ?", (data, nome))
        app.memoria.x("""INSERT INTO exames(data, marcador, valor, unidade, ref_min, ref_max, laboratorio, criado_em)
                         VALUES(?,?,?,?,?,?,?,?)""", (data, nome, valor, unidade, rmin, rmax, laboratorio, app.agora().isoformat()))
        salvos.append(nome)
        if nome in CRITICOS and valor >= CRITICOS[nome]:
            alertas.append(f"{nome} {valor:g} {unidade}")
    msg = f"Guardei {len(salvos)} marcador(es) do exame de {data}."
    if alertas:
        msg += " PEDE ATENÇÃO MÉDICA LOGO: " + ", ".join(alertas) + "."
    return msg + "\n" + historico(app)


def historico(app, marcador: str = "") -> str:
    _tabela(app)
    if marcador:
        nome = canonico(marcador)
        linhas = app.memoria.q("SELECT * FROM exames WHERE marcador = ? ORDER BY data", (nome,))
        if not linhas:
            return f"Nenhum registro de {marcador}."
        serie = " → ".join(f"{x['valor']:g} ({x['data'][8:10]}/{x['data'][5:7]}/{x['data'][2:4]})" for x in linhas)
        ref = REFERENCIAS.get(nome)
        return (f"{nome} ({linhas[-1]['unidade']}): {serie}."
                + (f" Referência geral: {ref[2]:g}–{ref[3]:g}. {ref[4]}" if ref else ""))
    ultima = app.memoria.q("SELECT MAX(data) d FROM exames")[0]["d"]
    if not ultima:
        return "Nenhum exame registrado ainda."
    atual = app.memoria.q("SELECT * FROM exames WHERE data = ? ORDER BY marcador", (ultima,))
    fora, dentro = [], []
    for x in atual:
        anterior = app.memoria.q("SELECT valor, data FROM exames WHERE marcador = ? AND data < ? ORDER BY data DESC LIMIT 1",
                                 (x["marcador"], ultima))
        tend = ""
        if anterior:
            dif = x["valor"] - anterior[0]["valor"]
            tend = f" ({'↑' if dif > 0 else '↓' if dif < 0 else '='} de {anterior[0]['valor']:g})"
        txt = f"{x['marcador']} {x['valor']:g} {x['unidade']}{tend}"
        baixo = x["ref_min"] is not None and x["valor"] < x["ref_min"]
        alto = x["ref_max"] is not None and x["valor"] > x["ref_max"]
        if baixo or alto:
            obs = REFERENCIAS.get(x["marcador"], ("", "", 0, 0, ""))[4]
            fora.append(f"{txt} — {'abaixo' if baixo else 'acima'} da referência ({x['ref_min']:g}–{x['ref_max']:g})" + (f"; {obs}" if obs else ""))
        else:
            dentro.append(txt)
    return (f"Exame de {ultima[8:10]}/{ultima[5:7]}/{ultima[:4]}: {len(atual)} marcadores.\n"
            + ("Fora da referência: " + "; ".join(fora) + ".\n" if fora else "Todos dentro das referências gerais.\n")
            + ("Dentro: " + "; ".join(dentro) + "." if dentro else "")
            + "\n(Referências gerais; vale a do laudo. Interpretação final é do médico.)")
