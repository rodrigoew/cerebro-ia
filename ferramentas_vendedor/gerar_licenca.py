"""
Gera a licença de um comprador.

    python gerar_licenca.py "Nome do Amigo" amigo@email.com            (vitalícia)
    python gerar_licenca.py "Nome do Amigo" amigo@email.com 2027-12-31 (com validade)

Cria licenca-<email>.json. Envie esse arquivo (ou o texto dele) ao comprador;
ele cola em Ajustes > Licença.
"""
import base64
import datetime as dt
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
nome, email = sys.argv[1], sys.argv[2]
validade = sys.argv[3] if len(sys.argv) > 3 else None
if validade:
    dt.date.fromisoformat(validade)
privada = serialization.load_pem_private_key(Path(__file__).with_name("chave_privada.pem").read_bytes(), None)
dados = {"produto": "Núcleo", "nome": nome, "email": email, "emitida": dt.date.today().isoformat(),
         "validade": validade, "edicao": "completa"}
assinatura = privada.sign(json.dumps(dados, sort_keys=True, ensure_ascii=False).encode())
licenca = {"dados": dados, "assinatura": base64.b64encode(assinatura).decode()}
saida = Path(f"licenca-{email}.json")
saida.write_text(json.dumps(licenca, ensure_ascii=False, indent=2), encoding="utf-8")
print("Licença criada:", saida.resolve())
