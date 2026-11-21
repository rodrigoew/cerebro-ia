# Núcleo

Segundo cérebro local: IA no seu computador, voz, e-mails, agenda, finanças, decisões e processos.
O guia completo de uso está em [LEIAME.md](LEIAME.md).

A esteira de produção para YouTube e TikTok está documentada em [documentos/CRIADOR.md](documentos/CRIADOR.md).
Ela acrescenta fila persistente, seleção de trechos, perfis de edição, agendamento via Buffer e acompanhamento de resultados.

## Estrutura do repositório

```
├── app.py, cerebro.py, …        o aplicativo (Python)
├── interface.html               estrutura da interface
├── static/                      estilo.css e js/ (um módulo por tela)
├── vendor/freellmapi/           submódulo Git (projeto de terceiros, licença MIT)
├── scripts/                     instalar, atualizar e publicar versões
├── empacotar/                   gerar a versão instalável (Windows)
├── ferramentas_vendedor/        licenças para venda (a chave privada nunca entra no Git)
└── documentos/                  licença de uso, privacidade, terceiros, como vender
```

## Abrir e atualizar

Baixe o **Nucleo.exe** em Releases e abra. Ele atualiza pelo Git e abre o app a cada uso. O próprio GitHub gera o executável pelo `.github/workflows/lancador.yml`.

## Clonar em outro computador

```
git clone --recurse-submodules <endereço do seu repositório> nucleo
cd nucleo
instalar.bat
```

## Fluxo de versões

1. Trabalhe e teste normalmente.
2. Anote as mudanças no `CHANGELOG.md`.
3. Rode `scripts\nova_versao.bat`: ele atualiza o `VERSION`, faz o commit, cria a tag (`v0.9.1`, por exemplo) e oferece enviar ao GitHub.

O FreeLLMAPI fica preso numa versão testada. Para trazer a versão nova dele, rode `scripts\atualizar_freellmapi.bat`, teste e faça o commit (ou crie uma nova versão do Núcleo).
