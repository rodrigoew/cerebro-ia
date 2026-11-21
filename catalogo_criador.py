"""Catálogo recarregável e importação atômica de cadastros, sem execução de código."""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
from pathlib import Path
import re
import shutil
import sys
import uuid


def validar(c):
    from fontes_auto import url_canal
    from regras_fontes import escopo_video, escopo_serie
    if (not isinstance(c, dict) or type(c.get("ativo")) is not bool
            or not isinstance(c.get("fontes"), list) or len(c["fontes"]) > 100):
        raise ValueError("Catálogo precisa de ativo booleano e até 100 fontes.")
    from rotina_criador import configuracao
    configuracao(c)
    ids = set()
    for f in c["fontes"]:
        if (not isinstance(f, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,55}", str(f.get("id", "")))
                or f["id"] in ids or not isinstance(f.get("tema"), str) or not f["tema"].strip()):
            raise ValueError("Fonte precisa de id único e tema.")
        ids.add(f["id"])
        if f.get("url"):
            url_canal(f["url"])
        elif not (f.get("direitos") == "pendente" and f.get("consultas")):
            raise ValueError("Fonte precisa de URL de origem; monitores podem usar somente consultas.")
        if "videos_permitidos" in f and not escopo_video(f):
            raise ValueError("videos_permitidos deve conter de 1 a 20 IDs reais de episódios.")
        if "uploader_id" in f and not escopo_serie(f):
            raise ValueError("Escopo por perfil exige @perfil, série e palavras do tema.")
        if "duracao_min_seg" in f and (type(f["duracao_min_seg"]) is not int or not 1 <= f["duracao_min_seg"] <= 7200):
            raise ValueError("duracao_min_seg inválida.")
        if "videos_excluidos" in f:
            from regras_fontes import VIDEO
            if not isinstance(f["videos_excluidos"], list) or any(not isinstance(v,str) or not VIDEO.fullmatch(v) for v in f["videos_excluidos"]):
                raise ValueError("videos_excluidos precisa de IDs de vídeo.")
        espera = float(f.get("aguardar_horas", 0))
        if not math.isfinite(espera) or not 0 <= espera <= 8760:
            raise ValueError("aguardar_horas inválido.")
        for campo in ("ativo", "formato_revisado", "publicar_automaticamente", "ia_sintetica",
                      "revisao_automatica", "publicacao_catalogo"):
            if campo in f and type(f[campo]) is not bool:
                raise ValueError(campo + " deve ser true ou false.")
        for campo in ("consultas", "serie", "palavras_tema", "excluir_titulos", "videos_excluidos"):
            if campo in f and (not isinstance(f[campo], list) or len(f[campo]) > 100
                    or any(not isinstance(t, str) or not 0 < len(t.strip()) <= 180 for t in f[campo])):
                raise ValueError(campo + " deve ser lista de textos curtos.")
    buscas = c.get("buscas", {})
    if not isinstance(buscas, dict):
        raise ValueError("buscas deve mapear temas para consultas.")
    for tema, consultas in buscas.items():
        if (not isinstance(tema, str) or not isinstance(consultas, list) or not 1 <= len(consultas) <= 100
                or any(not isinstance(q, str) or not 0 < len(q.strip()) <= 180 for q in consultas)):
            raise ValueError("Cada tema precisa de 1 a 100 consultas curtas.")
    for campo, minimo, maximo in (("max_buscas_ciclo", 1, 10), ("intervalo_min", 30, 10080),
                                  ("max_downloads_dia", 0, 8), ("max_armazenamento_mb", 0, 1000000)):
        if campo in c and (type(c[campo]) is not int or not minimo <= c[campo] <= maximo):
            raise ValueError(campo + " fora do limite.")
    if "busca_por_tema" in c and type(c["busca_por_tema"]) is not bool:
        raise ValueError("busca_por_tema deve ser booleano.")
    return c


def carregar(raiz, padrao):
    raiz = Path(raiz)
    seed = raiz / "catalogo_fontes.json"
    # PyInstaller separa dados empacotados da pasta de configurações pessoal.
    if not seed.is_file() and getattr(sys, "frozen", False):
        seed = Path(getattr(sys, "_MEIPASS", raiz)) / "catalogo_fontes.json"
    c = json.loads(seed.read_text(encoding="utf-8-sig")) if seed.is_file() else copy.deepcopy(padrao)
    pessoal = raiz / "fontes_online.json"
    if pessoal.is_file():
        local = json.loads(pessoal.read_text(encoding="utf-8-sig"))
        # Arquivos antigos continuam sendo uma substituição completa, inclusive pausas.
        if local.get("mesclar_catalogo") is not True:
            return validar(local)
        fontes = {f["id"]: f for f in c["fontes"]}
        fontes.update({f["id"]: f for f in local.get("fontes", [])})
        c = {**c, **local, "fontes": list(fontes.values()),
             "buscas": {**c.get("buscas", {}), **local.get("buscas", {})}}
    return validar(c)


def importar(raiz, arquivo, padrao, aplicar=False):
    """Prévia por padrão; --aplicar grava catálogo completo com backup e replace."""
    raiz, arquivo = Path(raiz), Path(arquivo)
    if arquivo.stat().st_size > 2 * 1024**2:
        raise ValueError("Catálogo excede 2 MB.")
    novo = validar(json.loads(arquivo.read_text(encoding="utf-8-sig")))
    atual = carregar(raiz, padrao)
    ids = {f["id"] for f in atual["fontes"]}
    r = {"aplicado": False, "fontes": len(novo["fontes"]),
         "adicionadas": [f["id"] for f in novo["fontes"] if f["id"] not in ids],
         "aviso": "Importação substitui o cadastro local completo. Direitos e opt-in são explícitos; credenciais não fazem parte do catálogo."}
    if not aplicar:
        return r
    destino = raiz / "fontes_online.json"
    if destino.resolve() == arquivo.resolve():
        raise ValueError("Use um arquivo de entrada diferente de fontes_online.json.")
    if destino.exists():
        backup = destino.with_name("fontes_online.backup-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6] + ".json")
        shutil.copy2(destino, backup)
        r["backup"] = str(backup)
    temp = destino.with_name(destino.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temp.write_text(json.dumps(novo, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(destino)
    finally:
        temp.unlink(missing_ok=True)
    r["aplicado"] = True
    return r
