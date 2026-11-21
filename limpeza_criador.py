"""Remove apenas mídias geradas/baixadas pelo criador após publicação confirmada."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import cortes
from publicacao import sha256

UTC = dt.timezone.utc


def configuracao(cfg):
    c = cfg.get("limpeza", {})
    if not isinstance(c, dict):
        raise ValueError("limpeza deve ser um objeto JSON.")
    modo = c.get("modo", "automatico")
    horas = float(c.get("reter_horas", 24))
    if modo not in ("automatico", "propor", "desativado") or not math.isfinite(horas) or not 0 <= horas <= 8760:
        raise ValueError("Limpeza: modo automatico/propor/desativado; reter_horas entre 0 e 8760.")
    return {"modo": modo, "reter_horas": horas}


def seguro(caminho, base):
    """Sem exclusão recursiva; recusa links e junctions antes de validar contenção."""
    p, raiz = Path(caminho).absolute(), Path(base).absolute()
    if raiz not in p.parents:
        raise ValueError("Arquivo fora da pasta gerenciada.")
    for atual in (p, *p.parents):
        if atual.exists() or atual.is_symlink():
            st = atual.lstat()
            if atual.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
                raise ValueError("Limpeza recusada em link/junction.")
        if atual == raiz:
            break
    real = p.resolve()
    if raiz.resolve() not in real.parents:
        raise ValueError("Caminho resolvido fora da pasta gerenciada.")
    return real


class LimpezaCriador:
    def __init__(self, app, banco):
        self.app, self.banco = app, banco
        self.entrada = Path(app.saida) / "criador_entrada_online"
        self.banco.x("""CREATE TABLE IF NOT EXISTS limpeza_arquivos (
            chave TEXT PRIMARY KEY,fonte INTEGER NOT NULL,caminho TEXT NOT NULL,
            estado TEXT NOT NULL,bytes INTEGER NOT NULL,quando TEXT NOT NULL,erro TEXT)""")

    @staticmethod
    def publicados(posts, limite):
        if not posts:
            return False
        for p in posts:
            if p["estado"] != "publicado" or not p["remoto_id"] or not p["publicado"]:
                return False
            try:
                quando = dt.datetime.fromisoformat(p["publicado"])
                if not quando.tzinfo or quando > limite:
                    return False
            except (ValueError, TypeError):
                return False
        return True

    def plano(self, cfg):
        c = configuracao(cfg)
        limite = dt.datetime.now(UTC) - dt.timedelta(hours=c["reter_horas"])
        plano = []
        for fonte in self.banco.q("SELECT * FROM fontes WHERE estado='concluido' ORDER BY id"):
            posts = self.banco.q("SELECT * FROM posts WHERE fonte_id=?", (fonte["id"],))
            if not self.publicados(posts, limite):
                continue
            alvos = []
            for post in posts:
                # Só o perfil automático específico desse job/canal, nunca a pasta de cortes inteira.
                perfil = hashlib.sha256(post["canal"].encode()).hexdigest()[:12]
                pasta = cortes._pasta(self.app) / f"auto-{fonte['id']}-{perfil}"
                alvos.append((post["caminho"], pasta, post["hash"], "corte"))
            # Somente originais baixados e registrados pelo monitor online são descartáveis.
            if str(fonte["fonte_id"]).startswith("online-"):
                origem = self.banco.q("SELECT * FROM descobertas WHERE caminho=? AND estado='importado' AND fonte=?",
                    (fonte["caminho"], fonte["fonte_id"][7:]))
                if origem:
                    alvos.append((fonte["caminho"], self.entrada / origem[0]["fonte"], fonte["hash"], "original_baixado"))
            vistos = set()
            for caminho, base, digest, tipo in alvos:
                chave = hashlib.sha256((str(Path(caminho).absolute()) + ":" + digest).encode()).hexdigest()
                if chave in vistos:
                    continue
                vistos.add(chave)
                if self.banco.q("SELECT 1 FROM limpeza_arquivos WHERE chave=? AND estado='apagado'", (chave,)):
                    continue
                erro, tamanho = "", 0
                try:
                    if not re.fullmatch(r"[a-f0-9]{64}", digest):
                        raise ValueError("Hash de mídia inválido.")
                    arq = seguro(caminho, base)
                    # Arquivo compartilhado com qualquer publicação pendente deve permanecer.
                    refs = self.banco.q("SELECT * FROM posts WHERE caminho=?", (caminho,))
                    if refs and not self.publicados(refs, limite):
                        continue
                    usadas = self.banco.q("SELECT * FROM fontes WHERE caminho=? AND id!=?", (caminho, fonte["id"]))
                    if any(f["estado"] != "concluido" or not self.publicados(
                            self.banco.q("SELECT * FROM posts WHERE fonte_id=?", (f["id"],)), limite) for f in usadas):
                        continue
                    if arq.exists():
                        if not arq.is_file():
                            raise ValueError("Alvo não é um arquivo.")
                        tamanho = arq.stat().st_size
                except (OSError, ValueError):
                    erro = "Caminho ou arquivo exige revisão manual."
                plano.append({"chave": chave, "fonte": fonte["id"], "caminho": caminho,
                              "base": str(base), "hash": digest, "tipo": tipo, "bytes": tamanho, "erro": erro})
                if len(plano) >= 30:
                    return plano
        return plano

    def propor(self, fonte, itens, cfg):
        chave = "limpeza_lembrete:" + str(fonte)
        memoria = getattr(self.app, "memoria", None)
        if self.banco.get(chave) or memoria is None:
            return
        texto = f"Revisar limpeza dos vídeos publicados da fonte #{fonte}: {sum(i['bytes'] for i in itens)/1024**2:.1f} MB. Consulte a fila de limpeza do criador."
        # Deduplica também se o processo cair após salvar o lembrete no banco da memória.
        existente = memoria.q("SELECT id FROM lembretes WHERE texto=?", (texto,))
        if existente:
            ident = existente[0]["id"]
        else:
            ident = memoria.x("INSERT INTO lembretes(texto,data,hora,criado_em) VALUES(?,?,NULL,?)",
                (texto, dt.datetime.now(ZoneInfo(cfg["fuso"])).date().isoformat(), dt.datetime.now(UTC).isoformat()))
        self.banco.set(chave, ident)
        notificar = getattr(self.app, "notificar", None)
        if callable(notificar):
            notificar("Limpeza de vídeos", texto, "atencao", "nucleo")

    def ciclo(self, cfg):
        c = configuracao(cfg)
        if c["modo"] == "desativado" or cfg.get("ativo") is not True:
            return
        pendencias = {}
        for item in self.plano(cfg):
            erro = item["erro"]
            estado, liberados = "proposto", 0
            if not erro:
                try:
                    if not seguro(item["caminho"], item["base"]).exists():
                        estado = "apagado"  # Reconhece também a limpeza manual.
                except (OSError, ValueError):
                    erro = "Caminho exige revisão manual."
            if c["modo"] == "automatico" and not erro:
                try:
                    # Revalida imediatamente antes da exclusão; nunca percorre/apaga diretórios.
                    arq = seguro(item["caminho"], item["base"])
                    if arq.exists():
                        if sha256(arq) != item["hash"]:
                            raise ValueError("Mídia alterada desde a criação do corte.")
                        liberados = arq.stat().st_size
                        arq.unlink()
                    estado = "apagado"
                except (OSError, ValueError):
                    erro = "Arquivo alterado, ocupado ou inacessível; revisar manualmente."
            if erro:
                estado = "revisar"
            self.banco.x("""INSERT INTO limpeza_arquivos VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(chave) DO UPDATE SET estado=excluded.estado,bytes=excluded.bytes,
                quando=excluded.quando,erro=excluded.erro""",
                (item["chave"], item["fonte"], item["caminho"], estado,
                 liberados if estado == "apagado" else item["bytes"], dt.datetime.now(UTC).isoformat(), erro or None))
            if estado != "apagado":
                pendencias.setdefault(item["fonte"], []).append(item)
        for fonte, itens in pendencias.items():
            self.propor(fonte, itens, cfg)
        memoria = getattr(self.app, "memoria", None)
        if memoria is not None:
            for row in self.banco.q("SELECT chave,valor FROM estado WHERE chave LIKE 'limpeza_lembrete:%'"):
                fonte = row["chave"].split(":", 1)[1]
                registros = self.banco.q("SELECT estado FROM limpeza_arquivos WHERE fonte=?", (fonte,))
                if registros and all(r["estado"] == "apagado" for r in registros):
                    memoria.x("UPDATE lembretes SET feito=1 WHERE id=?", (row["valor"],))

    def status(self, cfg):
        return {**configuracao(cfg), "resumo": self.banco.q("""SELECT estado,COUNT(*) arquivos,SUM(bytes) bytes
            FROM limpeza_arquivos GROUP BY estado"""),
            "pendencias": self.banco.q("""SELECT fonte,caminho,estado,bytes,erro FROM limpeza_arquivos
            WHERE estado!='apagado' ORDER BY quando LIMIT 30"""),
            "erro": self.banco.get("limpeza_erro"),
            "escopo": "Mídias locais geradas pelo criador e originais baixados pelo monitor; hospedagem Cloudinary preservada."}
