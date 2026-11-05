# Histórico de versões

## 0.12.0
- Nova tela inicial em palco, em tela cheia: o núcleo no centro pergunta o que você quer ver e mostra só o que importa agora; a resposta surge do núcleo em destaque; conversa, lembretes, novidades, memória e status ficam recolhidos em abas.
- Legenda na tela com o que você disse e o que o assistente está falando.
- Indicador flutuante (sempre por cima) mostrando quando ele está ouvindo, pensando ou falando, mesmo com a janela minimizada.
- Abre em tela cheia (F11 alterna); menu lateral recolhível.
- Ícone próprio na janela, na barra de tarefas, na bandeja, no executável e no atalho (scripts\criar_atalho.bat).
- Detecção de placa de vídeo mais robusta no instalador.
- Roteamento automático para o FreeLLMAPI: perguntas gerais vão sozinhas, sem nenhum dado pessoal; o que envolve seus e-mails, finanças e notas fica local (ou vai mascarado, no modo "automático total"). Se a nuvem falhar, a IA local assume; após 3 falhas, um disjuntor deixa tudo local por 10 minutos.
- Dois provedores de nuvem ao mesmo tempo: respostas automáticas (FreeLLMAPI, grátis) e Aprofundar (Claude, usando o crédito mensal da API do plano Max).
- O instalador do Núcleo agora instala o Node.js, as dependências e compila o FreeLLMAPI, e liga o roteador junto com o app.

## 0.11.0
- Sincronização criptografada entre aparelhos (central + secundários + PWA no celular/tablet).
- Vigia proativo (widget sempre ativo) observando títulos de janela, com avisos de risco.
- Segurança: cookie httpOnly, anti-DNS-rebinding, anti-força bruta, LAN opcional, sincronização AES-GCM.
- Scripts de publicação no GitHub (repositório privado recomendado).

## 0.10.0
- Cérebro: a IA local escolhe ferramentas de forma nativa (entende pedidos em linguagem livre); respostas em fluxo, com a voz começando já na primeira frase.
- Pessoas e compromissos: promessas detectadas nos e-mails (suas e dos outros), fichas de contatos, avisos de prazo.
- Bandeja do Windows, atalho global (Ctrl+Alt+Espaço) e notificações nativas; fechar a janela mantém o app ativo.
- Busca global (Ctrl+K) em e-mails, pessoas, decisões, ideias, contas, lembretes e conhecimento.
- Telas menores (1366×768), painéis recolhíveis, teclado no quadro de ideias, "desfazer" ao apagar.
- Interface dividida em módulos (static/estilo.css e static/js/*.js).

## 0.9.0
- Núcleo como segundo cérebro: Mente (pensamentos, ideias, decisões, processos).
- E-mails de vários provedores (Gmail, Microsoft, IMAP, POP) com rascunhos de resposta.
- Cores de estado e animações; licença para venda; primeiros passos.
- FreeLLMAPI integrado como submódulo (uso pessoal), iniciado junto com o app.
