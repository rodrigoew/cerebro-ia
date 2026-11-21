"""Publicação YouTube/TikTok via Buffer e mídia própria via Cloudinary.

As integrações só são chamadas com configuração e autorização explícitas.
Uma criação de post com resposta ambígua NÃO é repetida automaticamente.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import urllib.request

SERVICO = "nucleo-criador"


class ConfiguracaoPendente(RuntimeError):
    pass


class EnvioIncerto(RuntimeError):
    pass


def segredo(nome):
    env = os.environ.get("NUCLEO_" + nome.upper())
    if env:
        return env
    try:
        import keyring
        return keyring.get_password(SERVICO, nome) or ""
    except Exception:
        return ""


def guardar_segredo(nome, valor):
    import keyring
    keyring.set_password(SERVICO, nome, valor)


def sha256(arquivo):
    h = hashlib.sha256()
    with Path(arquivo).open("rb") as stream:
        for bloco in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


class Buffer:
    def __init__(self, chave=None):
        self.chave = chave or segredo("buffer_token")
        if not self.chave:
            raise ConfiguracaoPendente("Conecte a conta Buffer e guarde buffer_token no cofre.")

    def graphql(self, query, variables):
        req = urllib.request.Request("https://api.buffer.com", method="POST",
              data=json.dumps({"query": query, "variables": variables}).encode(),
              headers={"Authorization": "Bearer " + self.chave, "Content-Type": "application/json"})
        # Nunca incluir respostas brutas ou tokens em logs.
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read(2_000_000))
        except Exception as erro:
            raise RuntimeError("Buffer indisponível (" + type(erro).__name__ + ").") from None
        if result.get("errors"):
            detalhe = "; ".join(str(e.get("message","Erro da API")) for e in result["errors"])
            raise RuntimeError("Buffer rejeitou a consulta: "+detalhe.replace(self.chave,"[chave oculta]")[:500])
        return result["data"]

    def canal(self, channel_id, plataforma):
        r = self.graphql("""query($input: ChannelInput!) {
          channel(input: $input) { id name service isDisconnected isLocked isQueuePaused }
        }""", {"input": {"id": channel_id}})["channel"]
        if r["service"].lower() != plataforma or any(r.get(k) for k in ("isDisconnected", "isLocked", "isQueuePaused")):
            raise ConfiguracaoPendente("Canal incompatível, desconectado, bloqueado ou pausado no Buffer.")
        return r

    def agendar(self, channel_id, plataforma, titulo, descricao, media_url, quando, config, rascunho=False):
        if plataforma not in ("youtube", "tiktok") or not media_url.startswith("https://"):
            raise ValueError("Plataforma ou mídia inválida.")
        metadata = ({"youtube": {"title": titulo[:95], "categoryId": str(config.get("categoria", "24")),
                     "privacy": "public", "madeForKids": bool(config.get("infantil", False)),
                     "isAiGenerated": bool(config.get("ia_sintetica", False))}}
                    if plataforma == "youtube" else {"tiktok": {"isAiGenerated": bool(config.get("ia_sintetica", False))}})
        dados = {"channelId": channel_id, "schedulingType": "automatic", "mode": "customScheduled",
                 "dueAt": quando, "text": (titulo + "\n\n" + descricao)[:2000],
                 "assets": [{"video": {"url": media_url}}], "metadata": metadata}
        dados["needsApproval"] = False
        dados["saveToDraft"] = bool(rascunho)
        if rascunho:
            dados["mode"] = "addToQueue"
            dados.pop("dueAt", None)
        try:
            r = self.graphql("""mutation($input: CreatePostInput!) {
              createPost(input: $input) {
                ... on PostActionSuccess { post { id status dueAt } }
                ... on MutationError { message }
              }
            }""", {"input": dados})["createPost"]
            if not r.get("post", {}).get("id"):
                raise RuntimeError("Post não confirmado pelo provedor.")
            if rascunho and r["post"].get("status") != "draft":
                raise RuntimeError("Buffer não confirmou estado de rascunho.")
            return r["post"]
        except Exception as erro:
            # O provedor pode ter criado o post antes de a conexão cair.
            detalhe = str(erro).replace(self.chave,"[chave oculta]")[:500]
            raise EnvioIncerto("Confirme a fila no Buffer antes de reconciliar este envio. Não houve repetição automática. "+detalhe) from None

    def consultar(self, post_id):
        return self.graphql("""query($input: PostInput!) {
          post(input: $input) { id status sentAt metricsUpdatedAt metrics { type value } }
        }""", {"input": {"id": post_id}})["post"]


class Cloudinary:
    def __init__(self):
        self.cloud = segredo("cloudinary_cloud")
        self.key = segredo("cloudinary_key")
        self.secret = segredo("cloudinary_secret")
        if not all((self.cloud, self.key, self.secret)):
            raise ConfiguracaoPendente("Configure Cloudinary no cofre para hospedar somente os cortes destinados à publicação.")

    def enviar(self, arquivo, limite_bytes):
        import cloudinary.uploader
        arquivo = Path(arquivo)
        if not arquivo.is_file() or not 0 < arquivo.stat().st_size <= limite_bytes:
            raise ValueError("Arquivo excede o limite de upload configurado.")
        # Nome por conteúdo: repetir apenas a hospedagem não cria cópias adicionais.
        r = cloudinary.uploader.upload_large(str(arquivo), resource_type="video", secure=True,
            public_id="nucleo/" + sha256(arquivo), overwrite=True, cloud_name=self.cloud,
            api_key=self.key, api_secret=self.secret, timeout=120, chunk_size=6_000_000)
        url = r.get("secure_url", "")
        if not url.startswith("https://res.cloudinary.com/"):
            raise RuntimeError("Hospedagem não confirmou uma URL HTTPS de mídia.")
        return url
