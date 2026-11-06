"""
Voz 100% local, sem tokens e sem internet durante o uso.

Ouvir:  faster-whisper (modelo large-v3-turbo) na placa NVIDIA.
        Sem GPU utilizável, usa o modelo "small" no processador.
        Reserva: Vosk, se estiver instalado.
Falar:  Piper, com vozes brasileiras (faber, cadu ou jeff).

O reconhecimento recebe o vocabulário da sua memória (nomes de contatos,
projetos, fornecedores e termos que você usa), para acertar nomes próprios.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import threading
import time
import wave
from pathlib import Path

VOZES_PIPER = {
    "faber": "pt/pt_BR/faber/medium/pt_BR-faber-medium",
    "cadu": "pt/pt_BR/cadu/medium/pt_BR-cadu-medium",
    "jeff": "pt/pt_BR/jeff/medium/pt_BR-jeff-medium",
}
URL_PIPER = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
URL_KOKORO = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
ARQUIVOS_KOKORO = ("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")

# Vozes disponíveis em português do Brasil (id: motor:voz)
CATALOGO_VOZES = [
    # vozes neurais da Microsoft (as do "Ler em voz alta" do Edge): muito naturais, precisam de internet
    {"id": "nuvem:pt-BR-ThalitaMultilingualNeural", "nome": "Thalita", "genero": "feminina", "motor": "Neural (internet)", "qualidade": "natural"},
    {"id": "nuvem:pt-BR-FranciscaNeural", "nome": "Francisca", "genero": "feminina", "motor": "Neural (internet)", "qualidade": "natural"},
    {"id": "nuvem:pt-BR-AntonioNeural", "nome": "Antônio", "genero": "masculina", "motor": "Neural (internet)", "qualidade": "natural"},
    {"id": "kokoro:pf_dora", "nome": "Dora", "genero": "feminina", "motor": "Kokoro", "qualidade": "alta"},
    {"id": "kokoro:pm_alex", "nome": "Alex", "genero": "masculina", "motor": "Kokoro", "qualidade": "alta"},
    {"id": "kokoro:pm_santa", "nome": "Santa", "genero": "masculina", "motor": "Kokoro", "qualidade": "alta"},
    {"id": "piper:faber", "nome": "Faber", "genero": "masculina", "motor": "Piper", "qualidade": "média"},
    {"id": "piper:cadu", "nome": "Cadu", "genero": "masculina", "motor": "Piper", "qualidade": "média"},
    {"id": "piper:jeff", "nome": "Jeff", "genero": "masculina", "motor": "Piper", "qualidade": "média"},
]


def _preparar_cuda_windows() -> None:
    """No Windows, as bibliotecas CUDA instaladas pelo pip ficam em pastas
    próprias; elas precisam ser registradas antes de carregar o Whisper."""
    if sys.platform != "win32":
        return
    try:
        import nvidia  # wheels nvidia-cublas-cu12 / nvidia-cudnn-cu12
    except ImportError:
        return
    for raiz in getattr(nvidia, "__path__", []):
        for sub in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
            pasta = Path(raiz) / sub / "bin"
            if pasta.is_dir():
                try:
                    os.add_dll_directory(str(pasta))
                except OSError:
                    pass
                os.environ["PATH"] = str(pasta) + os.pathsep + os.environ.get("PATH", "")


def _silencio(segundos: float):
    import numpy as np
    return np.zeros(int(16000 * segundos), dtype=np.float32)


class Voz:
    def __init__(self, cfg: dict, base: Path):
        c = cfg.get("voz", {})
        self.cfg = c
        self.pasta_modelos = base / "modelos"
        self.modelo_whisper = c.get("modelo_whisper", "large-v3-turbo")
        self.modelo_whisper_cpu = c.get("modelo_whisper_cpu", "small")
        self.dispositivo = c.get("dispositivo", "auto")  # auto | cuda | cpu
        self.voz_id = c.get("voz", "kokoro:pf_dora" if "voz_piper" not in c else f"piper:{c['voz_piper']}")
        self.voz_piper = self.voz_id.split(":", 1)[1] if self.voz_id.startswith("piper:") else c.get("voz_piper", "faber")
        self.velocidade = float(c.get("velocidade", 1.0))
        self._kokoro = None
        caminho_vosk = c.get("modelo_vosk", "modelos/vosk-model-small-pt-0.3")
        self.caminho_vosk = base / caminho_vosk if not Path(caminho_vosk).is_absolute() else Path(caminho_vosk)
        self.vocabulario_extra: list[str] = list(c.get("vocabulario", []))
        self._whisper = None
        self._whisper_desc = None
        self._piper = None
        self._vosk = None
        self._trava = threading.Lock()
        self.motivo = None

    # ------------------------------------------------------------ estado
    def caminho_piper(self, nome: str | None = None) -> Path:
        nome = nome or self.voz_piper
        return self.pasta_modelos / "piper" / (Path(VOZES_PIPER.get(nome, VOZES_PIPER["faber"])).name + ".onnx")

    def tem_whisper(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def tem_piper(self) -> bool:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return self.caminho_piper().exists()

    def tem_kokoro(self) -> bool:
        try:
            import kokoro_onnx  # noqa: F401
        except ImportError:
            return False
        return all((self.pasta_modelos / "kokoro" / a).exists() for a in ARQUIVOS_KOKORO)

    def vozes(self) -> list[dict]:
        saida = []
        for v in CATALOGO_VOZES:
            if self.cfg.get("_edicao") == "comercial" and v["motor"] == "Piper":
                continue
            motor, nome = v["id"].split(":")
            ok = self.tem_nuvem() if motor == "nuvem" else self.tem_kokoro() if motor == "kokoro" else \
                (self._tem_pacote_piper() and self.caminho_piper(nome).exists())
            saida.append({**v, "instalada": ok, "atual": v["id"] == self.voz_id})
        return saida

    def tem_nuvem(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    def _sintetizar_nuvem(self, texto: str, voz: str, velocidade: float) -> bytes:
        """Voz neural da Microsoft (MP3). Se falhar (sem internet), quem chama usa a Kokoro."""
        import asyncio
        import edge_tts
        taxa = f"{round((velocidade - 1) * 100):+d}%"

        async def gerar() -> bytes:
            partes = []
            async for bloco in edge_tts.Communicate(texto, voz, rate=taxa).stream():
                if bloco["type"] == "audio":
                    partes.append(bloco["data"])
            return b"".join(partes)

        audio = asyncio.run(asyncio.wait_for(gerar(), timeout=10))
        if not audio:
            raise RuntimeError("voz neural sem áudio")
        return audio

    def _tem_pacote_piper(self) -> bool:
        try:
            import piper  # noqa: F401
            return True
        except ImportError:
            return False

    def descricao_voz(self, voz_id: str | None = None) -> str:
        v = next((x for x in CATALOGO_VOZES if x["id"] == (voz_id or self.voz_id)), None)
        return f"{v['motor']} ({v['nome']}, {v['genero']})" if v else "voz desconhecida"

    def pode_falar(self) -> bool:
        return self.tem_kokoro() or self.tem_piper() or (self.voz_id.startswith("nuvem:") and self.tem_nuvem())

    def tem_vosk(self) -> bool:
        try:
            import vosk  # noqa: F401
        except ImportError:
            return False
        return self.caminho_vosk.exists()

    def disponivel(self) -> bool:
        ok = self.tem_whisper() or self.tem_vosk()
        self.motivo = None if ok else "Reconhecimento de voz não instalado. Use o instalador."
        return ok

    def status(self) -> dict:
        ouvir = self.tem_whisper() or self.tem_vosk()
        return {
            "ouvir": "whisper" if self.tem_whisper() else "vosk" if self.tem_vosk() else None,
            "ouvir_desc": self._whisper_desc or (f"Whisper {self.modelo_whisper}" if self.tem_whisper()
                                                 else "Vosk (básico)" if self.tem_vosk() else None),
            "falar": (self.descricao_voz() if (self.voz_id.startswith("kokoro") and self.tem_kokoro()) or
                      (self.voz_id.startswith("piper") and self.tem_piper())
                      else self.descricao_voz("kokoro:pf_dora") if self.tem_kokoro()
                      else f"Piper ({self.voz_piper})" if self.tem_piper() else None),
            "motivo": None if ouvir else "Reconhecimento de voz não instalado. Use o instalador.",
        }

    # ------------------------------------------------------------ ouvir
    def carregar_whisper(self):
        with self._trava:
            if self._whisper is not None:
                return self._whisper
            _preparar_cuda_windows()
            from faster_whisper import WhisperModel
            raiz = str(self.pasta_modelos / "whisper")
            tentativas = []
            if self.dispositivo in ("auto", "cuda"):
                tentativas.append((self.modelo_whisper, "cuda", self.cfg.get("precisao_gpu", "int8_float16")))
            if self.dispositivo in ("auto", "cpu"):
                tentativas.append((self.modelo_whisper_cpu, "cpu", "int8"))
            erro_final = None
            for modelo, disp, precisao in tentativas:
                try:
                    m = WhisperModel(modelo, device=disp, compute_type=precisao, download_root=raiz)
                    # Falhas de CUDA só aparecem na primeira transcrição: testa já.
                    list(m.transcribe(_silencio(0.5), language="pt")[0])
                    self._whisper = m
                    self._whisper_desc = (f"Whisper {modelo} "
                                          f"({'placa de vídeo' if disp == 'cuda' else 'processador'})")
                    return m
                except Exception as erro:
                    erro_final = erro
            texto = str(erro_final)
            if "Hub" in texto or "snapshot" in texto or "ConnectError" in texto:
                raise RuntimeError("O modelo do Whisper ainda não foi baixado. Rode o instalador "
                                   "(botão Instalar o que falta ou instalar.bat) com internet uma vez.")
            raise RuntimeError(f"Não consegui carregar o Whisper: {texto[:200]}")

    def prompt_vocabulario(self, termos: list[str]) -> str:
        unicos, vistos = [], set()
        for t in self.vocabulario_extra + termos:
            t = (t or "").strip()
            if len(t) > 1 and t.lower() not in vistos:
                vistos.add(t.lower())
                unicos.append(t)
        if not unicos:
            return "Conversa em português do Brasil."
        return "Conversa em português do Brasil. Nomes e termos que podem aparecer: " + ", ".join(unicos[:60]) + "."

    def transcrever(self, pcm16: bytes, taxa: int = 16000, vocabulario: list[str] | None = None) -> str:
        if not pcm16 or len(pcm16) < taxa // 4:
            return ""
        if self.tem_whisper():
            import numpy as np
            modelo = self.carregar_whisper()
            audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
            segmentos, _ = modelo.transcribe(
                audio, language="pt", beam_size=5, vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                initial_prompt=self.prompt_vocabulario(vocabulario or []),
                condition_on_previous_text=False)
            texto = " ".join(s.text.strip() for s in segmentos).strip()
            # Em trechos sem fala, o Whisper às vezes "ouve" frases prontas: descarta.
            if re.fullmatch(r"(?i)[\s.,!?…]*(obrigad[oa]( por assistir)?|legendas?\b.*|tchau)[\s.!]*", texto):
                return ""
            return texto
        if self.tem_vosk():
            return self._transcrever_vosk(pcm16, taxa)
        raise RuntimeError("Reconhecimento de voz não instalado. Use o instalador.")

    def _transcrever_vosk(self, pcm16: bytes, taxa: int) -> str:
        import vosk
        with self._trava:
            if self._vosk is None:
                vosk.SetLogLevel(-1)
                self._vosk = vosk.Model(str(self.caminho_vosk))
        rec = vosk.KaldiRecognizer(self._vosk, taxa)
        partes = []
        for i in range(0, len(pcm16), taxa * 2):
            if rec.AcceptWaveform(pcm16[i:i + taxa * 2]):
                partes.append(json.loads(rec.Result()).get("text", ""))
        partes.append(json.loads(rec.FinalResult()).get("text", ""))
        return " ".join(p for p in partes if p).strip()

    # ------------------------------------------------------------ falar
    def carregar_piper(self):
        with self._trava:
            if self._piper is None:
                from piper import PiperVoice
                self._piper = PiperVoice.load(str(self.caminho_piper()))
            return self._piper

    def carregar_kokoro(self):
        with self._trava:
            if self._kokoro is None:
                from kokoro_onnx import Kokoro
                pasta = self.pasta_modelos / "kokoro"
                self._kokoro = Kokoro(str(pasta / ARQUIVOS_KOKORO[0]), str(pasta / ARQUIVOS_KOKORO[1]))
            return self._kokoro

    def aplicar(self, cfg_voz: dict) -> None:
        """Atualiza voz e velocidade sem reiniciar o app."""
        self.cfg.update(cfg_voz)
        if "voz" in cfg_voz:
            self.voz_id = cfg_voz["voz"]
            if self.voz_id.startswith("piper:"):
                novo = self.voz_id.split(":", 1)[1]
                if novo != self.voz_piper:
                    self._piper = None
                self.voz_piper = novo
        if "velocidade" in cfg_voz:
            self.velocidade = float(cfg_voz["velocidade"])
        if "vocabulario" in cfg_voz:
            self.vocabulario_extra = list(cfg_voz["vocabulario"])

    def sintetizar(self, texto: str, voz_id: str | None = None, velocidade: float | None = None) -> bytes:
        texto = preparar_fala(texto)
        if not texto:
            return b""
        voz_id = voz_id or self.voz_id
        velocidade = max(0.6, min(1.6, float(velocidade or self.velocidade)))
        if voz_id.startswith("nuvem:"):
            if self.tem_nuvem() and time.time() - getattr(self, "_falha_nuvem", 0) > 120:
                try:
                    return self._sintetizar_nuvem(texto, voz_id.split(":", 1)[1], velocidade)
                except Exception:
                    self._falha_nuvem = time.time()      # sem internet: Kokoro por 2 minutos, depois tenta de novo
            reserva = self.cfg.get("voz_reserva", "kokoro:pf_dora")
            if self.tem_kokoro():
                return self.sintetizar(texto, reserva if reserva.startswith("kokoro:") else "kokoro:pf_dora", velocidade)
            if self.tem_piper():
                return self.sintetizar(texto, "piper:" + self.voz_piper, velocidade)
            raise RuntimeError("Sem internet para a voz neural e nenhuma voz local instalada.")
        if voz_id.startswith("kokoro:") and self.tem_kokoro():
            import numpy as np
            amostras, taxa = self.carregar_kokoro().create(texto, voice=voz_id.split(":", 1)[1], speed=velocidade,
                                                           lang="pt-br")
            pcm = (np.clip(amostras, -1, 1) * 32767).astype("<i2").tobytes()
            saida = io.BytesIO()
            with wave.open(saida, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(taxa)
                wav.writeframes(pcm)
            return saida.getvalue()
        if voz_id.startswith("piper:") and voz_id.split(":", 1)[1] != self.voz_piper:
            self.voz_piper, self._piper = voz_id.split(":", 1)[1], None
        if not self.tem_piper():
            if self.tem_kokoro():
                return self.sintetizar(texto, "kokoro:pf_dora", velocidade)
            raise RuntimeError("Nenhuma voz instalada. Use o instalador.")
        voz = self.carregar_piper()
        escala = 1.0 / velocidade
        saida = io.BytesIO()
        with wave.open(saida, "wb") as wav:
            try:  # piper-tts 1.3 ou mais novo
                from piper import SynthesisConfig
                voz.synthesize_wav(texto, wav, syn_config=SynthesisConfig(length_scale=escala))
            except ImportError:  # versões anteriores
                voz.synthesize(texto, wav, length_scale=escala)
        return saida.getvalue()


# ------------------------------------------------------------ texto para a fala

MESES_FALA = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
              "setembro", "outubro", "novembro", "dezembro"]


def _reais(m: re.Match) -> str:
    inteiro = int(m.group(1).replace(".", ""))
    centavos = int(m.group(2) or 0)
    texto = f"{inteiro} {'real' if inteiro == 1 else 'reais'}"
    if centavos:
        texto += f" e {centavos} {'centavo' if centavos == 1 else 'centavos'}"
    return texto


def preparar_fala(texto: str) -> str:
    """Deixa o texto natural para ser falado: tira marcações e citações e
    escreve dinheiro, datas e horas do jeito que se fala."""
    t = texto or ""
    t = re.sub(r"\[\d+\]", "", t)
    t = re.sub(r"[*_#`>|]+", " ", t)
    t = re.sub(r"(?m)^\s*[-•]\s*", "", t)
    t = re.sub(r"https?://\S+", "o link", t)
    t = re.sub(r"R\$\s?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{2}))?", _reais, t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b",
               lambda m: f"{int(m.group(1))} de {MESES_FALA[int(m.group(2)) - 1]}"
               if 1 <= int(m.group(2)) <= 12 else m.group(0), t)
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b",
               lambda m: f"{int(m.group(1))} horas" + (f" e {int(m.group(2))}" if int(m.group(2)) else ""), t)
    t = re.sub(r"\b(\d{1,2})h(\d{2})?\b",
               lambda m: f"{int(m.group(1))} horas" + (f" e {int(m.group(2))}" if m.group(2) else ""), t)
    t = re.sub(r"\b1 (\w+)\((?:s|es)\)", r"1 \1", t)
    t = re.sub(r"(\w)\((s|es)\)", r"\1\2", t)
    t = t.replace("–", " a ").replace("%", " por cento")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"\s+([.,!?;:])", r"\1", t).strip()
