"""
Sincronização entre os seus aparelhos (PC, notebook, tablet, iPhone).

Como funciona, sem perder memória:
  - Um dos computadores é o "núcleo central" (de preferência o que fica mais
    ligado). Ele expõe um endpoint de sincronização pela sua rede privada.
  - Cada aparelho tem um relógio lógico por tabela. A sincronização troca só
    o que mudou desde a última vez (notas, lembretes, financeiro, ideias,
    decisões, processos, compromissos, conhecimento, e-mails indexados).
  - Conflito do mesmo registro: vence a edição mais recente (campo
    atualizado_em / criado_em). Exclusões são marcadas, nunca somem de um
    lado sem o outro saber.
  - Tudo trafega cifrado com uma frase secreta que só os seus aparelhos têm.
    O servidor nunca guarda a frase; ele só valida quem tem a mesma.

O tablet e o iPhone não rodam este servidor: eles acessam o núcleo central
pelo navegador (PWA), pela mesma rede privada. Então a "memória" é uma só.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time

# Tabelas sincronizadas e a coluna de carimbo de tempo de cada uma.
TABELAS = {
    "notas": "criado_em", "lembretes": "criado_em", "conhecimento": "atualizado_em",
    "ideias": "atualizado_em", "decisoes": "atualizado_em", "processos": "criado_em",
    "compromissos": "atualizado_em", "emails": "data",
    "lancamentos": "criado_em",          # financeiro (banco separado)
}
BANCO_FINANCEIRO = {"lancamentos"}


def _derivar(frase: str, sal: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", frase.encode(), sal, 200_000, dklen=32)


def cifrar(frase: str, dados: dict) -> str:
    """AES-GCM via biblioteca cryptography; devolve texto base64 (sal+nonce+cifra)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os
    sal, nonce = os.urandom(16), os.urandom(12)
    chave = _derivar(frase, sal)
    cifra = AESGCM(chave).encrypt(nonce, json.dumps(dados, ensure_ascii=False, default=str).encode(), None)
    return base64.b64encode(sal + nonce + cifra).decode()


