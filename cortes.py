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
    return shutil.which("ffmpeg") or "ffmpeg"


def _nome(t: str) -> str:
    return re.sub(r"[^\w.-]+", "-", str(t or "corte").strip()).strip("-.")[:50] or "corte"


# ------------------------------------------------------------------ baixar (opcional)
def baixar(url: str, destino: pathlib.Path) -> pathlib.Path:
    if not shutil.which("yt-dlp"):
        raise RuntimeError("Para baixar de um link falta o yt-dlp. Rode o instalador (Instalar o que falta) uma vez com internet, "
                           "ou me dê o arquivo do vídeo já baixado.")
    destino.mkdir(parents=True, exist_ok=True)
    saida = destino / "fonte.%(ext)s"
    r = subprocess.run(["yt-dlp", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4", "-o", str(saida), url],
                       capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError("Não consegui baixar esse vídeo: " + (r.stderr or "").strip()[-300:])
    arquivos = sorted(destino.glob("fonte.*"))
    if not arquivos:
        raise RuntimeError("O download não gerou arquivo.")
    return arquivos[0]


# ------------------------------------------------------------------ transcrição em palavras
def transcrever_palavras(voz, caminho: pathlib.Path) -> list[dict]:
    """Devolve [{inicio, fim, texto}] por palavra, usando o Whisper já instalado."""
    import numpy as np
    wav = caminho.with_suffix(".16k.wav")
    subprocess.run([_ffmpeg(), "-y", "-i", str(caminho), "-ac", "1", "-ar", "16000", "-vn", str(wav)],
                   capture_output=True, timeout=1800)
    audio = np.frombuffer(wav.read_bytes()[44:], dtype=np.int16).astype(np.float32) / 32768.0
    modelo = voz.carregar_whisper()
    na_gpu = getattr(voz, "_whisper_gpu", False)
    segmentos, _ = modelo.transcribe(audio, language="pt", beam_size=3 if na_gpu else 1, word_timestamps=True,
                                     vad_filter=True, condition_on_previous_text=False)
    palavras = []
    for seg in segmentos:
        for p in (seg.words or []):
            texto = p.word.strip()
            if texto:
                palavras.append({"inicio": float(p.start), "fim": float(p.end), "texto": texto})
    try:
        wav.unlink()
    except Exception:
        pass
    return palavras


# ------------------------------------------------------------------ escolher os melhores trechos
def _frases(palavras: list[dict]) -> list[dict]:
    frases, atual = [], []
    for p in palavras:
        atual.append(p)
        if re.search(r"[.!?…]$", p["texto"]):
            frases.append(atual); atual = []
    if atual:
        frases.append(atual)
    return [{"inicio": f[0]["inicio"], "fim": f[-1]["fim"], "texto": " ".join(w["texto"] for w in f)} for f in frases if f]


def escolher_trechos(palavras: list[dict], quantidade: int = 3, dur_min: float = 15, dur_max: float = 60) -> list[dict]:
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
            break
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
           "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, "
           "MarginL, MarginR, MarginV, Encoding\n"
           "Style: Leg,Arial,78,&H00FFFFFF,&H00000000,&H90000000,1,5,2,2,60,60,320,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    dentro = [p for p in palavras if p["fim"] > ini and p["inicio"] < fim]
    linhas = []
    for k in range(0, len(dentro), por_grupo):
        grupo = dentro[k:k + por_grupo]
        a = max(grupo[0]["inicio"], ini) - ini
        b = min(grupo[-1]["fim"], fim) - ini
        txt = " ".join(w["texto"] for w in grupo).replace("{", "(").replace("}", ")").upper()
        linhas.append(f"Dialogue: 0,{_t(a)},{_t(b)},Leg,{txt}")
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")


def gerar_corte(entrada: pathlib.Path, ini: float, fim: float, palavras: list[dict], saida: pathlib.Path,
                legendar: bool = True) -> None:
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
    cmd = [_ffmpeg(), "-y", "-ss", f"{ini:.2f}", "-to", f"{fim:.2f}", "-i", str(entrada.resolve()),
           "-filter_complex", filtro, "-map", mapa, "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k",
           "-movflags", "+faststart", saida.name]
    r = subprocess.run(cmd, cwd=str(saida.parent), capture_output=True, text=True, timeout=1800)
    try:
        saida.with_suffix(".ass").unlink()
    except Exception:
        pass
    if r.returncode != 0 or not saida.exists():
        raise RuntimeError("Falha ao gerar o corte: " + (r.stderr or "").strip()[-300:])


# ------------------------------------------------------------------ orquestra tudo
def criar_cortes(app, fonte: str, nome: str = "", quantidade: int = 3, dur_min: float = 15, dur_max: float = 60,
                 legendar: bool = True, trechos: list | None = None) -> str:
    if not shutil.which("ffmpeg"):
        return "Falta o ffmpeg (processa o vídeo). Rode o instalador (Instalar o que falta) uma vez."
    nome = _nome(nome or "cortes")
    destino = _pasta(app) / nome
    destino.mkdir(parents=True, exist_ok=True)
    # 1) o vídeo: arquivo local ou link
    if re.match(r"https?://", fonte.strip()):
        try:
            entrada = baixar(fonte.strip(), destino)
        except Exception as erro:
            return str(erro)
    else:
        entrada = pathlib.Path(fonte).expanduser()
        if not entrada.exists():
            return f"Não achei o vídeo em {entrada}. Mande o caminho do arquivo ou um link."
    voz = getattr(app, "voz", None)
    if voz is None or not voz.tem_whisper():
        return "Para achar os trechos e legendar eu preciso do reconhecimento de voz (Whisper) instalado. Rode o instalador."
    # 2) transcrição
    try:
        palavras = transcrever_palavras(voz, entrada)
    except Exception as erro:
        return f"Não consegui transcrever o vídeo ({type(erro).__name__}). Veja se o arquivo tem áudio."
    if not palavras:
        return "Não encontrei fala no vídeo para gerar cortes com legenda."
    # 3) trechos (automáticos ou os que você indicou em segundos: [{inicio, fim}])
    if trechos:
        escolhidos = [{"inicio": float(t["inicio"]), "fim": float(t["fim"]),
                       "texto": ""} for t in trechos if t.get("fim", 0) > t.get("inicio", 0)]
    else:
        escolhidos = escolher_trechos(palavras, int(quantidade), float(dur_min), float(dur_max))
    if not escolhidos:
        return "Não achei trechos bons nesse tamanho. Tente aumentar a duração máxima ou me indicar os tempos."
    # 4) corta
    feitos = []
    for i, t in enumerate(escolhidos, 1):
        arq = destino / f"corte_{i:02d}.mp4"
        try:
            gerar_corte(entrada, t["inicio"], t["fim"], palavras, arq, legendar)
            dur = t["fim"] - t["inicio"]
            previa = (t.get("texto") or "").strip()[:70]
            feitos.append(f"corte_{i:02d}.mp4 ({dur:.0f}s{' — ' + previa if previa else ''})")
        except Exception as erro:
            feitos.append(f"corte_{i:02d}: falhou ({str(erro)[:80]})")
    return (f"Gerei {sum('falhou' not in f for f in feitos)} corte(s) em {destino}:\n- " + "\n- ".join(feitos)
            + "\nAbra a pasta, revise e publique você mesmo o que tiver direito de usar.")
