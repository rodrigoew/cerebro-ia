"""Planejamento persistente de reposição de fila e sinais editoriais locais."""
from __future__ import annotations

from collections import defaultdict
import datetime as dt
import json
import re
import time
from zoneinfo import ZoneInfo

from fontes_auto import normalizar, permissao

PADRAO = {"ativo": False, "intervalo_min": 30, "reposicao_min": 60, "min_posts_canal": 2}
IGNORAR = set("para como com uma que dos das por pelo pela esse essa isso hoje live podcast cortes corte melhores momentos oficial episodio canal parte sobre mais muito jogo jogar games gameplay streamer entrevista treino voce quando porque todos elas eles video videos foi tem nao sim seja sem seus suas novo nova agora aqui ainda depois durante nossa nosso antes apos serie".split())


def configuracao(catalogo):
    r = {**PADRAO, **catalogo.get("rotina", {})}
    if type(r["ativo"]) is not bool:
        raise ValueError("rotina.ativo deve ser booleano.")
    for campo, minimo, maximo in (("intervalo_min", 5, 360), ("reposicao_min", 30, 1440), ("min_posts_canal", 1, 10)):
        if type(r[campo]) is not int or not minimo <= r[campo] <= maximo:
            raise ValueError("rotina." + campo + " inválido.")
    pautas = r.get("pautas", [])
    if not isinstance(pautas, list) or len(pautas) > 50:
        raise ValueError("Até 50 pautas prioritárias.")
    for p in pautas:
        if not isinstance(p,dict) or not isinstance(p.get("tema"),str) or not isinstance(p.get("consulta"),str) or not 1 <= len(p["consulta"]) <= 180:
            raise ValueError("Pauta precisa de tema e consulta curta.")
        for chave in ("inicio", "fim"):
            dt.date.fromisoformat(p[chave])
        if p["inicio"] > p["fim"]:
            raise ValueError("Prazo da pauta invertido.")
    return r


def pautas_ativas(catalogo, tema, data):
    return [p["consulta"] for p in configuracao(catalogo).get("pautas", [])
            if p["tema"] == tema and p["inicio"] <= data <= p["fim"]]


def extrair_sinais(rows):
    """Recorrência em canais distintos, sem alegar volume de buscas ou tendências externas."""
    apoio = defaultdict(set)
    for r in rows:
        palavras = re.findall(r"[a-z0-9]+", normalizar(r["titulo"]))
        for i,w in enumerate(palavras[:-1]):
            if w == "gta" and palavras[i+1] in ("6", "vi"):
                apoio["gta 6"].add(r["fonte"])
        for tamanho in (2, 3):
            for i in range(len(palavras)-tamanho+1):
                trecho = palavras[i:i+tamanho]
                if any(w in IGNORAR or len(w) < 2 for w in trecho):
                    continue
                termo = " ".join(trecho)
                apoio[termo].add(r["fonte"])
    return [k for k in sorted(apoio, key=lambda k:(-len(apoio[k]),-len(k),k)) if len(apoio[k]) >= 3][:4]


class RotinaCriador:
    def __init__(self, app, banco):
        self.app, self.banco = app, banco

    def avisar(self, chave, texto):
        # Um aviso por motivo a cada 24h; nunca encaminha mensagens para terceiros.
        agora = time.time()
        if agora - float(self.banco.get("rotina_aviso_"+chave, "0")) < 86400:
            return
        notificar = getattr(self.app, "notificar", None)
        if callable(notificar):
            try:
                notificar("Rotina de conteúdo", texto, "atencao", "nucleo")
            except Exception:
                return
        self.banco.set("rotina_aviso_"+chave, agora)
        self.banco.evento("rotina_aviso", texto)

    def ciclo(self, cfg, catalogo):
        r = configuracao(catalogo)
        if not r["ativo"] or not cfg.get("ativo"):
            return
        agora = time.time()
        if agora - float(self.banco.get("rotina_ultima", "0")) < r["intervalo_min"]*60:
            return
        data = dt.datetime.now(ZoneInfo(cfg["fuso"])).date().isoformat()
        planos, temas_baixos = [], set()
        for canal in cfg["canais"]:
            if not canal.get("ativo", True):
                continue
            elegiveis = [f["id"] for f in cfg["fontes"] if f.get("ativo", True) and f["tema"] == canal["tema"]
                         and f.get("direitos") in ("autorizado","proprio","licenca_livre") and bool(f.get("comprovante"))
                         and canal["plataforma"] in f.get("plataformas", ["youtube","tiktok"])
                         and (f.get("revisao_automatica") is True or (f.get("formato_revisado") is True and f.get("publicar_automaticamente") is True))]
            n = 0
            if elegiveis:
                n = self.banco.q("SELECT COUNT(*) n FROM posts p JOIN fontes f ON f.id=p.fonte_id WHERE p.canal=? AND f.fonte_id IN (" + ",".join("?" for _ in elegiveis) + ") AND (p.estado IN ('pronto','enviando','verificar_envio') OR (p.estado='agendado' AND p.agendado>?))", (canal["id"],*elegiveis,dt.datetime.now(dt.timezone.utc).isoformat()))[0]["n"]
            tem_fontes = bool(elegiveis)
            falta = max(0, r["min_posts_canal"]-n)
            planos.append({"canal":canal["id"], "tema":canal["tema"], "fila":n,"faltam":falta,"fonte_permitida":tem_fontes})
            if falta:
                temas_baixos.add(canal["tema"])
                if not tem_fontes:
                    self.avisar("fonte_"+canal["id"], f"{canal['id']}: fila baixa sem fonte com permissão cadastrada. Busca de metadados continua; não há liberação automática de direitos.")
            if not canal.get("buffer_channel_id"):
                self.avisar("conta_"+canal["id"], f"{canal['id']}: conectar a conta Buffer para permitir agendamento.")
        for tema in {c["tema"] for c in cfg["canais"] if c.get("ativo", True)}:
            rows = self.banco.q("SELECT titulo,fonte FROM descobertas WHERE tema=? AND fonte LIKE 'achado-%' AND criado>? ORDER BY criado DESC LIMIT 300", (tema, agora-86400))
            termos = extrair_sinais(rows)
            consultas = pautas_ativas(catalogo, tema, data) + [t+" entrevista melhores momentos" for t in termos]
            self.banco.set("rotina_consultas_"+tema, json.dumps(consultas[:10],ensure_ascii=False))
            if tema in temas_baixos:
                chave = "rotina_reposicao_"+tema
                if agora - float(self.banco.get(chave, "0")) >= r["reposicao_min"]*60:
                    self.banco.set("online_tema_"+tema, 0)
                    for f in catalogo["fontes"]:
                        if f["tema"] == tema and permissao(f):
                            self.banco.set("online_busca_"+f["id"], 0)
                    self.banco.set(chave, agora)
                    self.banco.evento("rotina_reposicao", "Busca antecipada para repor fila de "+tema)
        erros = self.banco.q("SELECT COUNT(*) n FROM posts WHERE estado IN ('bloqueado','falha_publicacao','verificar_envio')")[0]["n"]
        if erros:
            self.avisar("envios", f"Há {erros} envio(s) com bloqueio ou confirmação pendente. O Núcleo preservou o histórico e não repete envios incertos.")
        self.banco.set("rotina_plano", json.dumps({"atualizado":agora,"canais":planos,"reposicao_temas":sorted(temas_baixos)},ensure_ascii=False))
        self.banco.set("rotina_ultima", agora)

    def status(self):
        return json.loads(self.banco.get("rotina_plano", "{}"))
