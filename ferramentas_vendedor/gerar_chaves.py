"""
Rode UMA vez, no SEU computador (nunca entregue a chave privada a ninguém).

    python gerar_chaves.py

Cria chave_privada.pem (guarde em local seguro, com backup) e mostra a chave
pública, que deve ser colada em CHAVE_PUBLICA no arquivo licenca.py antes de
empacotar o app para venda.
"""
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

destino = Path(__file__).with_name("chave_privada.pem")
if destino.exists():
    raise SystemExit("Já existe uma chave_privada.pem aqui. Não sobrescreva: licenças antigas deixariam de valer.")
privada = Ed25519PrivateKey.generate()
destino.write_bytes(privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
publica = privada.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
print("Chave privada salva em", destino)
print("\nCole esta linha no licenca.py:\n")
print(f'CHAVE_PUBLICA = "{base64.b64encode(publica).decode()}"')
