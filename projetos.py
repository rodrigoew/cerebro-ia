"""
Projetos de programação criados pelo Núcleo (ferramenta criar_projeto).

Tudo fica numa pasta própria (Documentos/Nucleo/Projetos, ou cfg["projetos_dir"]). Nenhum arquivo é gravado fora
dela, nada é executado: o Núcleo escreve o código, o README diz como rodar e a pasta é aberta para você.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

MAX_ARQUIVOS = 80
MAX_BYTES = 600_000
PROIBIDOS = {".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".scr", ".msi", ".lnk", ".reg"}


def pasta_base(cfg: dict) -> pathlib.Path:
    destino = (cfg or {}).get("projetos_dir")
    if destino:
        return pathlib.Path(destino).expanduser()
    docs = pathlib.Path.home() / "Documents"
    if not docs.exists():
        docs = pathlib.Path.home() / "Documentos" if (pathlib.Path.home() / "Documentos").exists() else pathlib.Path.home()
    return docs / "Nucleo" / "Projetos"


def _nome(nome: str) -> str:
    n = re.sub(r"[^\w.-]+", "-", str(nome or "").strip()).strip("-.")[:60]
    if not n:
        raise ValueError("Dê um nome ao projeto.")
    return n


def _caminho(c: str) -> str:
    c = str(c or "").replace("\\", "/").strip().lstrip("/")
    partes = [p for p in c.split("/") if p not in ("", ".")]
    if not partes or any(p == ".." or ":" in p for p in partes):
        raise ValueError(f"Caminho inválido: {c!r}")
    if pathlib.PurePosixPath(partes[-1]).suffix.lower() in PROIBIDOS:
        raise ValueError(f"Por segurança, não gravo executáveis ou scripts do sistema: {partes[-1]}")
    return "/".join(partes)


def validar(a: dict) -> dict:
    arquivos = a.get("arquivos") or []
    if not isinstance(arquivos, list) or not arquivos:
        raise ValueError("O projeto não tem arquivos.")
    if len(arquivos) > MAX_ARQUIVOS:
        raise ValueError(f"Projeto grande demais ({len(arquivos)} arquivos; máximo {MAX_ARQUIVOS}).")
    limpos, vistos, total = [], set(), 0
    for x in arquivos:
        c = _caminho(x.get("caminho"))
        conteudo = str(x.get("conteudo") or "")
        total += len(conteudo.encode("utf-8"))
        if c.lower() in vistos:
            continue
        vistos.add(c.lower())
        limpos.append({"caminho": c, "conteudo": conteudo})
    if total > MAX_BYTES:
        raise ValueError("Projeto grande demais para criar de uma vez; divida em partes.")
    return {"nome": _nome(a.get("nome")), "descricao": str(a.get("descricao") or "")[:2000],
            "como_rodar": str(a.get("como_rodar") or "")[:1500], "arquivos": limpos}


def criar(cfg: dict, dados: dict, abrir: bool = True) -> dict:
    d = validar(dados)
    raiz = (pasta_base(cfg) / d["nome"]).resolve()
    base = pasta_base(cfg).resolve()
    if base not in raiz.parents:
        raise ValueError("Destino fora da pasta de projetos.")
    novo = not raiz.exists()
    gravados = []
    for x in d["arquivos"]:
        alvo = (raiz / x["caminho"]).resolve()
        if raiz not in alvo.parents:
            raise ValueError(f"Caminho fora do projeto: {x['caminho']}")
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(x["conteudo"], encoding="utf-8", newline="")
        gravados.append(x["caminho"])
    leia = raiz / "README.md"
    if not leia.exists():
        leia.write_text(f"# {d['nome']}\n\n{d['descricao']}\n\n## Como rodar\n\n```\n{d['como_rodar'] or '(veja os arquivos do projeto)'}\n```\n"
                        "\nCriado pelo Núcleo.\n", encoding="utf-8")
    if abrir:
        abrir_pasta(raiz)
    return {"ok": True, "pasta": str(raiz), "arquivos": gravados,
            "mensagem": f"{'Criei' if novo else 'Atualizei'} o projeto “{d['nome']}” ({len(gravados)} arquivo(s)) em {raiz}."
                        + (f" Para rodar: {d['como_rodar']}" if d["como_rodar"] else "")}


def abrir_pasta(caminho: pathlib.Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(caminho)])
        else:
            subprocess.Popen(["xdg-open", str(caminho)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def ver(cfg: dict, nome: str) -> str:
    base = pasta_base(cfg)
    if not nome:
        if not base.exists():
            return "Nenhum projeto criado ainda."
        projetos = sorted(p.name for p in base.iterdir() if p.is_dir())
        return "Projetos: " + (", ".join(projetos) if projetos else "nenhum")
    raiz = base / _nome(nome)
    if not raiz.exists():
        return f"Projeto “{nome}” não encontrado. " + ver(cfg, "")
    saida, total = [f"Projeto {raiz}:"], 0
    for arq in sorted(raiz.rglob("*")):
        if arq.is_dir() or any(p in (".git", "bin", "obj", "node_modules", "target", "__pycache__", ".venv") for p in arq.parts):
            continue
        rel = arq.relative_to(raiz).as_posix()
        try:
            texto = arq.read_text(encoding="utf-8")
        except Exception:
            saida.append(f"--- {rel} (binário)")
            continue
        if total > 60_000:
            saida.append(f"--- {rel} (não mostrado: limite)")
            continue
        total += len(texto)
        saida.append(f"--- {rel}\n{texto[:12_000]}")
    return "\n".join(saida)
