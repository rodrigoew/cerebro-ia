"""
Atualização pelo Git (só biblioteca padrão; usado pelo Nucleo.exe e pelo próprio app).

  verificar(pasta)  busca no GitHub se há versão nova (sem mudar nada)
  atualizar(pasta)  baixa a versão nova com segurança:
                    - só avança (fast-forward), nunca apaga trabalho seu;
                    - se você tiver alterações não enviadas no código, adia e avisa;
                    - reinstala dependências e o FreeLLMAPI só quando eles mudaram.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

WINDOWS = platform.system() == "Windows"
SEM_JANELA = 0x08000000 if WINDOWS else 0


def _rodar(cmd: list[str], pasta: Path | str, timeout: int = 120, env: dict | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(pasta), capture_output=True, text=True, timeout=timeout,
                           creationflags=SEM_JANELA, env=env, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, f"programa não encontrado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "tempo esgotado"


def git_disponivel() -> str | None:
    return shutil.which("git") or next((c for c in (r"C:\Program Files\Git\cmd\git.exe",) if os.path.exists(c)), None)


def git(pasta, *args, timeout: int = 120) -> tuple[int, str]:
    exe = git_disponivel()
    if not exe:
        return 127, "Git não instalado"
    return _rodar([exe, *args], pasta, timeout)


def versao(pasta) -> str:
    try:
        return (Path(pasta) / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "?"


def eh_repositorio(pasta) -> bool:
    return (Path(pasta) / ".git").exists()


def verificar(pasta) -> dict:
    pasta = Path(pasta)
    base = {"disponivel": False, "versao_local": versao(pasta), "versao_remota": None, "motivo": None, "commits": 0}
    if not eh_repositorio(pasta):
        return {**base, "motivo": "Esta instalação não usa o Git (atualize pelo instalador)."}
    codigo, saida = git(pasta, "fetch", "--quiet", "--tags", "origin", timeout=40)
    if codigo != 0:
        return {**base, "motivo": "Sem conexão com o GitHub agora." if codigo != 127 else "Git não instalado."}
    ramo = git(pasta, "rev-parse", "--abbrev-ref", "HEAD")[1] or "main"
    codigo, n = git(pasta, "rev-list", "--count", f"HEAD..origin/{ramo}")
    commits = int(n) if codigo == 0 and n.isdigit() else 0
    remota = git(pasta, "show", f"origin/{ramo}:VERSION")[1].strip() if commits else base["versao_local"]
    return {**base, "disponivel": commits > 0, "versao_remota": remota, "commits": commits, "ramo": ramo}


def alteracoes_locais(pasta) -> list[str]:
    """Arquivos do código alterados e não enviados (dados pessoais ficam fora do Git e não contam)."""
    codigo, saida = git(pasta, "status", "--porcelain", "--untracked-files=no")
    return [l.split(maxsplit=1)[1] for l in saida.splitlines() if len(l.split(maxsplit=1)) == 2] if codigo == 0 else []


def atualizar(pasta, registrar=print, python: str | None = None) -> dict:
    pasta = Path(pasta)
    info = verificar(pasta)
    if not info["disponivel"]:
        return {"ok": True, "atualizou": False, "mensagem": info["motivo"] or f"Já está na versão mais recente ({info['versao_local']})."}
    pendentes = alteracoes_locais(pasta)
    if pendentes:
        return {"ok": False, "atualizou": False,
                "mensagem": "Você tem alterações no código que ainda não foram enviadas ao GitHub "
                            f"({', '.join(pendentes[:3])}{'…' if len(pendentes) > 3 else ''}). Envie ou descarte antes de atualizar."}
    ramo = info.get("ramo", "main")
    mudou = git(pasta, "diff", "--name-only", "HEAD", f"origin/{ramo}")[1].splitlines()
    registrar(f"Atualizando da versão {info['versao_local']} para {info['versao_remota']}…")
    codigo, saida = git(pasta, "merge", "--ff-only", f"origin/{ramo}", timeout=120)
    if codigo != 0:
        return {"ok": False, "atualizou": False, "mensagem": "Não consegui avançar a versão com segurança: " + saida[-200:]}
    git(pasta, "submodule", "update", "--init", "--recursive", timeout=600)
    if "requirements.txt" in mudou and python:
        registrar("Instalando dependências novas…")
        _rodar([python, "-m", "pip", "install", "-q", "-r", "requirements.txt"], pasta, timeout=1800)
    if any(m.startswith("vendor/freellmapi") for m in mudou):
        reconstruir_freellmapi(pasta, registrar)
    registrar(f"Pronto: versão {versao(pasta)}.")
    return {"ok": True, "atualizou": True, "mensagem": f"Atualizado para a versão {versao(pasta)}.", "arquivos": len(mudou)}


def reconstruir_freellmapi(pasta, registrar=print) -> None:
    alvo = Path(pasta) / "vendor" / "freellmapi"
    node = shutil.which("node") or (r"C:\Program Files\nodejs\node.exe" if os.path.exists(r"C:\Program Files\nodejs\node.exe") else None)
    if not (alvo / "package.json").exists() or not node:
        return
    npm = str(Path(node).parent / ("npm.cmd" if WINDOWS else "npm"))
    env = {**os.environ, "PATH": str(Path(node).parent) + os.pathsep + os.environ.get("PATH", "")}
    registrar("Atualizando o FreeLLMAPI…")
    if _rodar([npm, "ci"], alvo, timeout=1800, env=env)[0] != 0:
        _rodar([npm, "install"], alvo, timeout=1800, env=env)
    _rodar([npm, "run", "build"], alvo, timeout=1800, env=env)


def python_do_projeto() -> tuple[str | None, str | None]:
    """(python.exe, pythonw.exe) do Python 3.12 do computador."""
    candidatos = []
    if shutil.which("py"):
        codigo, saida = _rodar(["py", "-3.12", "-c", "import sys;print(sys.executable)"], ".", 30)
        if codigo == 0 and saida:
            candidatos.append(saida.splitlines()[-1].strip())
    for nome in ("python", "python3"):
        exe = shutil.which(nome)
        if exe and "WindowsApps" not in exe:
            candidatos.append(exe)
    for exe in candidatos:
        if os.path.exists(exe):
            janela = str(Path(exe).with_name("pythonw.exe"))
            return exe, (janela if os.path.exists(janela) else exe)
    return None, None
