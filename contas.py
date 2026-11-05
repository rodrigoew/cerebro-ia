"""
Contas de e-mail de vários provedores ao mesmo tempo.

Tipos:
  imap       qualquer provedor com IMAP e senha (Locaweb, Hostgator, Zoho, iCloud, Yahoo...)
  gmail      Gmail/Google Workspace por IMAP com senha de app
  microsoft  Outlook.com, Hotmail e Microsoft 365 por IMAP com login moderno (OAuth2)
  pop        provedores que só oferecem POP3 (somente leitura; rascunhos ficam no app)

Gestão permitida: ler, marcar como lida/não lida, sinalizar, arquivar e salvar
rascunhos de resposta. Nada é enviado: o envio é sempre feito por você, no seu
programa de e-mail.
"""
from __future__ import annotations

import email
import email.message
import email.utils
import imaplib
import json
import poplib
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

SERVICO = "resumo-da-manha"
PADROES = {
    "gmail": {"host": "imap.gmail.com", "porta": 993},
    "microsoft": {"host": "outlook.office365.com", "porta": 993},
    "imap": {"host": "", "porta": 993},
    "pop": {"host": "", "porta": 995},
}
ESCOPO_MS = "offline_access https://outlook.office.com/IMAP.AccessAsUser.All"
URL_MS = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/"


def _keyring():
    import keyring
    return keyring


# ================================================================ Microsoft (OAuth2, código de dispositivo)

