"""Regras cadastradas de fontes; escopo inicial limitado ao episódio revisado."""
from __future__ import annotations

import datetime as dt
import math
import json
from pathlib import Path
import re
import unicodedata

UTC = dt.timezone.utc
VIDEO = re.compile(r"[A-Za-z0-9_-]{11}")
VACA_CAST = {
    "id": "vacacast-rodrigo-goes-203", "nome": "Vaca Cast / Evelyn Regly — Rodrigo Goes #203",
    "tema": "maromba", "url": "https://www.youtube.com/@evelynregly/videos", "channel_id": "",
    "ativo": True, "direitos": "autorizado",
    "comprovante": "https://www.vacacast.com.br/tenha-um-canal-de-cortes",
    "pagina_episodio": "https://www.vacacast.com.br/fake-natty-com-rodrigo-goes",
    "videos_permitidos": ["7MY_ZpLqIkw"], "aguardar_horas": 48,
    "titulos_episodios": {"7MY_ZpLqIkw": "Rodrigo Goes — Vaca Cast #203"},
    "plataformas": ["youtube", "tiktok"], "valido_ate": "",
    "credito": "Vaca Cast / Evelyn Regly.\nCanal de cortes oficial: https://www.youtube.com/@vacacast\nPerfil oficial do Vaca Cast: https://www.instagram.com/vacacast/",
    "creditos_obrigatorios": ["https://www.youtube.com/@vacacast", "https://www.instagram.com/vacacast/"],
    "regras_editoriais": ["Selecionar trechos próprios do episódio completo; não copiar cortes oficiais",
        "Criar título, capa e descrição próprios", "Manter contexto e respeito ao convidado; não usar títulos falsos",
        "Incluir link do episódio e do canal de cortes oficial; mencionar perfil oficial nas outras redes",
        "Conferir novamente a página de regras antes de liberar a publicação, pois elas podem mudar"],
    "formato_revisado": False, "publicar_automaticamente": False, "ia_sintetica": False,
    "revisao_automatica": True,
    "regras_verificadas_em": "2026-11-20", "perfil_instagram": "https://www.instagram.com/vacacast/"
}


def escopo_video(fonte):
    videos = fonte.get("videos_permitidos")
    return (isinstance(videos, list) and 0 < len(videos) <= 20
            and all(isinstance(v, str) and VIDEO.fullmatch(v) for v in videos))


def _normalizar(s):
    return "".join(c for c in unicodedata.normalize("NFD",str(s).casefold()) if not unicodedata.combining(c))


def escopo_serie(fonte):
    return (isinstance(fonte.get("uploader_id"), str)
            and re.fullmatch(r"@[A-Za-z0-9_.-]{1,100}", fonte["uploader_id"]) is not None
            and all(isinstance(fonte.get(k), list) and fonte[k]
                    and all(isinstance(v, str) and v.strip() for v in fonte[k])
                    for k in ("serie", "palavras_tema")))


def titulo_confere(fonte, titulo):
    titulo = _normalizar(titulo)
    return (all(not fonte.get(k) or any(_normalizar(v) in titulo for v in fonte[k])
                for k in ("serie", "palavras_tema"))
            and not any(_normalizar(v) in titulo for v in fonte.get("excluir_titulos", [])))


def origem_confere(fonte, info):
    if info.get("id") in fonte.get("videos_excluidos", []):
        return False
    if fonte.get("videos_permitidos") is not None:
        if not escopo_video(fonte) or info.get("id") not in fonte["videos_permitidos"]:
            return False
    if not titulo_confere(fonte, info.get("title", "")):
        return False
    if fonte.get("uploader_id"):
        if (not escopo_serie(fonte) or str(info.get("uploader_id", "")).casefold() != fonte["uploader_id"].casefold()):
            return False
        dur = info.get("duration")
        if not isinstance(dur, (int,float)) or not math.isfinite(dur) or dur < float(fonte.get("duracao_min_seg", 600)):
            return False
        return not fonte.get("channel_id") or info.get("channel_id") == fonte["channel_id"]
    if fonte.get("channel_id"):
        return info.get("channel_id") == fonte["channel_id"]
    return bool(escopo_video(fonte) and info.get("id") in fonte["videos_permitidos"])


def conferir_espera(fonte, info, instante=None):
    horas = float(fonte.get("aguardar_horas", 0))
    if not math.isfinite(horas) or not 0 <= horas <= 8760:
        raise ValueError("Prazo de espera inválido.")
    if not horas:
        return
    agora = instante or dt.datetime.now(UTC)
    datas = []
    for chave in ("timestamp", "release_timestamp"):
        valor = info.get(chave)
        if isinstance(valor, (int, float)) and math.isfinite(valor):
            datas.append(dt.datetime.fromtimestamp(valor, UTC))
    if not datas and re.fullmatch(r"\d{8}", str(info.get("upload_date", ""))):
        # Sem horário, considera o fim do dia UTC para não antecipar o prazo.
        datas.append(dt.datetime.strptime(info["upload_date"], "%Y%m%d").replace(tzinfo=UTC) + dt.timedelta(days=1))
    if not datas or max(datas) + dt.timedelta(hours=horas) > agora:
        raise ValueError("Aguardar prazo da fonte ou confirmar a data original do episódio.")


def conferir_creditos(fonte, descricao):
    obrigatorios = fonte.get("creditos_obrigatorios", [])
    if fonte.get("videos_permitidos"):
        if not any("https://www.youtube.com/watch?v=" + v in descricao for v in fonte["videos_permitidos"]):
            raise ValueError("Descrição sem link para o episódio permitido.")
    if any(texto not in descricao for texto in obrigatorios):
        raise ValueError("Descrição sem crédito obrigatório da fonte.")


def conferir_publicacao(fonte, descricao, caminho_original):
    conferir_creditos(fonte, descricao)
    if float(fonte.get("aguardar_horas", 0)) or fonte.get("uploader_id"):
        p = Path(caminho_original)
        meta = json.loads(p.with_suffix(p.suffix + ".json").read_text(encoding="utf-8"))
        if fonte.get("videos_permitidos") and meta.get("origem") not in fonte["videos_permitidos"]:
            raise ValueError("Metadados do episódio fora do escopo autorizado.")
        if fonte.get("uploader_id"):
            if not origem_confere(fonte, meta):
                raise ValueError("Metadados fora da série, origem ou tema permitido.")
            if "https://www.youtube.com/watch?v=" + str(meta.get("id", "")) not in descricao:
                raise ValueError("Descrição sem link para o episódio original.")
        conferir_espera(fonte, meta)


def config_publicacao(canal, fonte):
    if "ia_sintetica" in fonte:
        return {**canal, "ia_sintetica": fonte["ia_sintetica"]}
    return canal
