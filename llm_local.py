"""
IA local via Ollama (roda na sua placa NVIDIA, sem internet).

Modelos padrão (troque em "llm_local" no config.json):
  modelo            qwen3:8b   conversa, resumo, classificação
  modelo_embedding  bge-m3     busca por significado (multilíngue)
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request


class LLMLocal:
    def __init__(self, cfg: dict):
        c = cfg.get("llm_local", {})
        self.ativo = c.get("ativo", True)
        self.url = c.get("url", "http://127.0.0.1:11434").rstrip("/")
        self.modelo = c.get("modelo", "qwen3:8b")
        self.modelo_emb = c.get("modelo_embedding", "bge-m3")
        pequeno = any(t in self.modelo for t in (":4b", ":1.7b", ":0.6b"))
        self.contexto = int(c.get("contexto", 4096 if pequeno else 8192))
        if pequeno and self.contexto > 4096 and not c.get("contexto_fixo"):
            self.contexto = 4096        # vale também para configurações antigas, que tinham 8192
        self.manter = c.get("manter_carregado", "60m")
        # placas pequenas: a busca por significado roda no processador, para o modelo de conversa
        # não ser tirado da placa a cada pergunta (era a maior causa de demora em 4 GB)
        self.emb_cpu = bool(c.get("embedding_na_cpu", pequeno))
        self._estado = (0.0, False, "")
        self._trava = threading.Lock()
        # IA do aparelho central (ex.: o PC com placa maior), usada quando estiver na mesma rede
        self.remoto = {"ativo": False, "url": "", "token": None}
        self._remoto = (0.0, None)          # (quando verificou, estado do central ou None)

    # ------------------------------------------------------------ IA do central pela rede
    def _estado_remoto(self) -> dict | None:
        r = self.remoto
        if not (r.get("ativo") and r.get("url") and r.get("token")):
            return None
        agora = time.time()
        if agora - self._remoto[0] < 30:
            return self._remoto[1]
        estado = None
        try:
            req = urllib.request.Request(r["url"].rstrip("/") + "/api/ia/estado", headers={"X-Sinc": r["token"]()})
            with urllib.request.urlopen(req, timeout=3) as resp:
                d = json.loads(resp.read())
            estado = d if d.get("chat_ok") else None
        except Exception:
            estado = None
        self._remoto = (agora, estado)
        return estado

    def _alvo(self) -> tuple[str, dict]:
        """Para onde mandar: o central (se alcançável) ou o Ollama deste computador."""
        if self._estado_remoto():
            return self.remoto["url"].rstrip("/") + "/api/ia", {"X-Sinc": self.remoto["token"]()}
        return self.url, {}

    def _remoto_falhou(self) -> None:
        self._remoto = (time.time(), None)

    @property
    def modelo_em_uso(self) -> str:
        e = self._estado_remoto()
        return f"{e['modelo']} do central" if e else self.modelo

    # ------------------------------------------------------------ disponibilidade
    def _req(self, caminho: str, dados: dict | None = None, timeout: int = 120, local: bool = False):
        corpo = json.dumps(dados).encode() if dados is not None else None
        base, extra = (self.url, {}) if local else self._alvo()
        req = urllib.request.Request(base + caminho, data=corpo,
                                     headers={"Content-Type": "application/json", **extra},
                                     method="POST" if dados is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.URLError:
            if base != self.url:                 # o central sumiu da rede: tenta no próprio computador
                self._remoto_falhou()
                return self._req(caminho, dados, timeout, local=True)
            raise

    def status(self, forcar: bool = False) -> dict:
        """Verifica o Ollama e se os modelos estão baixados (cache de 30 s)."""
        agora = time.time()
        with self._trava:
            if not forcar and agora - self._estado[0] < 30:
                return self._estado[2]
        info = {"ativo": self.ativo, "online": False, "modelo": self.modelo,
                "modelo_embedding": self.modelo_emb, "chat_ok": False, "emb_ok": False, "motivo": None, "central": False}
        remoto = self._estado_remoto()
        if remoto:
            info.update(online=True, chat_ok=True, emb_ok=bool(remoto.get("emb_ok")), central=True,
                        modelo=f"{remoto['modelo']} do central", modelo_embedding=remoto.get("modelo_embedding", self.modelo_emb))
            with self._trava:
                self._estado = (agora, True, info)
            return info
        if not self.ativo:
            info["motivo"] = "IA local desligada no config."
        else:
            try:
                nomes = {m["name"] for m in self._req("/api/tags", timeout=4).get("models", [])}
                base = lambda n: n if ":" in n else n + ":latest"
                info["online"] = True
                info["chat_ok"] = base(self.modelo) in nomes
                info["emb_ok"] = base(self.modelo_emb) in nomes
                faltam = [m for m, ok in ((self.modelo, info["chat_ok"]), (self.modelo_emb, info["emb_ok"])) if not ok]
                if faltam:
                    info["motivo"] = "Baixe no terminal: " + "  e  ".join(f"ollama pull {m}" for m in faltam)
            except Exception:
                info["motivo"] = "Ollama não está rodando. Instale em ollama.com e abra o programa."
        with self._trava:
            self._estado = (agora, info["chat_ok"], info)
        return info

    def pode_conversar(self) -> bool:
        return bool(self.status().get("chat_ok"))

    def pode_vetorizar(self) -> bool:
        return bool(self.status().get("emb_ok"))

    # ------------------------------------------------------------ conversa
    def conversar(self, mensagens: list[dict], sistema: str, temperatura: float = 0.3,
                  json_saida: bool = False, max_tokens: int = 900) -> str:
        dados = {"model": self.modelo, "stream": False, "keep_alive": self.manter, "think": False,
                 "messages": [{"role": "system", "content": sistema}] + mensagens,
                 "options": {"temperature": temperatura, "num_ctx": self.contexto, "num_predict": max_tokens}}
        if json_saida:
            dados["format"] = "json"
        try:
            resposta = self._req("/api/chat", dados, timeout=180)
        except urllib.error.HTTPError as erro:
            if erro.code == 400:  # versões antigas do Ollama não conhecem "think"
                dados.pop("think", None)
                resposta = self._req("/api/chat", dados, timeout=180)
            else:
                raise RuntimeError(f"A IA local recusou o pedido ({erro.code}).")
        except urllib.error.URLError:
            raise RuntimeError("Não consegui falar com o Ollama. Ele está aberto?")
        texto = resposta.get("message", {}).get("content", "")
        return re.sub(r"(?s)<think>.*?</think>", "", texto).strip()

    def json(self, mensagens: list[dict], sistema: str, max_tokens: int = 700) -> dict:
        bruto = self.conversar(mensagens, sistema, temperatura=0.1, json_saida=True, max_tokens=max_tokens)
        bruto = re.sub(r"```(json)?", "", bruto).strip()
        try:
            return json.loads(bruto)
        except json.JSONDecodeError:
            achou = re.search(r"\{.*\}", bruto, re.S)
            return json.loads(achou.group(0)) if achou else {}

    # ------------------------------------------------------------ vetores
    def vetorizar(self, textos: list[str]) -> list[list[float]]:
        textos = [t[:4000] or " " for t in textos]
        try:
            r = self._req("/api/embed", {"model": self.modelo_emb, "input": textos,
                                         **({"options": {"num_gpu": 0}} if self.emb_cpu and not self._estado_remoto() else {}),
                                         "keep_alive": self.manter}, timeout=180)
            return r["embeddings"]
        except urllib.error.HTTPError as erro:
            if erro.code != 404:
                raise
        # API antiga, um texto por vez
        return [self._req("/api/embeddings", {"model": self.modelo_emb, "prompt": t}, timeout=120)["embedding"]
                for t in textos]


    # ------------------------------------------------------------ resposta em fluxo (streaming)
    def conversar_fluxo(self, mensagens: list[dict], sistema: str, temperatura: float = 0.3, max_tokens: int = 900):
        """Gera a resposta aos pedaços, conforme o modelo escreve."""
        dados = {"model": self.modelo, "stream": True, "keep_alive": self.manter, "think": False,
                 "messages": [{"role": "system", "content": sistema}] + mensagens,
                 "options": {"temperature": temperatura, "num_ctx": self.contexto, "num_predict": max_tokens}}
        base, extra = self._alvo()
        req = urllib.request.Request(base + "/api/chat", data=json.dumps(dados).encode(),
                                     headers={"Content-Type": "application/json", **extra})
        try:
            try:
                resposta = urllib.request.urlopen(req, timeout=180)
            except urllib.error.URLError as erro:
                if base == self.url or isinstance(erro, urllib.error.HTTPError):
                    raise
                self._remoto_falhou()            # central fora da rede: segue no próprio computador
                req = urllib.request.Request(self.url + "/api/chat", data=json.dumps(dados).encode(),
                                             headers={"Content-Type": "application/json"})
                resposta = urllib.request.urlopen(req, timeout=180)
        except urllib.error.HTTPError as erro:
            if erro.code == 400:
                dados.pop("think", None)
                req = urllib.request.Request(self.url + "/api/chat", data=json.dumps(dados).encode(),
                                             headers={"Content-Type": "application/json"})
                resposta = urllib.request.urlopen(req, timeout=180)
            else:
                raise RuntimeError(f"A IA local recusou o pedido ({erro.code}).")
        except urllib.error.URLError:
            raise RuntimeError("Não consegui falar com o Ollama. Ele está aberto?")
        pensando = False
        with resposta:
            for linha in resposta:
                if not linha.strip():
                    continue
                d = json.loads(linha)
                pedaco = d.get("message", {}).get("content", "")
                if "<think>" in pedaco:
                    pensando = True
                if pensando:
                    if "</think>" in pedaco:
                        pensando = False
                        pedaco = pedaco.split("</think>", 1)[1]
                    else:
                        pedaco = ""
                if pedaco:
                    yield pedaco
                if d.get("done"):
                    break

    # ------------------------------------------------------------ chamada de ferramentas (tool calling nativo)
    def ferramentas(self, mensagens: list[dict], sistema: str, ferramentas: list[dict]) -> list[dict]:
        """Pede ao modelo para escolher ferramentas. Devolve [{"nome", "args"}]."""
        dados = {"model": self.modelo, "stream": False, "keep_alive": self.manter, "think": False,
                 "messages": [{"role": "system", "content": sistema}] + mensagens, "tools": ferramentas,
                 "options": {"temperature": 0, "num_ctx": min(self.contexto, 4096), "num_predict": 160}}
        try:
            resposta = self._req("/api/chat", dados, timeout=90)
        except urllib.error.HTTPError as erro:
            if erro.code == 400:
                dados.pop("think", None)
                resposta = self._req("/api/chat", dados, timeout=90)
            else:
                raise
        chamadas = resposta.get("message", {}).get("tool_calls") or []
        saida = []
        for c in chamadas:
            f = c.get("function", {})
            args = f.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            saida.append({"nome": f.get("name", ""), "args": args})
        return saida


    # ------------------------------------------------------------ aquecimento (evita a demora da 1ª pergunta)
    def aquecer(self) -> bool:
        """Carrega o modelo de conversa na placa antes da primeira pergunta e o mantém lá."""
        if self._estado_remoto():
            return True                       # quem responde é o central; ele se aquece sozinho
        try:
            self._req("/api/generate", {"model": self.modelo, "prompt": "", "keep_alive": self.manter}, timeout=180, local=True)
            if self.emb_cpu:
                self._req("/api/embed", {"model": self.modelo_emb, "input": ["aquecer"], "options": {"num_gpu": 0},
                                         "keep_alive": self.manter}, timeout=120, local=True)
            return True
        except Exception:
            return False