class OAuthMicrosoft:
    """Login moderno da Microsoft sem navegador embutido: o app mostra um código,
    você entra em microsoft.com/devicelogin, autoriza, e o app guarda só o
    token de renovação no cofre do sistema."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.fluxos: dict[str, dict] = {}
        self._cache: dict[str, tuple[float, str]] = {}
        self._trava = threading.Lock()

    @property
    def client_id(self) -> str:
        return (self.cfg.get("microsoft", {}).get("client_id") or "").strip()

    @property
    def tenant(self) -> str:
        return self.cfg.get("microsoft", {}).get("tenant", "common")

    def _post(self, caminho: str, dados: dict) -> dict:
        req = urllib.request.Request(URL_MS.format(tenant=self.tenant) + caminho,
                                     data=urllib.parse.urlencode(dados).encode(),
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as erro:
            return json.loads(erro.read() or b"{}")

    def iniciar(self, usuario: str) -> dict:
        if not self.client_id:
            raise ValueError("Falta o identificador do aplicativo Microsoft (Ajustes > Contas > Microsoft).")
        d = self._post("devicecode", {"client_id": self.client_id, "scope": ESCOPO_MS})
        if "device_code" not in d:
            raise RuntimeError(d.get("error_description", "A Microsoft recusou o pedido de login."))
        fluxo = {"estado": "aguardando", "codigo": d["user_code"], "url": d["verification_uri"],
                 "expira": time.time() + int(d.get("expires_in", 900)), "mensagem": None}
        self.fluxos[usuario] = fluxo
        threading.Thread(target=self._aguardar, args=(usuario, d["device_code"], int(d.get("interval", 5))),
                         daemon=True).start()
        return {"codigo": fluxo["codigo"], "url": fluxo["url"]}

    def _aguardar(self, usuario: str, device_code: str, intervalo: int):
        fluxo = self.fluxos[usuario]
        while time.time() < fluxo["expira"]:
            time.sleep(intervalo)
            d = self._post("token", {"client_id": self.client_id, "device_code": device_code,
                                     "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
            if "access_token" in d:
                _keyring().set_password(SERVICO, f"oauth-ms:{usuario}", d["refresh_token"])
                with self._trava:
                    self._cache[usuario] = (time.time() + int(d.get("expires_in", 3600)) - 120, d["access_token"])
                fluxo.update(estado="concluido", mensagem="Conta conectada.")
                return
            erro = d.get("error")
            if erro == "slow_down":
                intervalo += 5
            elif erro != "authorization_pending":
                fluxo.update(estado="erro", mensagem=d.get("error_description", erro or "falha no login"))
                return
        fluxo.update(estado="erro", mensagem="O código expirou. Tente de novo.")

    def estado(self, usuario: str) -> dict:
        f = self.fluxos.get(usuario)
        return {"estado": f["estado"], "mensagem": f["mensagem"], "codigo": f["codigo"], "url": f["url"]} if f \
            else {"estado": "nenhum"}

    def token(self, usuario: str) -> str:
        with self._trava:
            em_cache = self._cache.get(usuario)
            if em_cache and em_cache[0] > time.time():
                return em_cache[1]
        renovacao = _keyring().get_password(SERVICO, f"oauth-ms:{usuario}")
        if not renovacao:
            raise RuntimeError("conta Microsoft ainda não conectada (Ajustes > Contas > Conectar)")
        d = self._post("token", {"client_id": self.client_id, "grant_type": "refresh_token",
                                 "refresh_token": renovacao, "scope": ESCOPO_MS})
        if "access_token" not in d:
            raise RuntimeError("login da Microsoft expirou; conecte a conta de novo")
        if d.get("refresh_token"):
            _keyring().set_password(SERVICO, f"oauth-ms:{usuario}", d["refresh_token"])
        with self._trava:
            self._cache[usuario] = (time.time() + int(d.get("expires_in", 3600)) - 120, d["access_token"])
        return d["access_token"]


_oauth: OAuthMicrosoft | None = None


def oauth(cfg: dict | None = None) -> OAuthMicrosoft:
    global _oauth
    if _oauth is None:
        _oauth = OAuthMicrosoft(cfg or {})
    elif cfg is not None:
        _oauth.cfg = cfg
    return _oauth


# ================================================================ conexões

def tipo_de(conta: dict) -> str:
    return conta.get("tipo", "imap")


def conectar_imap(conta: dict, senha: str | None) -> imaplib.IMAP4_SSL:
    tipo = tipo_de(conta)
    padrao = PADROES.get(tipo, PADROES["imap"])
    host = conta.get("host") or padrao["host"]
    m = imaplib.IMAP4_SSL(host, int(conta.get("porta") or padrao["porta"]),
                          ssl_context=ssl.create_default_context(), timeout=40)
    if tipo == "microsoft":
        token = oauth().token(conta["usuario"])
        autenticacao = f"user={conta['usuario']}\x01auth=Bearer {token}\x01\x01".encode()
        m.authenticate("XOAUTH2", lambda _: autenticacao)
    else:
        if not senha:
            raise RuntimeError(f"sem senha guardada para {conta['apelido']} (Ajustes > Contas)")
        m.login(conta["usuario"], senha)
    return m


def conectar_pop(conta: dict, senha: str | None) -> poplib.POP3_SSL:
    if not senha:
        raise RuntimeError(f"sem senha guardada para {conta['apelido']} (Ajustes > Contas)")
    p = poplib.POP3_SSL(conta["host"], int(conta.get("porta") or 995), timeout=40,
                        context=ssl.create_default_context())
    p.user(conta["usuario"])
    p.pass_(senha)
    return p


def _texto_da_mensagem(msg) -> str:
    texto, html_alt = [], []
    for parte in msg.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        if "attachment" in str(parte.get("Content-Disposition", "")).lower():
            continue
        tipo = parte.get_content_type()
        if tipo not in ("text/plain", "text/html"):
            continue
        carga = parte.get_payload(decode=True) or b""
        conteudo = carga.decode(parte.get_content_charset() or "utf-8", errors="replace")
        (texto if tipo == "text/plain" else html_alt).append(conteudo)
    if texto:
        return "\n".join(texto)
    if html_alt:
        import html
        limpo = re.sub(r"(?is)<(script|style).*?</\1>", " ", "\n".join(html_alt))
        return html.unescape(re.sub(r"(?s)<[^>]+>", " ", limpo))
    return ""


def coletar_pop(conta: dict, senha: str | None, limite: int = 60) -> list[tuple[dict, str]]:
    """Baixa as mensagens mais recentes (POP não tem pastas nem marcações)."""
    p = conectar_pop(conta, senha)
    try:
        _, lista, _ = p.uidl()
        itens = [l.decode().split(" ", 1) for l in lista][-limite:]
        saida = []
        for numero, uidl in itens:
            _, linhas, _ = p.retr(int(numero))
            bruto = b"\r\n".join(linhas)
            msg = email.message_from_bytes(bruto)
            saida.append(({"uid": uidl, "flags": "", "cabecalho": msg}, _texto_da_mensagem(msg)))
        return saida
    finally:
        try:
            p.quit()
        except Exception:
            pass


def corpo_pop(conta: dict, senha: str | None, uidl: str) -> str:
    p = conectar_pop(conta, senha)
    try:
        _, lista, _ = p.uidl()
        numero = next((l.decode().split(" ", 1)[0] for l in lista if l.decode().split(" ", 1)[1] == uidl), None)
        if not numero:
            raise RuntimeError("a mensagem não está mais no servidor")
        _, linhas, _ = p.retr(int(numero))
        return _texto_da_mensagem(email.message_from_bytes(b"\r\n".join(linhas)))
    finally:
        try:
            p.quit()
        except Exception:
            pass


# ================================================================ pastas especiais

def pasta_especial(m: imaplib.IMAP4_SSL, flag: str, nomes: tuple[str, ...]) -> str | None:
    tipo, linhas = m.list()
    candidatas = []
    for bruto in linhas or []:
        linha = bruto.decode(errors="replace") if isinstance(bruto, bytes) else str(bruto)
        achou = re.match(r'\((?P<f>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<n>.+)$', linha)
        if not achou:
            continue
        nome = achou.group("n").strip().strip('"')
        if flag in achou.group("f"):
            return nome
        if any(re.search(n, nome, re.I) for n in nomes):
            candidatas.append(nome)
    return candidatas[0] if candidatas else None


# ================================================================ gestão (sem envio)

def operar(m: imaplib.IMAP4_SSL, uid: str, acao: str) -> str:
    if m.select("INBOX")[0] != "OK":
        raise RuntimeError("não consegui abrir a caixa de entrada")
    if acao == "lida":
        m.uid("store", uid, "+FLAGS", "(\\Seen)")
        return "Marcada como lida."
    if acao == "nao_lida":
        m.uid("store", uid, "-FLAGS", "(\\Seen)")
        return "Marcada como não lida."
    if acao == "sinalizar":
        m.uid("store", uid, "+FLAGS", "(\\Flagged)")
        return "Sinalizada."
    if acao == "tirar_sinal":
        m.uid("store", uid, "-FLAGS", "(\\Flagged)")
        return "Sinal removido."
    if acao == "arquivar":
        destino = pasta_especial(m, "\\Archive", (r"^archive$", r"arquiv")) or \
            pasta_especial(m, "\\All", (r"all mail", r"todos os e-?mails"))
        if not destino:
            raise RuntimeError("esta conta não tem pasta de arquivo")
        capacidades = " ".join(c.decode() if isinstance(c, bytes) else c for c in m.capabilities)
        if "MOVE" in capacidades:
            tipo, _ = m.uid("MOVE", uid, f'"{destino}"')
            if tipo != "OK":
                raise RuntimeError("o servidor recusou mover a mensagem")
        else:
            if m.uid("COPY", uid, f'"{destino}"')[0] != "OK":
                raise RuntimeError("o servidor recusou copiar a mensagem")
            m.uid("store", uid, "+FLAGS", "(\\Deleted)")
            if "UIDPLUS" in capacidades:
                m.uid("EXPUNGE", uid)
        return f"Arquivada em {destino}."
    raise ValueError("ação desconhecida")


def montar_resposta(de: str, para: str, assunto: str, corpo: str, em_resposta_a: str = "", cc: str = "") -> bytes:
    msg = email.message.EmailMessage()
    msg["From"] = de
    if para:
        msg["To"] = para
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = assunto or "(sem assunto)"
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid()
    if em_resposta_a:
        msg["In-Reply-To"] = em_resposta_a
        msg["References"] = em_resposta_a
    msg.set_content(corpo or "")
    return msg.as_bytes()


def salvar_rascunho(m: imaplib.IMAP4_SSL, mensagem: bytes) -> str:
    pasta = pasta_especial(m, "\\Drafts", (r"draft", r"rascunho"))
    if not pasta:
        raise RuntimeError("não encontrei a pasta de rascunhos")
    tipo, _ = m.append(f'"{pasta}"', "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), mensagem)
    if tipo != "OK":
        raise RuntimeError("o servidor recusou o rascunho")
    return pasta


def link_mailto(para: str, assunto: str, corpo: str) -> str:
    return "mailto:" + urllib.parse.quote(para or "") + "?" + urllib.parse.urlencode(
        {"subject": assunto, "body": corpo}, quote_via=urllib.parse.quote)
