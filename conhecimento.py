"""
Pacotes de conhecimento do Núcleo (pasta conhecimento/*.md).

Cada arquivo é um tema; cada "## seção" é um trecho. A ferramenta consultar_conhecimento devolve as seções mais
relevantes para a pergunta. Você pode criar seus próprios pacotes: basta salvar um .md nessa pasta.
"""
from __future__ import annotations

import pathlib
import re
import unicodedata

PASTA = pathlib.Path(__file__).resolve().parent / "conhecimento"
_CACHE: dict = {}
VAZIAS = set("""que com para por uma uns umas como qual quais quem onde quando sobre isso isto esse essa este esta meu minha meus
minhas seu sua seus suas dos das nos nas pelo pela mais menos muito muita tem ter sao foi ser esta estao fazer faco devo posso
pode qual vale sim nao voce voces ele ela eles elas aqui ali hoje agora ainda tambem entre ate sem the and""".split())


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def _carregar() -> dict:
    if not PASTA.exists():
        return {}
    assinatura = tuple(sorted((p.name, p.stat().st_mtime) for p in PASTA.glob("*.md")))
    if _CACHE.get("assinatura") == assinatura:
        return _CACHE["temas"]
    temas = {}
    for arq in sorted(PASTA.glob("*.md")):
        texto = arq.read_text(encoding="utf-8")
        titulo = (re.search(r"^#\s+(.+)", texto, re.M) or [None, arq.stem])[1].strip()
        partes = re.split(r"(?m)^##\s+", texto)
        intro, secoes = partes[0], []
        for bloco in partes[1:]:
            nome, _, corpo = bloco.partition("\n")
            secoes.append({"nome": nome.strip(), "texto": corpo.strip()})
        temas[arq.stem] = {"titulo": titulo, "intro": re.sub(r"^#.*\n", "", intro).strip(), "secoes": secoes}
    _CACHE.update(assinatura=assinatura, temas=temas)
    return temas


def temas() -> list[tuple[str, str]]:
    return [(k, v["titulo"]) for k, v in _carregar().items()]


def consultar(tema: str = "", pergunta: str = "", limite: int = 4) -> str:
    dados = _carregar()
    if not dados:
        return "Nenhum pacote de conhecimento instalado."
    alvo = _norm(tema or "")
    escolhidos = [k for k in dados if alvo and (alvo in _norm(k) or alvo in _norm(dados[k]["titulo"]))] or list(dados)
    termos = [w for w in re.findall(r"\w{3,}", _norm(f"{tema} {pergunta}")) if w not in VAZIAS]
    pontuados = []
    for k in escolhidos:
        for s in dados[k]["secoes"]:
            alvo_txt = _norm(s["nome"] + " " + s["texto"])
            pontos = sum(alvo_txt.count(t) for t in termos) + 3 * sum(t in _norm(s["nome"]) for t in termos)
            if len(escolhidos) == 1:
                pontos += 1          # tema explícito: todas as seções contam
            if pontos:
                pontuados.append((pontos, k, s))
    pontuados.sort(key=lambda x: -x[0])
    if not pontuados:
        return "Nada específico nos pacotes. Temas disponíveis: " + ", ".join(v["titulo"] for v in dados.values())
    saida, vistos = [], set()
    for _, k, s in pontuados[:limite]:
        if k not in vistos and dados[k]["intro"]:
            saida.append(f"[{dados[k]['titulo']}] {dados[k]['intro']}")
            vistos.add(k)
        saida.append(f"[{dados[k]['titulo']} > {s['nome']}]\n{s['texto']}")
    return "\n\n".join(saida)[:9000]