def decifrar(frase: str, texto: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    bruto = base64.b64decode(texto)
    sal, nonce, cifra = bruto[:16], bruto[16:28], bruto[28:]
    chave = _derivar(frase, sal)
    return json.loads(AESGCM(chave).decrypt(nonce, cifra, None).decode())


class Sincronizador:
    def __init__(self, app):
        self.app = app
        self.trava = threading.Lock()
        self.ultimo = {"quando": None, "enviados": 0, "recebidos": 0, "erro": None}
        self._cols: dict[str, list[str]] = {}

    @property
    def cfg(self) -> dict:
        return self.app.cfg.get("sincronizacao", {})

    def frase(self) -> str | None:
        try:
            import keyring
            return keyring.get_password("resumo-da-manha", "sinc-frase")
        except Exception:
            return None

    def definir_frase(self, frase: str) -> None:
        import keyring
        keyring.set_password("resumo-da-manha", "sinc-frase", frase.strip())

    def token_servidor(self) -> str:
        """Prova, sem revelar a frase, de que o outro lado tem a mesma frase."""
        f = self.frase() or ""
        return hmac.new(f.encode(), b"cerebro-sync-v1", hashlib.sha256).hexdigest()

    def _conexao(self, tabela: str):
        return (self.app.banco if tabela in BANCO_FINANCEIRO else self.app.memoria)

    def _colunas(self, tabela: str) -> list[str]:
        if tabela not in self._cols:
            con = self._conexao(tabela)
            linhas = con.consultar(f"PRAGMA table_info({tabela})") if hasattr(con, "consultar") else con.q(f"PRAGMA table_info({tabela})")
            self._cols[tabela] = [l["name"] for l in linhas]
        return self._cols[tabela]

    def _q(self, tabela: str, sql: str, args=()):
        con = self._conexao(tabela)
        return con.consultar(sql, args) if hasattr(con, "consultar") else con.q(sql, args)

    def _x(self, tabela: str, sql: str, args=()):
        con = self._conexao(tabela)
        return con.executar(sql, args) if hasattr(con, "executar") else con.x(sql, args)

    # ------------------------------------------------------------ pacote de mudanças
    def coletar(self, desde: dict) -> dict:
        pacote = {}
        for tabela, carimbo in TABELAS.items():
            if tabela not in self._colunas(tabela):
                continue
            col = carimbo if carimbo in self._colunas(tabela) else "id"
            marca = desde.get(tabela, "")
            linhas = self._q(tabela, f"SELECT * FROM {tabela} WHERE COALESCE({col},'') > ? ORDER BY {col} LIMIT 2000",
                             (marca,))
            if linhas:
                pacote[tabela] = {"col": col, "linhas": linhas}
        return pacote

    def aplicar(self, pacote: dict) -> int:
        """Aplica mudanças recebidas, resolvendo conflitos pela edição mais recente."""
        aplicados = 0
        for tabela, bloco in pacote.items():
            if tabela not in TABELAS or tabela not in self._colunas(tabela):
                continue
            cols = self._colunas(tabela)
            chave = "ref" if "ref" in cols else "id"
            carimbo = TABELAS[tabela] if TABELAS[tabela] in cols else None
            for linha in bloco["linhas"]:
                linha = {k: v for k, v in linha.items() if k in cols}
                if chave not in linha:
                    continue
                existe = self._q(tabela, f"SELECT * FROM {tabela} WHERE {chave} = ?", (linha[chave],))
                if existe:
                    atual = existe[0]
                    if carimbo and str(linha.get(carimbo) or "") <= str(atual.get(carimbo) or ""):
                        continue          # o que já tenho é mais novo: mantém
                    campos = [c for c in linha if c != "id" and c in cols]
                    self._x(tabela, f"UPDATE {tabela} SET {', '.join(f'{c}=?' for c in campos)} WHERE {chave}=?",
                            [linha[c] for c in campos] + [linha[chave]])
                else:
                    campos = [c for c in linha if not (c == "id" and chave == "ref")]
                    self._x(tabela, f"INSERT OR IGNORE INTO {tabela}({', '.join(campos)}) VALUES({', '.join('?' * len(campos))})",
                            [linha[c] for c in campos])
                aplicados += 1
        if aplicados and hasattr(self.app, "aprendizado"):
            self.app.aprendizado._cache.clear()          # vetores recalculam o que faltar
        return aplicados

    def marcas(self, pacote: dict, atuais: dict) -> dict:
        saida = dict(atuais)
        for tabela, bloco in pacote.items():
            col = bloco["col"]
            saida[tabela] = max([str(l.get(col) or "") for l in bloco["linhas"]] + [saida.get(tabela, "")])
        return saida

    # ------------------------------------------------------------ cliente (puxa e envia)
    def estado_remoto(self) -> dict:
        try:
            self._colunas("notas")
        except Exception:
            pass
        return self.app.aprendizado and json.loads(self.app.aprendizado.ler_estado("sinc_marcas", "{}") or "{}") or {}

    def sincronizar_agora(self) -> dict:
        import urllib.error
        import urllib.request
        if not (self.cfg.get("ativo") and self.cfg.get("papel") == "cliente"):
            return {"ok": False, "mensagem": "Este aparelho não é cliente de sincronização."}
        frase = self.frase()
        if not frase:
            return {"ok": False, "mensagem": "Defina a frase de sincronização em Ajustes."}
        url = self.cfg.get("servidor", "").rstrip("/") + "/api/sinc/trocar"
        with self.trava:
            marcas = json.loads(self.app.aprendizado.ler_estado("sinc_marcas", "{}") or "{}")
            meu = self.coletar(marcas)
            corpo = {"token": self.token_servidor(), "desde": marcas, "mudancas": cifrar(frase, meu)}
            try:
                req = urllib.request.Request(url, data=json.dumps(corpo).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    resposta = json.loads(r.read())
            except urllib.error.HTTPError as erro:
                msg = "Frase de sincronização diferente entre os aparelhos." if erro.code == 403 else f"O central recusou ({erro.code})."
                self.ultimo["erro"] = msg
                return {"ok": False, "mensagem": msg}
            except Exception as erro:
                self.ultimo["erro"] = str(erro)
                return {"ok": False, "mensagem": f"Não consegui falar com o central: {erro}"}
            recebido = decifrar(frase, resposta["mudancas"])
            aplicados = self.aplicar(recebido)
            marcas = self.marcas(meu, marcas)                 # o que enviei
            marcas = self.marcas(recebido, marcas)            # o que recebi
            self.app.aprendizado.gravar_estado("sinc_marcas", json.dumps(marcas, ensure_ascii=False))
            enviados = sum(len(b["linhas"]) for b in meu.values())
            self.ultimo = {"quando": self.app.agora().isoformat(), "enviados": enviados, "recebidos": aplicados, "erro": None}
            return {"ok": True, "enviados": enviados, "recebidos": aplicados}

    # ------------------------------------------------------------ servidor (atende o cliente)
    def atender(self, corpo: dict) -> dict:
        frase = self.frase()
        if not frase:
            raise PermissionError("Sincronização não configurada neste aparelho.")
        if not hmac.compare_digest(corpo.get("token", ""), self.token_servidor()):
            raise PermissionError("Frase de sincronização incorreta.")
        with self.trava:
            recebido = decifrar(frase, corpo["mudancas"])
            self.aplicar(recebido)
            meu = self.coletar(corpo.get("desde", {}))
            return {"mudancas": cifrar(frase, meu)}
