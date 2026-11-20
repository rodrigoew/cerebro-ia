# Histórico de versões

## 0.19.0
- O agente responde em fluxo de verdade (Claude e IA local): a primeira palavra sai enquanto ele ainda pensa ou consulta ferramentas, e a voz começa na primeira frase.
- Claude com cache do prompt (respostas mais rápidas a partir da segunda) e modelo automático: Haiku na voz, Sonnet no texto.
- Mais ação: lê e-mails e escreve rascunhos de resposta (com permissão), encadeia ferramentas sem pedir confirmação do óbvio e recebe um panorama do momento (contas, promessas, agenda) para pensar com contexto e avisar o que for relevante.
- Voz: descarta trechos que não são você falando (TV, conversa ao fundo); transcrição mais rápida no processador; no modo conversa, depois de 45 s sem falar com ele, só reage ao nome do assistente.
- FreeLLMAPI sem chaves cadastradas sai do caminho (antes cada pergunta geral tentava e falhava, somando atraso).
- Tela inicial sugere ligar o Claude enquanto o cérebro estiver no modo local.

## 0.18.0
- Novo cérebro em forma de agente: a IA conduz a conversa com o histórico das últimas mensagens, usa as ferramentas do Núcleo (agenda, financeiro, e-mails, memória, pessoas, promessas, clima, decisões, organizar, processos, globo, ações no computador) e responde em linguagem natural, curta e falável. As regras antigas ficam como reserva quando não há IA.
- Ajustes > Cérebro: escolha quem pensa (Local, Claude com o crédito do Max, nuvem compatível ou regras), o modelo do Claude (Haiku, o mais rápido, ou Sonnet) e a espera do microfone.
- Botão "Ligar modo natural": Claude + voz Thalita + ações simples sem perguntar, com aviso claro do que vai para a nuvem.
- Voz: fala só a frase natural da resposta (nunca a lista do cartão); o microfone percebe o fim da fala mais rápido (600 ms, ajustável).
- Status mostra o tempo médio das respostas.

## 0.17.0
- Globo 3D ao vivo (God's Eye View) como ação do Núcleo: "mostra os voos sobre BH", "tem incêndio perto de São Paulo?", "satélites agora", "abre o globo". Abre numa aba dentro do app, já no lugar e nas camadas certos. Dados públicos, no seu computador; não busca pessoas.
- Entra como submódulo (scripts/adicionar_globo.bat) e instala com scripts/instalar_globo.bat. Liga em Ajustes > Globo ao vivo.
- Pesado em 3D: recomendado no PC gamer; no notebook funciona, porém mais lento.

## 0.16.2
- Perguntas de conselho e de sim/não recebem resposta direta primeiro ("Sim, leve o guarda-chuva: 86% de chance de chuva hoje"), com os dados embaixo como apoio:
  - no clima, por regras (guarda-chuva, vai chover, casaco, calor), mesmo sem a IA;
  - na agenda, no financeiro e nas listas, a IA local escreve a frase usando só os dados do cartão.
- "Tenho tempo para…", "estou livre…", "consigo encaixar…" consultam a agenda (antes eram confundidos com clima pela palavra "tempo").
- "Com calma", "com folga" etc. não são mais tratados como nome de pessoa na agenda.

## 0.16.1
- Corrigido: compromissos da agenda do Núcleo não apareciam na tela Agenda nem no resumo do dia (já estavam gravados; só não eram lidos ali).
- O resultado do que o Núcleo faz aparece como "Feito pelo Núcleo", com texto normal e o botão do convite .ics.

## 0.16.0
- Permissões por ação com memória: na primeira vez o Núcleo pergunta (Fazer e não perguntar mais / Fazer só agora / Agora não / Nunca) e passa a respeitar a sua escolha. Toda ação fica no histórico, virando memória.
- Ações delicadas (instalar atualizações, desligar) sempre pedem confirmação por clique, mesmo autorizadas.
- Nova tela Ajustes > Permissões das ações, para rever e mudar cada decisão.
- Corrigido: "organiza meus downloads" agora é a ação da pasta, e "organiza isso: ..." segue organizando pensamentos.

## 0.15.0
- Permissões para tudo o que o Núcleo faz (agenda, lembretes, financeiro, anotações, memória, tarefas), no mesmo modelo das ações no computador: na primeira vez ele pergunta; você responde (botão ou voz) "sim", "sim, sempre", "não" ou "nunca", e a decisão é lembrada e vira memória. Tudo editável em Ajustes > Permissões.
- "Lembre que…" guarda fatos sobre você na memória (com permissão).
- Pedidos que ele ainda não sabe executar: diz com clareza e oferece registrar como tarefa.
- Agenda própria do Núcleo: "adiciona/marca/agenda um compromisso…" cria o evento (com confirmação), lembrete na véspera e 1 hora antes, aparece junto das outras agendas e pode ser levado ao Google/Outlook por um convite .ics.
- Entende "esse compromisso" a partir da mensagem anterior.
- Corrigido: pedidos de adicionar compromisso eram tratados como consulta; "o que tenho no dia X?" volta a consultar a agenda.
- Gmail: mensagens de erro claras; a senha de app é limpa de espaços, validada e testada ao guardar.
- O Nucleo.exe não vai mais para o Git.

## 0.14.0
- Indicador flutuante compacto: cápsula de 150×40 no canto superior direito, quase transparente em espera.
- Respostas mais rápidas:
  - o modelo é aquecido ao abrir o app e fica na placa por 60 minutos;
  - em placas pequenas, a busca por significado roda no processador (o modelo de conversa não sai mais da placa a cada pergunta);
  - contexto de 4 mil tokens para modelos pequenos;
  - perguntas diretas pulam a consulta extra de roteamento;
  - o roteador ficou mais leve.
- Cada resposta mostra o tempo até começar e o tempo total.
- Vozes neurais naturais da Microsoft (Thalita, Francisca, Antônio), opcionais e com a Kokoro como reserva sem internet.
- O notebook usa também o Whisper do PC (placa de vídeo) para transcrever a fala.
- Suporte ao Tailscale: o notebook alcança a IA e o Whisper do PC mesmo fora de casa.

## 0.13.0
- Nucleo.exe: lançador único que confere o GitHub a cada abertura, atualiza com segurança (só avança, nunca apaga trabalho seu) e abre o app sem console. Em computador novo, instala Git e Python, baixa o projeto, instala tudo e cria o atalho.
- O GitHub gera o Nucleo.exe sozinho (GitHub Actions) e publica em Releases.
- Aviso de versão nova e botão "Atualizar e reiniciar" em Ajustes.
- O notebook usa a IA do PC quando estiver na mesma rede (pedidos autenticados pela frase secreta; só conversa e busca), e volta para a própria IA fora de casa.
- Sincronização automática a cada 5 minutos no aparelho secundário.
- Ajustes: seção "Acesso na rede" e "Atualizações".
- Placas de 12 GB passam a usar o qwen3:8b (o 14b só a partir de 16 GB).

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
