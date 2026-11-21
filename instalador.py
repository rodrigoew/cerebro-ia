"""
Instalador dos componentes locais (roda uma vez; pode repetir sem problema).

1. Pacotes Python de voz: faster-whisper, piper-tts e bibliotecas CUDA 12.
2. Ollama: instala pelo winget no Windows (ou indica o link) e o inicia.
3. Modelos da IA local: qwen3:8b e bge-m3 (via Ollama).
4. Vozes Piper em português (faber, cadu e jeff).
5. Modelo do Whisper (baixado na primeira carga).

Tudo isso usa a internet só para baixar. Depois, funciona sem internet.
"""
from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from voz import ARQUIVOS_KOKORO, URL_KOKORO, URL_PIPER, VOZES_PIPER

PACOTES_VOZ = ["faster-whisper>=1.1", "piper-tts>=1.2", "kokoro-onnx>=0.4", "numpy>=1.26", "edge-tts"]
PACOTES_CUDA = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12>=9,<10"]


def caminho_ollama() -> str | None:
    achado = shutil.which("ollama")
    if achado:
        return achado
    if platform.system() == "Windows":
        padrao = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if padrao.exists():
            return str(padrao)
    return None


class Instalador:
    def __init__(self, app):
        self.app = app
        self.log: list[str] = []
        self.rodando = False
        self.concluido = False
        self._trava = threading.Lock()

    def registrar(self, msg: str) -> None:
        linha = f"{time.strftime('%H:%M:%S')}  {msg}"
        with self._trava:
            self.log.append(linha)
            self.log = self.log[-300:]
        print(linha, flush=True)

    def componentes(self) -> dict:
        ia = self.app.llm.status(forcar=True)
        voz = self.app.voz
        return {
            "ollama_instalado": bool(caminho_ollama()) or ia["online"],
            "ollama_online": ia["online"],
            "modelo_chat": ia["chat_ok"],
            "modelo_embedding": ia["emb_ok"],
            "whisper": voz.tem_whisper(),
            "piper": voz.tem_piper(),
            "kokoro": voz.tem_kokoro(),
            "ffmpeg": self._tem("imageio_ffmpeg") or bool(shutil.which("ffmpeg")),
            "yt_dlp": self._tem("yt_dlp"),
        }

    def iniciar(self) -> bool:
        with self._trava:
            if self.rodando:
                return False
            self.rodando = True
            self.concluido = False
            self.log = []
        threading.Thread(target=self.executar, daemon=True).start()
        return True

    # ------------------------------------------------------------ passos
    def detectar_hardware(self) -> None:
        """Escolhe os modelos pelo tamanho da placa de vídeo (e grava no config)."""
        vram = 0
        candidatos = [shutil.which("nvidia-smi"), r"C:\Windows\System32\nvidia-smi.exe",
                      r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"]
        smi = next((c for c in candidatos if c and os.path.exists(c)), None)
        if smi:
            try:
                r = subprocess.run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=20)
                linhas = [l for l in r.stdout.strip().splitlines() if "," in l]
                melhor = max(linhas, key=lambda l: float(l.split(",")[-1]))     # notebooks com 2 placas: pega a maior
                nome, mem = melhor.rsplit(",", 1)
                vram = int(float(mem.strip()) / 1024 + 0.5)
                self.registrar(f"Placa de vídeo: {nome.strip()} com {vram} GB.")
            except Exception as erro:
                self.registrar(f"Não consegui ler a placa de vídeo ({erro}).")
        if not vram and platform.system() == "Windows":
            try:   # sem nvidia-smi: pergunta ao Windows (o valor pode vir limitado a 4 GB)
                r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                    "(Get-CimInstance Win32_VideoController | Where-Object {$_.Name -match 'NVIDIA'} | Select-Object -First 1).Name"],
                                   capture_output=True, text=True, timeout=20)
                nome = r.stdout.strip()
                if nome:
                    vram = 8 if any(x in nome for x in ("3070", "3080", "3090", "4060", "4070", "4080", "4090", "5070", "5080", "5090")) else 6
                    self.registrar(f"Placa NVIDIA encontrada pelo Windows: {nome} (estimando {vram} GB).")
            except Exception:
                pass
        if not vram:
            self.registrar("Nenhuma placa NVIDIA encontrada: usando modelos leves, que rodam no processador.")
        cfg = self.app.cfg
        if cfg.get("llm_local", {}).get("modelo_escolhido_manualmente"):
            self.registrar(f"Mantendo o modelo escolhido: {self.app.llm.modelo}.")
            return
        modelo = "qwen3:14b" if vram >= 16 else "qwen3:8b" if vram >= 7 else "qwen3:4b"
        cfg.setdefault("llm_local", {})["modelo"] = modelo
        cfg["llm_local"]["contexto"] = 8192 if vram >= 7 else 4096
        cfg["llm_local"]["embedding_na_cpu"] = vram < 7
        cfg.setdefault("voz", {})["dispositivo"] = "auto" if vram >= 6 else "cpu"
        self.app.llm.modelo = modelo
        self.app.voz.dispositivo = cfg["voz"]["dispositivo"]
        try:
            self.app.salvar_config()
        except Exception:
            pass
        self.registrar(f"Modelo de conversa escolhido: {modelo}. Reconhecimento de voz: "
                       f"{'placa de vídeo' if vram >= 6 else 'processador'}.")

    def executar(self) -> None:
        try:
            self.registrar("Começando a instalação dos componentes locais.")
            self.detectar_hardware()
            self._pacotes()
            self._ollama()
            self._modelos()
            self._vozes()
            self._whisper()
            self._freellmapi()
            faltando = [k for k, v in self.componentes().items() if not v]
            if faltando:
                self.registrar("Concluído com pendências: " + ", ".join(faltando) + ". Veja as mensagens acima.")
            else:
                self.registrar("Tudo pronto. A IA local e a voz já podem ser usadas.")
        except Exception as erro:
            self.registrar(f"Erro inesperado: {erro}")
        finally:
            self.rodando = False
            self.concluido = True

    def _freellmapi(self) -> None:
        """Instala e liga o roteador gratuito (uso pessoal), que fica dentro do projeto em vendor/freellmapi."""
        fla = self.app.cfg.get("freellmapi", {})
        if fla.get("instalar") is False or self.app.cfg.get("edicao") == "comercial":
            return
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        pasta = base / fla.get("pasta", "vendor/freellmapi")
        if not (pasta / "package.json").exists():
            self.registrar("FreeLLMAPI: pasta vendor/freellmapi vazia. No terminal, rode: git submodule update --init")
            return
        self.registrar("Passo extra: FreeLLMAPI (modelos gratuitos na nuvem, para perguntas gerais).")
        node = shutil.which("node") or (r"C:\Program Files\nodejs\node.exe" if os.path.exists(r"C:\Program Files\nodejs\node.exe") else None)
        if not node and platform.system() == "Windows" and shutil.which("winget"):
            self.registrar("Instalando o Node.js (necessário para o FreeLLMAPI)…")
            subprocess.run(["winget", "install", "--id", "OpenJS.NodeJS.LTS", "-e", "--silent",
                            "--accept-package-agreements", "--accept-source-agreements"], capture_output=True, timeout=900)
            node = r"C:\Program Files\nodejs\node.exe" if os.path.exists(r"C:\Program Files\nodejs\node.exe") else shutil.which("node")
        if not node:
            self.registrar("FreeLLMAPI: não encontrei o Node.js. Instale o Node LTS em nodejs.org e rode o instalador de novo.")
            return
        env = {**os.environ, "PATH": str(Path(node).parent) + os.pathsep + os.environ.get("PATH", "")}
        npm = str(Path(node).parent / ("npm.cmd" if platform.system() == "Windows" else "npm"))
        if not os.path.exists(npm):
            npm = shutil.which("npm") or "npm"
        if not (pasta / "node_modules").exists():
            self.registrar("FreeLLMAPI: baixando dependências (alguns minutos)…")
            r = subprocess.run([npm, "ci"], cwd=str(pasta), env=env, capture_output=True, text=True, timeout=1800)
            if r.returncode != 0:
                r = subprocess.run([npm, "install"], cwd=str(pasta), env=env, capture_output=True, text=True, timeout=1800)
            if r.returncode != 0:
                self.registrar("FreeLLMAPI: falha ao baixar dependências. " + (r.stderr or "")[-300:])
                return
        self.registrar("FreeLLMAPI: compilando…")
        r = subprocess.run([npm, "run", "build"], cwd=str(pasta), env=env, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            self.registrar("FreeLLMAPI: falha ao compilar. " + (r.stderr or "")[-300:])
            return
        cfg = self.app.cfg
        cfg.setdefault("freellmapi", {}).update({"ativo": True, "iniciar_junto": True})
        nv = cfg.setdefault("nuvem", {})
        nv.setdefault("provedor_aprofundar", "claude")
        nv.update({"provedor_auto": "openai", "url_openai": cfg["freellmapi"].get("url", "http://localhost:3001/v1"),
                                            "modelo_openai": "auto", "rotulo": "FreeLLMAPI",
                                            "roteamento": cfg.get("nuvem", {}).get("roteamento") if cfg.get("nuvem", {}).get("roteamento", "perguntar") != "perguntar" else "geral"})
        try:
            self.app.salvar_config()
        except Exception:
            pass
        self.registrar(self.app.iniciar_freellmapi(forcar=True))
        self.registrar("FreeLLMAPI pronto. Falta um passo seu, uma vez só: abra http://localhost:3001, crie a conta local, "
                       "cadastre as chaves gratuitas (Google, Groq…) e cole a chave unificada em Ajustes > Nuvem.")

    def _pip(self, pacotes: list[str]) -> bool:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *pacotes]
        self.registrar("Instalando: " + " ".join(pacotes))
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            self.registrar("Falhou: " + (r.stderr or r.stdout).strip().splitlines()[-1][:300])
            return False
        importlib.invalidate_caches()
        return True

    def _pacotes(self) -> None:
        self.registrar("Passo 1 de 5: pacotes de voz e edição.")
        if not getattr(sys, "frozen", False):
            self._pip(["imageio-ffmpeg>=0.5", "yt-dlp[default]>=2026.10.26", "sympy>=1.12", "cloudinary>=1.44"])
        if getattr(sys, "frozen", False):
            self.registrar("Versão instalada: os pacotes já vêm incluídos.")
            return
        if self.app.cfg.get("edicao") == "comercial":
            global PACOTES_VOZ
            PACOTES_VOZ = [p for p in PACOTES_VOZ if not p.startswith("piper")]
        if self.app.voz.tem_whisper() and self._tem("piper") and self._tem("kokoro_onnx"):
            self.registrar("Pacotes de voz já instalados.")
        else:
            self._pip(PACOTES_VOZ)
        if platform.system() in ("Windows", "Linux") and not self._tem("nvidia.cudnn"):
            self.registrar("Bibliotecas CUDA 12 para o Whisper usar a placa de vídeo (cerca de 1 GB).")
            if not self._pip(PACOTES_CUDA):
                self.registrar("Sem as bibliotecas CUDA, o Whisper roda no processador com o modelo menor.")

    @staticmethod
    def _tem(modulo: str) -> bool:
        try:
            importlib.import_module(modulo)
            return True
        except Exception:
            return False

    def _ollama(self) -> None:
        self.registrar("Passo 2 de 5: Ollama.")
        if self.app.llm.status(forcar=True)["online"]:
            self.registrar("Ollama já está rodando.")
            return
        exe = caminho_ollama()
        if not exe:
            if platform.system() == "Windows" and shutil.which("winget"):
                self.registrar("Instalando o Ollama pelo winget. O Windows pode pedir confirmação.")
                r = subprocess.run(["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent",
                                    "--accept-source-agreements", "--accept-package-agreements"],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    self.registrar("O winget não conseguiu instalar. Baixe em ollama.com/download e rode o "
                                   "instalador de novo.")
                    return
                exe = caminho_ollama()
            else:
                self.registrar("Instale o Ollama em ollama.com/download e rode o instalador de novo.")
                return
        if not exe:
            self.registrar("Ollama instalado, mas não encontrado ainda. Reinicie o computador e rode de novo.")
            return
        self.registrar("Iniciando o Ollama.")
        try:
            opcoes = {"creationflags": 0x08000000} if platform.system() == "Windows" else {}
            subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **opcoes)
        except Exception as erro:
            self.registrar(f"Não consegui iniciar o Ollama: {erro}")
        for _ in range(30):
            if self.app.llm.status(forcar=True)["online"]:
                self.registrar("Ollama no ar.")
                return
            time.sleep(1)
        self.registrar("O Ollama não respondeu. Abra o programa Ollama e rode o instalador de novo.")

    def _modelos(self) -> None:
        self.registrar("Passo 3 de 5: modelos da IA local.")
        st = self.app.llm.status(forcar=True)
        if not st["online"]:
            self.registrar("Pulando: o Ollama não está no ar.")
            return
        for nome, ok in ((self.app.llm.modelo, st["chat_ok"]), (self.app.llm.modelo_emb, st["emb_ok"])):
            if ok:
                self.registrar(f"{nome} já baixado.")
                continue
            self.registrar(f"Baixando {nome}. Pode levar alguns minutos.")
            try:
                req = urllib.request.Request(self.app.llm.url + "/api/pull",
                                             data=json.dumps({"name": nome, "stream": True}).encode(),
                                             headers={"Content-Type": "application/json"})
                ultimo = -10
                with urllib.request.urlopen(req, timeout=7200) as r:
                    for linha in r:
                        d = json.loads(linha or b"{}")
                        if d.get("error"):
                            raise RuntimeError(d["error"])
                        if d.get("total") and d.get("completed"):
                            pct = int(d["completed"] * 100 / d["total"])
                            if pct >= ultimo + 10:
                                ultimo = pct
                                self.registrar(f"{nome}: {pct}%")
                self.registrar(f"{nome} pronto.")
            except Exception as erro:
                self.registrar(f"Falha ao baixar {nome}: {erro}")

    def _vozes(self) -> None:
        self.registrar("Passo 4 de 5: vozes em português (Kokoro: Dora, Alex e Santa; Piper: Faber, Cadu e Jeff).")
        pasta_k = self.app.voz.pasta_modelos / "kokoro"
        pasta_k.mkdir(parents=True, exist_ok=True)
        for arquivo in ARQUIVOS_KOKORO:
            destino = pasta_k / arquivo
            if destino.exists():
                continue
            try:
                self.registrar(f"Baixando {arquivo} (Kokoro).")
                tmp = destino.with_suffix(destino.suffix + ".parcial")
                urllib.request.urlretrieve(URL_KOKORO + arquivo, tmp)
                tmp.replace(destino)
            except Exception as erro:
                self.registrar(f"Falha ao baixar {arquivo}: {erro}")
        if self.app.voz.tem_kokoro():
            self.registrar("Vozes Kokoro prontas.")
        pasta = self.app.voz.pasta_modelos / "piper"
        pasta.mkdir(parents=True, exist_ok=True)
        for nome, caminho in ({} if self.app.cfg.get("edicao") == "comercial" else VOZES_PIPER).items():
            destino = pasta / (Path(caminho).name + ".onnx")
            if destino.exists():
                self.registrar(f"Voz {nome} já baixada.")
                continue
            try:
                for ext in (".onnx.json", ".onnx"):
                    tmp = Path(str(destino).replace(".onnx", ext) + ".parcial")
                    urllib.request.urlretrieve(URL_PIPER + caminho + ext, tmp)
                    tmp.replace(Path(str(tmp)[:-len(".parcial")]))
                self.registrar(f"Voz {nome} pronta.")
            except Exception as erro:
                self.registrar(f"Falha ao baixar a voz {nome}: {erro}")

    def _whisper(self) -> None:
        self.registrar("Passo 5 de 5: reconhecimento de voz (Whisper). Primeira carga baixa cerca de 1,6 GB.")
        if not self.app.voz.tem_whisper():
            self.registrar("Pulando: o faster-whisper não foi instalado.")
            return
        try:
            self.app.voz.carregar_whisper()
            self.registrar(f"Pronto: {self.app.voz.status()['ouvir_desc']}.")
        except Exception as erro:
            self.registrar(f"Whisper não carregou: {erro}")
