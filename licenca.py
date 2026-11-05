"""
Licença de uso (para vender a amigos).

Como funciona:
  - Na primeira execução começa uma avaliação de DIAS_AVALIACAO dias.
  - Você (vendedor) gera uma licença com ferramentas_vendedor/gerar_licenca.py,
    assinada com a SUA chave privada (Ed25519). O app confere a assinatura com a
    chave pública embutida abaixo. Ninguém consegue gerar licenças sem a sua
    chave privada.
  - Funciona offline: não há servidor de ativação.

Enquanto CHAVE_PUBLICA estiver vazia, o app roda em modo pessoal (sem licença).
Para vender: rode ferramentas_vendedor/gerar_chaves.py uma vez e cole aqui a
chave pública que ele mostrar.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
from pathlib import Path

CHAVE_PUBLICA = ""          # cole aqui a chave pública gerada (texto base64)
DIAS_AVALIACAO = 14
PRODUTO = "Núcleo"


def _verificar(dados: dict, assinatura_b64: str) -> bool:
    if not CHAVE_PUBLICA:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        chave = Ed25519PublicKey.from_public_bytes(base64.b64decode(CHAVE_PUBLICA))
        mensagem = json.dumps(dados, sort_keys=True, ensure_ascii=False).encode()
        chave.verify(base64.b64decode(assinatura_b64), mensagem)
        return True
    except Exception:
        return False


class Licenca:
    def __init__(self, pasta_dados: Path):
        self.pasta = pasta_dados
        self.arquivo = pasta_dados / "licenca.json"
        self.marca = pasta_dados / ".instalado_em"
        pasta_dados.mkdir(parents=True, exist_ok=True)
        if not self.marca.exists():
            self.marca.write_text(dt.date.today().isoformat())

    def status(self) -> dict:
        if not CHAVE_PUBLICA:
            return {"modo": "pessoal", "liberado": True, "mensagem": "Uso pessoal (licenciamento desativado)."}
        if self.arquivo.exists():
            try:
                conteudo = json.loads(self.arquivo.read_text(encoding="utf-8"))
                dados, assinatura = conteudo["dados"], conteudo["assinatura"]
                if _verificar(dados, assinatura):
                    validade = dados.get("validade")
                    if validade and dt.date.fromisoformat(validade) < dt.date.today():
                        return {"modo": "expirada", "liberado": False, "titular": dados.get("nome"),
                                "mensagem": f"Licença expirou em {validade}. Fale com quem vendeu para renovar."}
                    return {"modo": "licenciado", "liberado": True, "titular": dados.get("nome"),
                            "email": dados.get("email"), "validade": validade, "edicao": dados.get("edicao", "completa"),
                            "mensagem": f"Licenciado para {dados.get('nome')}"
                                        + (f" até {validade}." if validade else " (vitalícia).")}
            except Exception:
                pass
            return {"modo": "invalida", "liberado": False, "mensagem": "Arquivo de licença inválido."}
        inicio = dt.date.fromisoformat(self.marca.read_text().strip())
        restam = DIAS_AVALIACAO - (dt.date.today() - inicio).days
        if restam > 0:
            return {"modo": "avaliacao", "liberado": True, "dias_restantes": restam,
                    "mensagem": f"Avaliação: faltam {restam} dia(s)."}
        return {"modo": "avaliacao_encerrada", "liberado": False,
                "mensagem": "O período de avaliação terminou. Instale sua licença em Ajustes > Licença."}

    def instalar(self, texto: str) -> dict:
        try:
            conteudo = json.loads(texto)
            dados, assinatura = conteudo["dados"], conteudo["assinatura"]
        except Exception:
            raise ValueError("Esse texto não é uma licença válida.")
        if not _verificar(dados, assinatura):
            raise ValueError("Assinatura da licença não confere.")
        self.arquivo.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.status()
