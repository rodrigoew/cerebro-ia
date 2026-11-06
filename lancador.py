"""
Nucleo.exe: o único arquivo que você precisa abrir.

A cada abertura:
  1. confere no seu GitHub se há versão nova e atualiza com segurança;
  2. abre o Núcleo, sem janela de console.

Em um computador novo (sem o projeto), ele prepara tudo:
  instala o Git e o Python (via winget), baixa o projeto, roda o instalador
  e cria o atalho "Núcleo" na área de trabalho e no menu Iniciar.

O GitHub gera este executável sozinho (veja .github/workflows/lancador.yml):
baixe uma vez em Releases e não precisa mais de .bat.
"""
from __future__ import annotations

import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import atualizador as at

REPO_PADRAO = "https://github.com/rodrigoew/cerebro-ia.git"
CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "Nucleo" / "lancador.json"
EXE = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()


def ler_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def gravar_config(d: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def achar_pasta(cfg: dict) -> Path | None:
    for c in (cfg.get("pasta"), EXE.parent, Path.home() / "Documents" / "cerebro-ia"):
        if c and (Path(c) / "app.py").exists():
            return Path(c)
    return None


def nucleo_rodando(porta: int = 8765) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
            return True
    except OSError:
        return False


def winget(pacote: str, registrar) -> bool:
    registrar(f"Instalando {pacote} (pode pedir permissão do Windows)…")
    codigo, saida = at._rodar(["winget", "install", "--id", pacote, "-e", "--silent",
                               "--accept-package-agreements", "--accept-source-agreements"], ".", timeout=1800)
    return codigo == 0 or "already installed" in saida.lower() or "já está instalado" in saida.lower()


def criar_atalhos(pasta: Path) -> None:
    icone = pasta / "static" / "icone.ico"
    alvo = str(EXE) if getattr(sys, "frozen", False) else sys.executable
    script = (
        "$w = New-Object -ComObject WScript.Shell;"
        "foreach ($d in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'))) {"
        f"$a = $w.CreateShortcut((Join-Path $d 'Núcleo.lnk')); $a.TargetPath = '{alvo}'; $a.WorkingDirectory = '{pasta}';"
        f"$a.IconLocation = '{icone}'; $a.Description = 'Núcleo, seu segundo cérebro'; $a.Save() }}")
    at._rodar(["powershell", "-NoProfile", "-Command", script], ".", timeout=60)


class Trabalho:
    """Faz o serviço em segundo plano e manda mensagens para a janela."""
    def __init__(self, fila: queue.Queue):
        self.fila = fila

    def registrar(self, texto: str) -> None:
        self.fila.put(("log", texto))

    def etapa(self, texto: str) -> None:
        self.fila.put(("etapa", texto))

    def executar(self) -> None:
        try:
            cfg = ler_config()
            pasta = achar_pasta(cfg)
            if pasta is None:
                pasta = self.preparar_maquina(cfg)
                if pasta is None:
                    return
            cfg["pasta"] = str(pasta)
            if not cfg.get("atalho_criado") and getattr(sys, "frozen", False):
                criar_atalhos(pasta)                 # o atalho passa a abrir este Nucleo.exe
                cfg["atalho_criado"] = True
                self.registrar("Atalho “Núcleo” criado na área de trabalho e no menu Iniciar.")
            gravar_config(cfg)
            python, pythonw = at.python_do_projeto()
            if nucleo_rodando():
                self.etapa("O Núcleo já está aberto.")
                self.abrir(pasta, pythonw)
                return
            if at.git_disponivel() and at.eh_repositorio(pasta):
                self.etapa("Procurando atualizações…")
                r = at.atualizar(pasta, self.registrar, python)
                self.registrar(r["mensagem"])
                if not r["ok"]:
                    self.fila.put(("aviso", r["mensagem"]))
                    time.sleep(4)
            self.etapa(f"Abrindo o Núcleo {at.versao(pasta)}…")
            self.abrir(pasta, pythonw)
        except Exception as erro:
            self.fila.put(("erro", f"Algo deu errado: {erro}"))

    def abrir(self, pasta: Path, pythonw: str | None) -> None:
        if not pythonw:
            self.fila.put(("erro", "Não encontrei o Python 3.12. Abra o Nucleo.exe de novo para instalar."))
            return
        subprocess.Popen([pythonw, str(pasta / "app.py")], cwd=str(pasta), creationflags=at.SEM_JANELA)
        time.sleep(1.5)
        self.fila.put(("fim", None))

    def preparar_maquina(self, cfg: dict) -> Path | None:
        self.etapa("Preparando este computador (só na primeira vez)…")
        if not at.git_disponivel() and not winget("Git.Git", self.registrar):
            self.fila.put(("erro", "Não consegui instalar o Git. Instale em git-scm.com e abra de novo."))
            return None
        python, _ = at.python_do_projeto()
        if not python and not winget("Python.Python.3.12", self.registrar):
            self.fila.put(("erro", "Não consegui instalar o Python 3.12. Instale em python.org e abra de novo."))
            return None
        destino = Path.home() / "Documents" / "cerebro-ia"
        repo = cfg.get("repositorio", REPO_PADRAO)
        self.etapa("Baixando o Núcleo do seu GitHub (pode abrir o login do GitHub)…")
        codigo, saida = at.git(destino.parent, "clone", "--recurse-submodules", repo, str(destino), timeout=1800)
        if codigo != 0:
            self.fila.put(("erro", "Não consegui baixar o projeto: " + saida[-200:]))
            return None
        python, _ = at.python_do_projeto()
        self.etapa("Instalando a IA local e as vozes (cerca de 9 GB, só uma vez)…")
        at._rodar([python, "-m", "pip", "install", "-q", "-r", "requirements.txt"], destino, timeout=3600)
        proc = subprocess.Popen([python, "app.py", "--instalar"], cwd=str(destino), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                creationflags=at.SEM_JANELA)
        for linha in proc.stdout:
            self.registrar(linha.rstrip())
        proc.wait()
        criar_atalhos(destino)
        self.registrar("Atalho “Núcleo” criado na área de trabalho e no menu Iniciar.")
        return destino


def janela() -> None:
    import tkinter as tk
    from tkinter import ttk
    fila: queue.Queue = queue.Queue()
    raiz = tk.Tk()
    raiz.title("Núcleo")
    raiz.configure(bg="#0E0B08")
    raiz.geometry("520x300")
    raiz.resizable(False, False)
    try:
        icone = (Path(getattr(sys, "_MEIPASS", EXE.parent)) / "icone.ico")
        if not icone.exists():
            icone = EXE.parent / "static" / "icone.ico"
        raiz.iconbitmap(str(icone))
    except Exception:
        pass
    tk.Label(raiz, text="Núcleo", fg="#F1E7D2", bg="#0E0B08", font=("Georgia", 22, "bold")).pack(pady=(18, 2))
    etapa = tk.Label(raiz, text="Iniciando…", fg="#D9A845", bg="#0E0B08", font=("Segoe UI", 11))
    etapa.pack()
    barra = ttk.Progressbar(raiz, mode="indeterminate", length=440)
    barra.pack(pady=10)
    barra.start(12)
    log = tk.Text(raiz, height=7, width=64, bg="#17130D", fg="#A89A80", relief="flat", font=("Consolas", 9))
    log.pack(padx=16)

    def tratar():
        try:
            while True:
                tipo, valor = fila.get_nowait()
                if tipo == "log":
                    log.insert("end", valor + "\n")
                    log.see("end")
                elif tipo == "etapa":
                    etapa.config(text=valor)
                elif tipo == "aviso":
                    etapa.config(text=valor[:90], fg="#E8893A")
                elif tipo == "erro":
                    barra.stop()
                    etapa.config(text="Não deu certo. Veja a mensagem abaixo.", fg="#E0483E")
                    log.insert("end", valor + "\n")
                    log.see("end")
                elif tipo == "fim":
                    raiz.destroy()
                    return
        except queue.Empty:
            pass
        raiz.after(150, tratar)

    threading.Thread(target=Trabalho(fila).executar, daemon=True).start()
    raiz.after(150, tratar)
    raiz.mainloop()


if __name__ == "__main__":
    janela()
