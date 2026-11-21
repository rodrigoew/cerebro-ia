"""Descoberta de episódios e ingestão limitada de fontes cadastradas.

Metadados públicos não constituem permissão de reutilização. A autorização
tem escopo por canal de origem, plataformas de destino e validade opcional.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import unicodedata
from urllib.parse import urlsplit
from regras_fontes import VACA_CAST, escopo_video, escopo_serie, titulo_confere, origem_confere, conferir_espera

UTC = dt.timezone.utc
CANAL = re.compile(r"UC[A-Za-z0-9_-]{22}")
VIDEO = re.compile(r"[A-Za-z0-9_-]{11}")
CATALOGO = {"ativo": True, "busca_por_tema": True, "intervalo_min": 360, "max_downloads_dia": 2,
    "max_armazenamento_mb": 12000, "fontes": [
        {"id": "cariani-monitor", "nome": "Renato Cariani", "tema": "maromba",
         "url": "https://www.youtube.com/@renatocariani/videos", "ativo": True,
         "channel_id": "", "direitos": "pendente", "comprovante": "",
         "plataformas": ["youtube", "tiktok"], "valido_ate": "",
         "formato_revisado": False, "publicar_automaticamente": False}, VACA_CAST]}
BUSCAS = {"maromba": ["podcast musculação fisiculturismo", "entrevista treino bodybuilding"],
          "games": ["live melhores momentos gameplay", "streamer gameplay entrevista"]}


def normalizar(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s).lower()) if not unicodedata.combining(c))


def url_canal(url):
    p = urlsplit(str(url))
    if (p.scheme != "https" or p.netloc != "www.youtube.com" or p.query or p.fragment
            or not re.fullmatch(r"/(?:@[A-Za-z0-9_.-]+|channel/UC[A-Za-z0-9_-]{22})/(?:videos|streams)", p.path)):
        raise ValueError("Use a aba /videos ou /streams de um canal www.youtube.com em HTTPS.")
    return url


def permissao(f, instante=None):
    if (not f or f.get("ativo") is not True or f.get("direitos") not in ("proprio", "autorizado", "licenca_livre")
            or not str(f.get("comprovante") or "").strip()
            or not (CANAL.fullmatch(f.get("channel_id", "")) or escopo_video(f) or escopo_serie(f))):
        return False
    plataformas = f.get("plataformas")
    if not isinstance(plataformas, list) or not plataformas or any(p not in ("youtube", "tiktok") for p in plataformas):
        return False
    if f.get("valido_ate"):
        try:
            validade = dt.datetime.fromisoformat(f["valido_ate"])
            if not validade.tzinfo or validade <= (instante or dt.datetime.now(UTC)):
                return False
        except (ValueError, TypeError):
            return False
    return True


class Silencioso:
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass


class YouTube:
    """Sem cookies, credenciais de navegador ou alterações de restrições de acesso."""
    @staticmethod
    def opcoes():
        js = {"node": {"path": shutil.which("node")}} if shutil.which("node") else {}
        return {"quiet": True, "no_warnings": True, "logger": Silencioso(), "js_runtimes": js,
                "socket_timeout": 15, "retries": 1, "extractor_retries": 1,
                "fragment_retries": 1, "cachedir": False, "noplaylist": True}

    def listar(self, fonte):
        if fonte.get("videos_permitidos") is not None:
            if not escopo_video(fonte):
                raise ValueError("Lista de episódios permitidos inválida.")
            return [{"id": video, "title": fonte.get("titulos_episodios", {}).get(video, video)}
                    for video in fonte["videos_permitidos"]]
        if fonte.get("consultas"):
            vistos, itens = set(), []
            for consulta in fonte["consultas"][:3]:
                for item in self.pesquisar(consulta):
                    if item.get("id") not in vistos:
                        vistos.add(item.get("id")); itens.append(item)
            return itens[:30]
        import yt_dlp
        with yt_dlp.YoutubeDL({**self.opcoes(), "extract_flat": "in_playlist",
                              "playlistend": 10, "lazy_playlist": True}) as ydl:
            info = ydl.extract_info(url_canal(fonte["url"]), download=False)
            if not info:
                raise ValueError("Canal não retornou metadados.")
            return list(itertools.islice((e for e in (info.get("entries") or []) if e), 10))

    def pesquisar(self, consulta):
        import yt_dlp
        consulta = " ".join(str(consulta).split())[:180]
        if not consulta:
            return []
        with yt_dlp.YoutubeDL({**self.opcoes(), "extract_flat": "in_playlist",
                              "playlistend": 10, "lazy_playlist": True}) as ydl:
            info = ydl.extract_info("ytsearch10:" + consulta, download=False)
            if not info:
                raise ValueError("Busca não retornou metadados.")
            return list(itertools.islice((e for e in (info.get("entries") or []) if e), 10))

    def baixar(self, fonte, video, pasta, cfg):
        import cortes
        import yt_dlp
        limite = int(cfg["max_video_mb"]) * 1024**2
        reserva = int(cfg["min_espaco_livre_mb"]) * 1024**2
        prazo = time.monotonic() + 1800

        def filtrar(info, *, incomplete=False):
            if not origem_confere(fonte, info):
                return "Canal de origem diferente do autorizado."
            try:
                conferir_espera(fonte, info)
            except (ValueError, OverflowError, OSError):
                return "Aguardar o prazo exigido pela fonte e confirmar a data original."
            if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming", "post_live"):
                return "Aguardar término e processamento da live."
            dur = info.get("duration")
            if not isinstance(dur, (int, float)) or not math.isfinite(dur) or not 1 <= dur <= int(cfg["max_duracao_fonte_min"]) * 60:
                return "Duração desconhecida ou fora do limite."
            if not permissao(fonte):
                return "Autorização ausente ou vencida."
            return None

        def progresso(_):
            ocupado = sum(p.stat().st_size for p in pasta.iterdir() if p.is_file())
            if ocupado > limite or shutil.disk_usage(pasta).free < reserva or time.monotonic() > prazo:
                raise RuntimeError("Limite de armazenamento, espaço livre ou tempo atingido.")

        with yt_dlp.YoutubeDL({**self.opcoes(), "format": "bv[height<=720][ext=mp4]+ba[ext=m4a]/b[ext=mp4][height<=720]/bv[height<=720]+ba/b[height<=720]",
                              "merge_output_format": "mp4",
                              "outtmpl": str(pasta / "video.%(ext)s"), "max_filesize": limite,
                              "ffmpeg_location": cortes._ffmpeg(), "match_filter": filtrar,
                              "progress_hooks": [progresso]}) as ydl:
            # Uma única extração completa; o filtro confere o canal real antes do download.
            info = ydl.extract_info("https://www.youtube.com/watch?v=" + video, download=True)
            if not info or filtrar(info):
                raise ValueError("Episódio não passou na validação de origem/duração.")
            caminho = pasta / "video.mp4"
            if not caminho.is_file():
                caminho = Path(ydl.prepare_filename(info))
            if not caminho.is_file() or not 0 < caminho.stat().st_size <= limite:
                raise ValueError("Download incompleto ou maior que o limite.")
            return caminho, info


class FontesOnline:
    def __init__(self, raiz, saida, banco, transporte=None):
        self.raiz, self.saida, self.banco = Path(raiz), Path(saida), banco
        self.caminho = self.raiz / "fontes_online.json"
        self.entrada = self.saida / "criador_entrada_online"
        self.transporte = transporte or YouTube()
        self.banco.x("""CREATE TABLE IF NOT EXISTS descobertas (
            fonte TEXT NOT NULL, video TEXT NOT NULL, titulo TEXT NOT NULL, tema TEXT NOT NULL,
            pontuacao REAL NOT NULL, estado TEXT NOT NULL, tentativas INTEGER NOT NULL DEFAULT 0,
            proxima REAL NOT NULL DEFAULT 0, erro TEXT, criado REAL NOT NULL,
            caminho TEXT, PRIMARY KEY(fonte,video))""")
        self.banco.x("""CREATE TABLE IF NOT EXISTS canais_encontrados (
            id TEXT PRIMARY KEY,channel_id TEXT NOT NULL,tema TEXT NOT NULL,nome TEXT NOT NULL,
            url TEXT NOT NULL,ultima REAL NOT NULL,UNIQUE(channel_id,tema))""")

    def config(self):
        from catalogo_criador import carregar
        return carregar(self.raiz, CATALOGO)

    def registrar(self, fonte, item, cfg):
        video = str(item.get("id", ""))
        if not VIDEO.fullmatch(video) or item.get("is_live") or item.get("live_status") in ("is_live", "is_upcoming", "post_live"):
            return
        if "videos_permitidos" in fonte and video not in fonte["videos_permitidos"]:
            return
        titulo = str(item.get("title") or video)[:300]
        if video in fonte.get("videos_excluidos", []) or not titulo_confere(fonte, titulo):
            return
        palavras = next((t.get("palavras", []) for t in cfg["temas"] if t["id"] == fonte["tema"]), [])
        pontos = sum(1 for p in palavras if normalizar(p) in normalizar(titulo))
        self.banco.x("""INSERT OR IGNORE INTO descobertas
            (fonte,video,titulo,tema,pontuacao,estado,criado) VALUES(?,?,?,?,?,'descoberto',?)""",
            (fonte["id"], video, titulo, fonte["tema"], pontos, time.time()))
        self.banco.x("INSERT OR REPLACE INTO sinais VALUES(?,?,?,?)",
            ("https://www.youtube.com/watch?v=" + video, fonte["tema"], titulo, dt.datetime.now(UTC).isoformat()))

    def buscar_temas(self, cfg, c):
        if c.get("busca_por_tema", True) is not True:
            return
        ativos = {x["tema"] for x in cfg["canais"] if x.get("ativo", True)}
        # Uma rodada por tema ativo; consultas genéricas e rodízio das palavras do usuário.
        for tema in [t for t in cfg["temas"] if t["id"] in ativos][:4]:
            chave = "online_tema_" + tema["id"]
            if time.time() - float(self.banco.get(chave, "0")) < max(30, int(c.get("intervalo_min", 360))) * 60:
                continue
            self.banco.set(chave, time.time())
            consultas_base = c.get("buscas", {}).get(tema["id"], BUSCAS.get(tema["id"], [str(tema["id"]) + " podcast entrevista"]))
            rodada_busca = int(self.banco.get(chave + "_busca_rodada", "0"))
            consultas = [consultas_base[(rodada_busca + n) % len(consultas_base)] for n in range(min(2,len(consultas_base)))]
            self.banco.set(chave + "_busca_rodada", rodada_busca + 2)
            proativas = json.loads(self.banco.get("rotina_consultas_"+tema["id"], "[]"))
            if proativas and c.get("rotina", {}).get("ativo") is True:
                rodada_proativa = int(self.banco.get(chave + "_proativa_rodada", "0"))
                consultas[-1] = proativas[rodada_proativa % len(proativas)]
                self.banco.set(chave + "_proativa_rodada", rodada_proativa + 1)
            palavras = [p for p in tema.get("palavras", []) if isinstance(p, str) and p.strip()]
            if palavras:
                rodada = int(self.banco.get(chave + "_rodada", "0"))
                consultas.append(palavras[rodada % len(palavras)] + " podcast entrevista melhores momentos")
                self.banco.set(chave + "_rodada", rodada + 1)
            falhas = []
            for consulta in consultas[:3]:
                try:
                    for item in self.transporte.pesquisar(consulta)[:10]:
                        canal = str(item.get("channel_id") or "")
                        if not CANAL.fullmatch(canal):
                            continue
                        ident = "achado-" + hashlib.sha256((canal + ":" + tema["id"]).encode()).hexdigest()[:16]
                        url = "https://www.youtube.com/channel/" + canal + "/videos"
                        nome = str(item.get("channel") or item.get("uploader") or canal)[:200]
                        self.banco.x("""INSERT INTO canais_encontrados VALUES(?,?,?,?,?,?)
                            ON CONFLICT(channel_id,tema) DO UPDATE SET nome=excluded.nome,ultima=excluded.ultima""",
                            (ident, canal, tema["id"], nome, url, time.time()))
                        # Origem já autorizada segue seu cadastro; novas origens permanecem pendentes.
                        fonte = next((f for f in c["fontes"] if f.get("channel_id") == canal and f["tema"] == tema["id"]),
                                     {"id": ident, "tema": tema["id"]})
                        if fonte["id"] != ident:
                            self.banco.x("""UPDATE OR IGNORE descobertas SET fonte=? WHERE fonte=?
                                AND estado IN ('descoberto','erro')""", (fonte["id"], ident))
                        self.registrar(fonte, item, cfg)
                except Exception as erro:
                    falhas.append(type(erro).__name__)
            self.banco.set(chave + "_erro", ", ".join(sorted(set(falhas))))
        self.banco.x("DELETE FROM canais_encontrados WHERE ultima<?", (time.time()-30*86400,))

    def fontes_locais(self):
        c = self.config()
        return [{**f, "id": "online-" + f["id"], "pasta": str(self.entrada / f["id"]),
                 "ativo": c["ativo"] and permissao(f), "origem_online": True,
                 "credito": f.get("credito") or "Origem: " + f["url"]} for f in c["fontes"]]

    def ciclo(self, cfg):
        c = self.config()
        if not c["ativo"]:
            return
        self.buscar_temas(cfg, c)
        # Evita busca de tema sem destino ativo; limita também o custo das falhas de rede.
        temas = {x["tema"] for x in cfg["canais"] if x.get("ativo", True)}
        visitadas = 0
        for f in sorted(c["fontes"], key=lambda f: float(self.banco.get("online_busca_"+f["id"], "0"))):
            if visitadas >= c.get("max_buscas_ciclo", 4):
                break
            if f.get("ativo") is not True or f["tema"] not in temas:
                continue
            chave = "online_busca_" + f["id"]
            intervalo = max(30, int(c.get("intervalo_min", 360))) * 60
            if time.time() - float(self.banco.get(chave, "0")) < intervalo:
                continue
            self.banco.set(chave, time.time())
            visitadas += 1
            try:
                for item in self.transporte.listar(f)[:30]:
                    self.registrar(f, item, cfg)
                self.banco.set("online_erro_" + f["id"], "")
            except Exception as erro:
                self.banco.set("online_erro_" + f["id"], "Busca indisponível: " + type(erro).__name__)
        # Só um episódio por volta; fila, cotas diárias e reserva de disco impedem crescimento sem limite.
        self.importar_um(cfg, c)
        self.banco.x("DELETE FROM descobertas WHERE criado<? AND estado!='importado'", (time.time()-30*86400,))

    def importar_um(self, cfg, c):
        pendentes = self.banco.q("SELECT COUNT(*) n FROM fontes WHERE estado IN ('novo','editando')")[0]["n"]
        prontos = self.banco.q("SELECT COUNT(*) n FROM posts WHERE estado='pronto'")[0]["n"]
        if pendentes >= int(cfg["max_fontes_pendentes"]) or prontos >= int(cfg.get("max_posts_prontos", 16)):
            return
        dia = dt.datetime.now(UTC).date().isoformat()
        chave = "online_downloads_" + dia
        usados = int(self.banco.get(chave, "0"))
        if usados >= min(8, max(0, int(c.get("max_downloads_dia", 2)))):
            return
        ativas = {f["id"]: f for f in c["fontes"] if permissao(f) and any(
            canal.get("ativo", True) and canal.get("tema") == f["tema"] and canal["plataforma"] in f["plataformas"]
            for canal in cfg["canais"])}
        # Não faz nenhuma requisição de mídia sem autorização.
        if not ativas:
            return
        placeholders = ",".join("?" for _ in ativas)
        if self.banco.get("download_node_ejs_revisao") != "1" and importlib.util.find_spec("yt_dlp_ejs") is not None:
            # Reconsidera uma única vez erros antigos após corrigir a dependência, sem zerar cotas/tentativas.
            self.banco.x("UPDATE descobertas SET proxima=0 WHERE estado='erro' AND tentativas<3 "
                         "AND erro LIKE '%DownloadError%' AND fonte IN ("+placeholders+")",tuple(ativas))
            self.banco.set("download_node_ejs_revisao","1")
        candidatos = self.banco.q("""SELECT * FROM descobertas WHERE estado IN ('descoberto','erro')
                AND tentativas<3 AND proxima<=? AND fonte IN (""" + placeholders + """
                ) ORDER BY pontuacao DESC,criado DESC LIMIT 1000""", (time.time(), *ativas))
        # Alterna temas e origens elegíveis sem aumentar as cotas de disco/download.
        candidatos.sort(key=lambda r: (float(self.banco.get("online_importou_tema_"+r["tema"], "0")),
                                      float(self.banco.get("online_importou_"+r["fonte"], "0"))))
        for row in candidatos:
            if self.banco.q("SELECT 1 FROM descobertas WHERE video=? AND estado='importado'", (row["video"],)):
                continue
            f = ativas.get(row["fonte"])
            if not f:
                continue
            self.entrada.mkdir(parents=True, exist_ok=True)
            limite = int(cfg["max_video_mb"]) * 1024**2
            total = sum(p.stat().st_size for p in self.entrada.rglob("*") if p.is_file())
            teto = max(0, int(c.get("max_armazenamento_mb", 12000))) * 1024**2
            if total + limite > teto or shutil.disk_usage(self.entrada).free < limite + int(cfg["min_espaco_livre_mb"]) * 1024**2:
                return
            # Reserva tentativas inclusive para falhas: um erro de rede não consome a máquina sem parar.
            self.banco.set(chave, usados + 1)
            self.banco.x("UPDATE descobertas SET tentativas=tentativas+1 WHERE fonte=? AND video=?", (f["id"], row["video"]))
            try:
                pasta = self.entrada / f["id"]
                pasta.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix="download-", dir=self.entrada) as temp:
                    arquivo, info = self.transporte.baixar(f, row["video"], Path(temp), cfg)
                    # Releitura protege contra revogação/expiração enquanto o download estava em andamento.
                    atual = next((x for x in self.config()["fontes"] if x["id"] == f["id"]), None)
                    if not self.config()["ativo"] or not permissao(atual) or atual != f:
                        raise ValueError("Autorização alterada durante download.")
                    if not origem_confere(f, info):
                        raise ValueError("Canal de origem incorreto.")
                    conferir_espera(f, info)
                    arquivo = Path(arquivo).resolve()
                    if Path(temp).resolve() not in arquivo.parents or arquivo.suffix.lower() not in (".mp4", ".webm", ".mkv"):
                        raise ValueError("Arquivo inesperado.")
                    if not 0 < arquivo.stat().st_size <= limite:
                        raise ValueError("Tamanho de download inválido.")
                    destino = pasta / (row["video"] + arquivo.suffix.lower())
                    credito = (str(f.get("credito") or "") + "\nOrigem: " + str(f.get("nome") or f["id"]) +
                        "\nhttps://www.youtube.com/watch?v=" + row["video"] + "\n" + str(info.get("title") or row["titulo"]))[:1800]
                    # Sidecar primeiro, mídia por último: descoberta local nunca vê um arquivo pela metade.
                    meta = {"titulo": info.get("title") or row["titulo"], "descricao": credito,
                            "origem": row["video"], "comprovante": f["comprovante"],
                            "timestamp": info.get("timestamp"), "release_timestamp": info.get("release_timestamp"),
                            "upload_date": info.get("upload_date"), "id": row["video"],
                            "title": info.get("title") or row["titulo"],
                            "channel_id": info.get("channel_id"), "uploader_id": info.get("uploader_id"),
                            "duration": info.get("duration")}
                    destino.with_suffix(destino.suffix + ".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
                    arquivo.replace(destino)
                    os.utime(destino, (time.time()-180, time.time()-180))
                self.banco.x("UPDATE descobertas SET estado='importado',caminho=?,erro=NULL WHERE fonte=? AND video=?",
                    (str(destino), f["id"], row["video"]))
                self.banco.set("online_importou_tema_"+f["tema"], time.time())
                self.banco.set("online_importou_"+f["id"], time.time())
            except Exception as erro:
                self.banco.x("UPDATE descobertas SET estado='erro',erro=?,proxima=? WHERE fonte=? AND video=?",
                    (diagnostico_download(erro), time.time()+3600*2**row["tentativas"], f["id"], row["video"]))
            return

    def status(self):
        c = self.config()
        fontes = [{"id": f["id"], "nome": f.get("nome", f["id"]), "tema": f["tema"],
            "url": f["url"], "autorizada": c["ativo"] and permissao(f),
            "situacao": "autorizada" if c["ativo"] and permissao(f) else "somente_monitoramento",
            "ultima_busca": self.banco.get("online_busca_"+f["id"]),
            "erro": self.banco.get("online_erro_"+f["id"])} for f in c["fontes"]]
        for resumo, fonte in zip(fontes, c["fontes"]):
            resumo.update({"aguardar_horas": fonte.get("aguardar_horas", 0),
                "videos_permitidos": fonte.get("videos_permitidos", []),
                "regras_editoriais": fonte.get("regras_editoriais", []),
                "publicar_automaticamente": fonte.get("publicar_automaticamente", False),
                "revisao_automatica": fonte.get("revisao_automatica", False),
                "publicacao_catalogo": fonte.get("publicacao_catalogo", False),
                "pendencia": fonte.get("pendencia", ""), "serie": fonte.get("serie", [])})
        pessoal = self.raiz / "criador.json"
        cfg = json.loads(pessoal.read_text(encoding="utf-8-sig")) if pessoal.is_file() else {}
        cobertura = []
        for canal in cfg.get("canais", []):
            if not canal.get("ativo", True):
                continue
            permitidas = [f["id"] for f in c["fontes"] if c["ativo"] and permissao(f)
                          and f["tema"] == canal.get("tema") and canal.get("plataforma") in f["plataformas"]]
            cobertura.append({"canal": canal["id"], "tema": canal.get("tema"),
                              "plataforma": canal.get("plataforma"), "fontes_autorizadas": permitidas,
                              "conta_configurada": bool(canal.get("buffer_channel_id")),
                              "publicar_global": cfg.get("publicar") is True})
        return {"ativo": c["ativo"], "catalogo_revisao": c.get("revisao", "local"), "fontes": fontes,
                "cobertura_canais": cobertura, "ultimo_erro": self.banco.get("online_erro_global"),
                "javascript": {"node_disponivel":bool(shutil.which("node")),
                               "ejs_instalado":importlib.util.find_spec("yt_dlp_ejs") is not None},
                "busca_por_tema": c.get("busca_por_tema", True),
                "buscas": [{"tema": t["chave"][len("online_tema_"):-len("_erro")], "erro": t["valor"]}
                           for t in self.banco.q("SELECT chave,valor FROM estado WHERE chave LIKE 'online_tema_%_erro'")],
                "canais_encontrados": self.banco.q("SELECT id,channel_id,nome,tema,url FROM canais_encontrados ORDER BY ultima DESC LIMIT 40"),
                "episodios": self.banco.q("SELECT fonte,video,titulo,pontuacao,estado,erro FROM descobertas ORDER BY criado DESC LIMIT 20"),
                "aviso": "Monitoramento não autoriza reutilização. Downloads dependem de permissão cadastrada; publicação segue criador.json."}


def diagnostico_download(erro):
    # Classifica mensagens conhecidas, sem persistir URLs temporárias, cookies ou dados brutos.
    texto = str(erro).lower()
    if any(t in texto for t in ("requested format", "no video formats", "only images")):
        return "Formato de vídeo indisponível: conferir EJS/Node e formatos separados."
    if any(t in texto for t in ("javascript", "challenge", "signature", "ejs")):
        return "Dependência JavaScript do YouTube indisponível: conferir Node e yt-dlp-ejs."
    if any(t in texto for t in ("sign in", "login", "not a bot", "private video", "age-restricted")):
        return "YouTube exige acesso/autenticação. O monitor não usa login ou cookies do navegador."
    if any(t in texto for t in ("403", "429", "too many requests")):
        return "YouTube restringiu esta solicitação; aguardar sem contornar o bloqueio."
    if any(t in texto for t in ("getaddrinfo", "resolve", "timed out", "connection")):
        return "Falha de rede ao obter o vídeo; nova tentativa respeitará os limites."
    return "Importação não concluída: " + type(erro).__name__
