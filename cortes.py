"""
Cortes automáticos para YouTube Shorts / TikTok / Reels.

Fluxo: pega um vídeo (arquivo seu ou, se você mandar um link, baixa com yt-dlp), transcreve com o mesmo Whisper que o
Núcleo já usa na voz, escolhe os melhores trechos, recorta em vertical 9:16 com legenda embutida e salva tudo em
Documentos/Nucleo/Cortes/<nome>/. Não publica em lugar nenhum e não cria contas: entrega os arquivos prontos.

O Núcleo é uma ferramenta; a responsabilidade pelo que é baixado e publicado é de quem usa. Baixe e publique só o que
você tem direito de usar (conteúdo seu, autorizado ou livre): republicar vídeo de terceiros pode derrubar o canal.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import wave
import json
import math

GANCHOS = ("segredo", "nunca", "sempre", "erro", "errado", "melhor", "pior", "ninguém", "ninguem", "dinheiro", "rico",
           "verdade", "mentira", "cuidado", "atenção", "atencao", "incrível", "incrivel", "impossível", "impossivel",
           "primeira vez", "descobri", "olha isso", "veja", "resultado", "antes", "depois", "por que", "porque", "como")


def _pasta(app) -> pathlib.Path:
    base = (app.cfg or {}).get("cortes_dir")
    if base:
        return pathlib.Path(base).expanduser()
    docs = pathlib.Path.home() / "Documents"
    if not docs.exists() and (pathlib.Path.home() / "Documentos").exists():
        docs = pathlib.Path.home() / "Documentos"
    return docs / "Nucleo" / "Cortes"


def _ffmpeg() -> str:
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        raise RuntimeError("FFmpeg não encontrado. Instale requirements.txt.")


def _nome(t: str) -> str:
    return re.sub(r"[^\w.-]+", "-", str(t or "corte").strip()).strip("-.")[:50] or "corte"


# ------------------------------------------------------------------ baixar (opcional)
def baixar(url: str, destino: pathlib.Path) -> pathlib.Path:
    import importlib.util
    if not shutil.which("yt-dlp") and importlib.util.find_spec("yt_dlp") is None:
        raise RuntimeError("Para baixar de um link falta o yt-dlp. Rode o instalador (Instalar o que falta) uma vez com internet, "
                           "ou me dê o arquivo do vídeo já baixado.")
    destino.mkdir(parents=True, exist_ok=True)
    saida = destino / "fonte.%(ext)s"
    comando = [shutil.which("yt-dlp")] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]
    r = subprocess.run(comando + ["--no-playlist", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4", "-o", str(saida), "--", url],
                       capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError("Não consegui baixar esse vídeo: " + (r.stderr or "").strip()[-300:])
    arquivos = sorted(destino.glob("fonte.*"))
    if not arquivos:
        raise RuntimeError("O download não gerou arquivo.")
    return arquivos[0]


# ------------------------------------------------------------------ transcrição em palavras
def transcrever_palavras(voz, caminho: pathlib.Path, max_duracao_seg=7200, bloco_seg=120, progresso=None) -> list[dict]:
    """Transcreve janelas pequenas, com contexto sobreposto e tempos absolutos."""
    import numpy as np
    if not math.isfinite(float(bloco_seg)) or not 1 <= float(bloco_seg) <= 300:
        raise ValueError("Bloco de transcrição deve ter entre 1 e 300 segundos.")
    with tempfile.TemporaryDirectory(prefix="nucleo-audio-") as temp:
        wav = pathlib.Path(temp) / "audio.wav"
        r = subprocess.run([_ffmpeg(), "-nostdin", "-y", "-i", str(caminho), "-t", str(max_duracao_seg+1), "-ac", "1", "-ar", "16000",
                            "-c:a", "pcm_s16le", "-vn", str(wav)], capture_output=True, timeout=1800,
                           **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
        if r.returncode:
            raise RuntimeError("Não foi possível extrair o áudio.")
        with wave.open(str(wav), "rb") as stream:
            taxa, frames = stream.getframerate(), stream.getnframes()
            duracao = frames / taxa
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or taxa != 16000:
                raise ValueError("Formato de áudio inesperado para transcrição.")
            if duracao > max_duracao_seg + .1:
                raise ValueError("Vídeo excede a duração máxima configurada; divida o original em partes.")
        modelo = voz.carregar_whisper()
        na_gpu = getattr(voz, "_whisper_gpu", False)
        palavras = []
        passo = int(float(bloco_seg)*taxa)
        margem = min(2.0,float(bloco_seg)/4)
        for centro in range(0,frames,passo):
            inicio = max(0,centro-int(margem*taxa))
            fim = min(frames,centro+passo+int(margem*taxa))
            # Fecha o WAV antes da inferência: nenhum áudio integral é mantido em RAM.
            with wave.open(str(wav),"rb") as stream:
                stream.setpos(inicio)
                pcm = stream.readframes(fim-inicio)
            audio = np.frombuffer(pcm,dtype="<i2").astype(np.float32)
            audio /= 32768.0
            del pcm
            segmentos, _ = modelo.transcribe(audio,language="pt",beam_size=3 if na_gpu else 1,
                word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
            deslocamento = inicio/taxa
            lim_inf, lim_sup = centro/taxa, min(frames,centro+passo)/taxa
            for seg in segmentos:
                for p in (seg.words or []):
                    texto = p.word.strip()
                    ini, final = float(p.start)+deslocamento,float(p.end)+deslocamento
                    if not texto or not all(math.isfinite(v) for v in (ini,final)) or not ini <= final:
                        continue
                    meio = (ini+final)/2
                    if lim_inf <= meio < lim_sup or (lim_sup == duracao and meio == duracao):
                        palavras.append({"inicio":max(0,ini),"fim":min(duracao,final),"texto":texto})
            del segmentos, audio
            if progresso:
                try: progresso(lim_sup,duracao)
                except Exception: pass  # O indicador não deve interromper a transcrição.
        return sorted(palavras,key=lambda p:(p["inicio"],p["fim"]))


# ------------------------------------------------------------------ escolher os melhores trechos
def _frases(palavras: list[dict]) -> list[dict]:
    frases, atual = [], []
    for p in palavras:
        atual.append(p)
        if re.search(r"[.!?…]$", p["texto"]) or p["fim"] - atual[0]["inicio"] >= 12:
            frases.append(atual); atual = []
    if atual:
        frases.append(atual)
    return [{"inicio": f[0]["inicio"], "fim": f[-1]["fim"], "texto": " ".join(w["texto"] for w in f)} for f in frases if f]


def escolher_trechos(palavras: list[dict], quantidade: int = 3, dur_min: float = 15, dur_max: float = 60) -> list[dict]:
    if not 1 <= float(dur_min) <= float(dur_max) <= 180:
        raise ValueError("Duração dos cortes deve estar entre 1 e 180 segundos.")
    quantidade = max(1, min(10, int(quantidade)))
    frases = _frases(palavras)
    if not frases:
        return []
    candidatos = []
    for i in range(len(frases)):
        ini = frases[i]["inicio"]
        fim = ini
        texto = []
        for j in range(i, len(frases)):
            fim = frases[j]["fim"]
            texto.append(frases[j]["texto"])
            dur = fim - ini
            if dur < dur_min:
                continue
            if dur > dur_max:
                break
            corpo = " ".join(texto)
            baixo = corpo.lower()
            pontos = sum(baixo.count(g) for g in GANCHOS) * 2
            pontos += baixo.count("?") * 2 + len(re.findall(r"\d", baixo)) * 0.3
            pontos += min(len(corpo.split()), 90) * 0.1          # densidade de fala
            pontos += 2.5 if i == 0 else 0                        # a abertura costuma ser boa
            candidatos.append({"inicio": ini, "fim": fim, "texto": corpo, "pontos": pontos})
    candidatos.sort(key=lambda c: -c["pontos"])
    escolhidos: list[dict] = []
    for c in candidatos:
        if all(c["fim"] <= e["inicio"] or c["inicio"] >= e["fim"] for e in escolhidos):
            escolhidos.append(c)
        if len(escolhidos) >= quantidade:
            break
    escolhidos.sort(key=lambda c: c["inicio"])
    return escolhidos


# ------------------------------------------------------------------ legenda (.ass) e corte vertical
def _t(seg: float) -> str:
    h = int(seg // 3600); m = int(seg % 3600 // 60); s = seg % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass(palavras: list[dict], ini: float, fim: float, caminho: pathlib.Path, por_grupo: int = 3) -> None:
    cab = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           "Style: Leg,Arial,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,320,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    dentro = [p for p in palavras if p["fim"] > ini and p["inicio"] < fim]
    linhas = []
    for k in range(0, len(dentro), por_grupo):
        grupo = dentro[k:k + por_grupo]
        a = max(grupo[0]["inicio"], ini) - ini
        b = min(grupo[-1]["fim"], fim) - ini
        txt = re.sub(r"[\\{}\r\n]", " ", " ".join(w["texto"] for w in grupo)).upper()
        linhas.append(f"Dialogue: 0,{_t(a)},{_t(b)},Leg,,0,0,0,,{txt}")
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")


def gerar_corte(entrada: pathlib.Path, ini: float, fim: float, palavras: list[dict], saida: pathlib.Path,
                legendar: bool = True) -> None:
    entrada, saida = entrada.resolve(), saida.resolve()
    if not all(math.isfinite(float(x)) for x in (ini, fim)) or not 0 <= ini < fim:
        raise ValueError("Tempos de corte inválidos.")
    saida.parent.mkdir(parents=True, exist_ok=True)
    # fundo: a própria imagem ampliada e borrada; frente: o vídeo inteiro cabendo na largura (padrão Shorts)
    filtro = ("[0:v]split[a][b];"
              "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:4[bg];"
              "[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]")
    mapa = "[v]"
    if legendar:
        ass = saida.with_suffix(".ass")
        _ass(palavras, ini, fim, ass)
        filtro += ";[v]subtitles=" + ass.name + ":force_style='Fontname=Arial'[vv]"
        mapa = "[vv]"
    parcial = saida.with_suffix(".partial.mp4")
    cmd = [_ffmpeg(), "-nostdin", "-y", "-ss", f"{ini:.2f}", "-i", str(entrada), "-t", f"{fim-ini:.2f}",
           "-filter_complex", filtro, "-map", mapa, "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k",
           "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", parcial.name]
    try:
        r = subprocess.run(cmd, cwd=str(saida.parent), capture_output=True, text=True, timeout=1800,
                           **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
        if r.returncode != 0 or not parcial.is_file() or not parcial.stat().st_size:
            raise RuntimeError("Falha ao gerar o corte: " + (r.stderr or "")[-300:])
        parcial.replace(saida)
    finally:
        parcial.unlink(missing_ok=True)
        saida.with_suffix(".ass").unlink(missing_ok=True)


# ------------------------------------------------------------------ orquestra tudo
def validar_trechos(trechos, palavras, dur_min, dur_max, quantidade):
    fim_video = palavras[-1]["fim"] if palavras else 0
    validos = []
    for trecho in trechos[:max(1, min(10, int(quantidade)))]:
        ini, fim = float(trecho["inicio"]), float(trecho["fim"])
        if not all(math.isfinite(v) for v in (ini, fim)) or not 0 <= ini < fim <= fim_video + .1:
            raise ValueError("Trecho fora do vídeo ou tempo inválido.")
        if not dur_min - .1 <= fim - ini <= dur_max + .1:
            raise ValueError("Trecho fora da duração configurada.")
        if any(ini < x["fim"] and fim > x["inicio"] for x in validos):
            raise ValueError("Trechos sobrepostos.")
        validos.append({"inicio": ini, "fim": fim, "titulo": str(trecho.get("titulo") or "")[:95],
            "texto": " ".join(p["texto"] for p in palavras if p["fim"] > ini and p["inicio"] < fim)})
    return sorted(validos, key=lambda x: x["inicio"])


def produzir(app, fonte, nome="", quantidade=3, dur_min=15, dur_max=60, legendar=True, trechos=None,
             seletor=None, max_duracao_seg=7200, cache_transcricao=None, progresso_transcricao=None):
    resultado = {"ok": False, "arquivos": [], "erros": []}
    try:
        _ffmpeg()
        if not 1 <= float(dur_min) <= float(dur_max) <= 180:
            raise ValueError("Duração deve estar entre 1 e 180 segundos.")
        destino = _pasta(app) / _nome(nome or "cortes")
        destino.mkdir(parents=True, exist_ok=True)
        entrada = baixar(fonte, destino) if re.match(r"https?://", fonte.strip()) else pathlib.Path(fonte).expanduser().resolve()
        if not entrada.is_file():
            raise ValueError("Vídeo não encontrado.")
        cache = pathlib.Path(cache_transcricao) if cache_transcricao else None
        if cache and cache.exists():
            palavras = json.loads(cache.read_text(encoding="utf-8"))
        else:
            palavras = transcrever_palavras(app.voz, entrada, max_duracao_seg, progresso=progresso_transcricao)
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                temp = cache.with_suffix(".tmp")
                temp.write_text(json.dumps(palavras, ensure_ascii=False), encoding="utf-8")
                temp.replace(cache)
        if not palavras:
            raise ValueError("Nenhuma fala encontrada.")
        if palavras[-1]["fim"] > max_duracao_seg:
            raise ValueError("Vídeo excede duração máxima configurada.")
        if trechos:
            escolhidos = validar_trechos(trechos, palavras, dur_min, dur_max, quantidade)
        else:
            escolhidos = escolher_trechos(palavras, quantidade, dur_min, dur_max)
            if seletor:
                escolhidos = validar_trechos(seletor(palavras, escolhidos), palavras, dur_min, dur_max, quantidade)
        if not escolhidos:
            raise ValueError("Nenhum trecho atende à duração configurada.")
        for i, trecho in enumerate(escolhidos, 1):
            arq = destino / f"corte_{i:02d}.mp4"
            try:
                gerar_corte(entrada, trecho["inicio"], trecho["fim"], palavras, arq, legendar)
                resultado["arquivos"].append({**trecho, "caminho": str(arq.resolve()), "duracao": trecho["fim"]-trecho["inicio"]})
            except Exception as erro:
                resultado["erros"].append(f"Corte {i}: {erro}")
        resultado["ok"] = bool(resultado["arquivos"])
        resultado["pasta"] = str(destino)
        manifesto = destino / "manifesto.json"
        temporario = manifesto.with_suffix(".tmp")
        temporario.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(manifesto)
    except Exception as erro:
        resultado["erros"].append(str(erro))
    return resultado


def criar_cortes(app, fonte, nome="", quantidade=3, dur_min=15, dur_max=60, legendar=True, trechos=None):
    r = produzir(app, fonte, nome, quantidade, dur_min, dur_max, legendar, trechos)
    if not r["ok"]:
        return "Não gerei cortes: " + "; ".join(r["erros"])
    return f"Gerei {len(r['arquivos'])} corte(s) em {r['pasta']}. " + "; ".join(r["erros"])
