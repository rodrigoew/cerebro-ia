# Núcleo, o seu segundo cérebro

Uma secretária que roda no seu computador. Ela organiza pensamentos, ideias, decisões e processos, cuida de vários e-mails ao mesmo tempo, da agenda, do financeiro e das ações no PC, e conversa por voz. A IA é local; a nuvem só entra quando você aprova.

Telas:

- **Assistente** (o nome é seu: Núcleo, Jarvis, Atlas…): conversa por texto e voz, com o núcleo animado que muda de cor conforme a situação.
- **Hoje:** o resumo do dia e o briefing narrado ("bom dia").
- **E-mails:** todas as contas num lugar só, com rascunhos de resposta. Nada é enviado.
- **Mente:** organizar pensamentos, ideias, decisões e processos.
- **Agenda e Financeiro:** calendários unificados e contas a pagar e a receber.
- **Ajustes:** contas, voz, briefing, clima, nuvem e licença.

Na primeira vez, um assistente de **primeiros passos** pergunta seu nome, o nome do assistente, a voz e a cidade, e depois instala a IA local.

## Novidades da 0.11

- **Sincronização entre aparelhos:** PC, notebook, tablet e iPhone com a mesma memória. Um computador é o central; o notebook sincroniza; tablet e iPhone acessam pelo navegador (PWA). A troca é criptografada com a sua frase secreta e roda na sua rede. Veja `documentos/APARELHOS.md`.
- **Widget sempre ativo (vigia):** em segundo plano no Windows, observa só o título da janela ativa e avisa diante de risco financeiro (compra por impulso, transferência) ou técnico (comando perigoso, configuração sensível), com a dica contextualizada pelo seu financeiro.
- **Segurança reforçada:** sessão por cookie httpOnly, proteção contra DNS rebinding, trava anti-força bruta, acesso pela rede desligado por padrão e sincronização cifrada. Veja `documentos/SEGURANCA.md`.
- **Publicar no GitHub:** `scripts\publicar_github.bat` envia para github.com/rodrigoew/cerebro-ia.

## Novidades da 0.10

- **Linguagem livre:** a IA local escolhe sozinha a ferramenta certa (agenda, financeiro, ações, decisões…). Os atalhos por regras continuam como caminho rápido.
- **Respostas em fluxo:** o texto aparece enquanto a IA escreve. No modo conversa, a voz começa já na primeira frase.
- **Pessoas e compromissos** (menu **Pessoas**): o app lê os e-mails no seu computador e encontra promessas com prazo, tanto as suas ("te envio amanhã") quanto as dos outros ("retorno na sexta"). Cada pessoa tem uma ficha com conversas, combinados, agenda, decisões e notas, além de um "Resumo da relação" feito pela IA local. Pergunte: "o que eu prometi?", "o que me devem?", "o que tenho com a Ana?". Promessas suas atrasadas deixam o núcleo laranja ou vermelho e entram no briefing.
- **Bandeja do Windows:** o ícone fica perto do relógio. Fechar a janela só esconde o app, que continua lembrando você. Use **Ctrl+Alt+Espaço** de qualquer programa para chamar o assistente (troque em `atalho_global`). As notificações do Windows avisam de lembretes na hora, contas vencendo e promessas atrasadas.
- **Busca global (Ctrl+K):** encontra e-mails, pessoas, decisões, ideias, processos, contas, lembretes e conhecimento, ou faz a pergunta direto ao assistente. **Ctrl+Shift+K** vai direto à conversa.
- **Notebooks:** em telas de 1366×768, os painéis da direita viram um botão "Painéis".
- **Teclado e desfazer:** no quadro de ideias, as setas movem o cartão de coluna e a tecla Delete apaga. Apagar ideias, decisões, processos, lançamentos e aprendizados mostra a opção "Desfazer" por alguns segundos.

## Cores do núcleo (estados)

| Cor | Significa |
|---|---|
| Âmbar | Tudo em ordem |
| Laranja | Atenção: algo vence hoje ou amanhã, há uma confirmação pendente ou uma atualização de segurança |
| Vermelho pulsante | Risco: conta vencida, ação que falhou ou ação de risco alto aguardando você |
| Sálvia (verde) | Confirmado: ação concluída, item guardado ou resposta com confiança alta |
| Ameixa (lilás) | Consultando a nuvem (Claude ou outro provedor que você aprovou) |
| Champanhe | Aprendendo: uma correção ou decisão sua virou conhecimento |

A cor de fundo reflete o estado geral do dia, com os motivos listados embaixo do núcleo. Cada resposta muda a cor por alguns segundos e emite uma onda a partir do centro. As respostas da IA local mostram um selo de **confiança**: alta quando a resposta se baseia em 2 ou mais registros seus, média quando há pouca base e baixa quando vem de conhecimento geral. No briefing, cada assunto acende na sua cor; uma conta vencida, por exemplo, aparece em vermelho.

## E-mails: vários provedores ao mesmo tempo

Adicione as contas em **Ajustes**, na seção **Contas de e-mail**:

| Tipo | Como conectar | O que dá para fazer |
|---|---|---|
| Gmail / Google Workspace | senha de app (myaccount.google.com/apppasswords, com verificação em duas etapas) | ler, rascunhos, lida/não lida, sinalizar, arquivar |
| Microsoft (Outlook, Hotmail, 365) | botão **Conectar com a Microsoft** (login moderno com código) | ler, rascunhos, lida/não lida, sinalizar, arquivar |
| Outro provedor IMAP | servidor, porta e senha | ler, rascunhos, lida/não lida, sinalizar, arquivar |
| Outro provedor POP | servidor, porta e senha | ler; rascunho fica no app, com o botão "Abrir no meu programa de e-mail" |

Na tela **E-mails**, você filtra por não lidos, pedem resposta, importantes ou pessoas, e escolhe a conta. Ao abrir uma mensagem, clique em **Rascunhar resposta**, escreva a orientação ("aceitar e pedir a nota fiscal até sexta") e o tom, e a IA local redige a resposta. Você revisa e salva como rascunho na pasta Rascunhos da própria conta. **O envio é sempre feito por você**, no seu programa de e-mail.

As contas Microsoft exigem um ID de aplicativo gratuito do Entra ID, cadastrado uma única vez. O passo a passo está em `documentos/VENDER.md`, no item 1.3.

## Mente: a secretária

- **Organizar pensamentos:** escreva tudo o que está na cabeça, do jeito que vier. A IA separa em tarefas, lembretes, ideias, decisões e notas, e você escolhe o que guardar. Pela conversa, também funciona: "organiza: …".
- **Ideias:** um quadro com as colunas Novas, Explorando, Em andamento, Feitas e Descartadas. "ideia: …" na conversa já cai aqui.
- **Decisões:** "preciso decidir entre X e Y" abre uma análise com opções, prós e contras, critérios e perguntas para pensar. **A decisão é sua**: você registra a escolha, o motivo e uma data para revisar. A decisão vira conhecimento, e a revisão vira lembrete.
- **Processos:** checklists reutilizáveis, como "cria um processo de fechamento do mês: conferir faturas; lançar despesas; enviar relatório". Para usar, diga "inicia o processo fechamento do mês" e marque os passos conforme faz.

## Nuvem: Claude ou provedor compatível com OpenAI

Em **Ajustes**, na seção **Nuvem**, escolha **Claude** (o único com pesquisa na web) ou **Compatível com OpenAI**. A segunda opção serve para GPT, OpenRouter, LM Studio ou um roteador local, como o FreeLLMAPI em `http://localhost:3001/v1`. O FreeLLMAPI é só para uso pessoal: ele envia os pedidos a vários provedores gratuitos, com limites e privacidade que variam. As chaves ficam no cofre do sistema. As regras não mudam: prévia, dados mascarados e confirmação. Se quiser desligar a nuvem de vez, escolha "Nunca enviar".

## Vender para amigos

O app está preparado para venda: tem licença com chave assinada e 14 dias de avaliação, edição comercial, versão instalável (PyInstaller e Inno Setup), primeiros passos sem dados pessoais e documentos (licença de uso, privacidade e componentes de terceiros). Veja `documentos/VENDER.md`.

## Instalação rápida (Windows)

1. Instale o **Python 3.12** em python.org e marque **Add Python to PATH**. As versões 3.10 a 3.12 também servem; a 3.13 pode não ter os pacotes de voz.
2. Atualize o driver da placa NVIDIA.
3. Dê dois cliques em **instalar.bat**. Ele instala os pacotes Python, o Ollama (pelo winget), os modelos de IA, o Whisper e as vozes em português. São cerca de 9 GB de download, só na primeira vez.
4. Preencha o `config.json` (veja o passo 3 abaixo) e abra o app com **iniciar.bat**.

Se faltar algo depois, use o botão **Instalar o que falta** no Núcleo. Ele mostra o progresso de cada etapa.

## 1. Instalar manualmente (alternativa)

Instale o Python 3.10 ou mais novo (python.org). No Windows, marque "Add Python to PATH". Depois, dentro desta pasta:

    pip install -r requirements.txt

O `pywebview` abre o app numa janela própria. Se ele não instalar, o app abre no Edge ou no Chrome em modo aplicativo, sem barra de endereço.

## 2. Preparar contas e agendas

**Gmail:** ative a verificação em duas etapas e crie uma senha de app em myaccount.google.com/apppasswords.

**Outras contas (IMAP):** peça ao provedor o servidor IMAP e a porta (normalmente 993, com SSL).

**Agendas** (quantas você quiser):
- Google Agenda: em Configurações, abra cada agenda e copie o "Endereço secreto no formato iCal".
- Outlook/Microsoft 365: em Configurações, abra Calendário e depois Calendários compartilhados. Use "Publicar um calendário" e copie o link ICS.

## 3. Configurar

Copie `config.exemplo.json` para `config.json` e preencha:

- `contas`: suas caixas de e-mail. O campo `contexto` liga cada conta a uma carteira.
- `calendarios_ics`: os links das agendas.
- `carteiras` e `categorias`: ajuste como preferir.

Depois, guarde as senhas no cofre do sistema e teste:

    python app.py --salvar-senha "Pessoal"
    python app.py --salvar-senha "PLURO"
    python app.py --testar

A chave da API do Claude é opcional e só serve para as perguntas que você decidir aprofundar. Veja a seção "Núcleo" abaixo.

## 4. Usar

    python app.py

O app abre e já atualiza e-mails e agendas. Para repetir a leitura quando quiser, use "Atualizar agora". Ao abrir, se a última leitura tiver mais de uma hora, o app atualiza sozinho.

## 5. Abrir sozinho todo dia útil

    python app.py --agendar 07:30

No Windows, a tarefa é criada no Agendador de Tarefas. No Mac ou Linux, o comando mostra a linha que deve ser colada no `crontab -e`.

## Como o financeiro funciona

- Faturas e boletos encontrados nos e-mails entram sozinhos como "a confirmar", com valor e vencimento lidos do e-mail. Se o e-mail não traz algum desses dados, o campo fica vazio.
- Cobranças de ferramentas (domínios em `dominios_ferramentas`) não entram.
- Quando você marca como paga uma conta que se repete, a próxima ocorrência é lançada automaticamente.
- Contas vencidas, que vencem hoje ou nos próximos 3 dias sobem para as 3 do dia, junto com os e-mails. Para desligar, use `"contas_com_vencimento_podem_subir": false`.
- Lançamentos vindos de e-mail que você excluir não são importados de novo.
- Os dados ficam em `saida/financeiro.db`, no seu computador. Faça backup desse arquivo.

## IA local (Ollama) — instalar uma vez

A IA local roda na sua placa NVIDIA, sem internet. Ela entende pedidos com frases livres, responde perguntas usando a sua memória e resume as notícias das fontes.

1. Instale o Ollama em **ollama.com/download** e abra o programa. Ele fica rodando ao lado do relógio do Windows.
2. No terminal, baixe os dois modelos:

       ollama pull qwen3:8b
       ollama pull bge-m3

   O `qwen3:8b` conversa e resume (cerca de 5 GB). O `bge-m3` faz a busca por significado (cerca de 1,2 GB).
3. Rode `python app.py --testar`. A linha "IA local" deve aparecer como OK.

Se a sua placa tiver 12 GB ou mais, troque `"modelo"` por `qwen3:14b` em `llm_local` no config, para ter respostas melhores. Sem o Ollama aberto, o app continua funcionando só com regras e busca.

## Como o Núcleo aprende

O Núcleo aprende pela memória, sem retreinar o modelo. Assim, nada fica gravado de forma irreversível.

- **Toda conversa fica guardada.** Abaixo de cada resposta há os botões **Útil**, **Não ajudou** e **Corrigir**.
- **Correções têm prioridade máxima.** Ao corrigir, o texto vira conhecimento fixo e vale já na próxima resposta.
- **Respostas marcadas como úteis** voltam como referência em perguntas parecidas. As marcadas como "Não ajudou" são descartadas.
- **Consolidação diária.** Às 22h (`hora_consolidacao`), ou na abertura seguinte se o app estava fechado, a IA local lê as conversas e notas novas e extrai fatos duráveis: pessoas e papéis, projetos, decisões, preferências e fornecedores.
- **Tudo fica visível em "O que sei sobre você".** Lá você edita, apaga ou ensina algo diretamente. O texto do campo `cerebro.perfil` no config também entra em todas as respostas.

## Ajustes (sem editar arquivos)

O menu **Ajustes** reúne tudo o que é mais comum mudar. As mudanças valem na hora e são gravadas no `config.json`, com uma cópia de segurança em `config.json.bak`.

- **Assistente:** troque o nome "Núcleo" por outro, como "Jarvis" ou "Atlas". O novo nome aparece no menu e nas respostas e passa a ser a palavra de ativação da escuta contínua. A palavra de ativação também pode ser diferente do nome. Prefira nomes curtos e fáceis de pronunciar, que o reconhecimento de voz acerta melhor.
- **Voz:** escolha entre **Dora** (feminina), **Alex** e **Santa** (masculinas), da Kokoro, ou entre **Faber**, **Cadu** e **Jeff** (masculinas, Piper). O botão **Ouvir** toca uma amostra, e a velocidade da fala é ajustável. As vozes da Kokoro são baixadas pelo instalador (cerca de 120 MB).
- **Briefing:** ligue e desligue cada bloco, mude a ordem com as setas e escolha o estilo. No **completo**, ele dá mais detalhes; no **curto**, cada assunto vira uma frase só. Também dá para definir a quantidade de notícias e de e-mails citados, os temas das notícias, uma frase extra na abertura e no fechamento e o horário em que o app abre sozinho no briefing. O botão **Salvar e ouvir agora** serve para testar na hora.
- **Clima:** cadastre até 6 cidades pela busca. Para cada uma, escolha o que dizer no briefing: **agora** (temperatura atual), **hoje** (mínima, máxima e chuva), **amanhã** ou **próximos dias** (faixa de temperatura e o dia com mais chance de chuva). Também dá para perguntar direto: "vai chover amanhã em Recife?", "como está o tempo?" ou "previsão da semana em São Paulo".

## Briefing narrado ("bom dia")

Diga **"bom dia"** no modo conversa (ou clique na sugestão "bom dia" no Núcleo) e o app abre em tela cheia o briefing do dia. O núcleo narra o dia em voz alta e, a cada assunto, um cartão surge do centro e depois se acomoda na faixa de baixo, com legenda. Os assuntos são:

1. o que mudou desde ontem;
2. clima da sua cidade (mínima, máxima, chance de chuva, umidade e vento);
3. agenda do dia;
4. e-mails que pedem atenção;
5. vencimentos do financeiro;
6. lembretes;
7. atualizações de segurança do computador;
8. notícias das suas fontes, com foto;
9. fechamento com o foco do dia.

As frases são montadas a partir dos seus dados reais, sem a IA, para não inventar números nem nomes.

- **Controles:** `Espaço` pausa, `→` pula o assunto, `Esc` fecha, e o botão **Tela cheia** ocupa o monitor inteiro.
- **Clima:** usa o Open-Meteo, que é gratuito e não exige chave. Ele recebe apenas as coordenadas configuradas em `clima`. O exemplo já vem com Belo Horizonte.
- **Notícias:** escolha os temas e a quantidade em `briefing`. As fotos vêm dos próprios feeds e ficam guardadas no computador.
- **Abrir sozinho de manhã:** o `--agendar 07:30` agora abre o app direto no briefing. Se o navegador bloquear o som sem um toque, aparece o botão "Toque para começar".

**Escuta contínua:** no painel da IA do Núcleo, clique em **Ligar escuta contínua**. O microfone fica atento, mas o app só reage quando você diz **"Núcleo"** (troque em `voz.palavra_ativacao`) ou **"bom dia"**. "Núcleo, como está o servidor?" é respondido direto. Depois de ativado, ele continua escutando por 40 segundos sem precisar da palavra de novo. Todo o áudio é processado no computador, e o que não tem a palavra de ativação é descartado na hora.

## Ações no computador

O Núcleo executa tarefas no seu PC por texto ou voz, sem teclado nem mouse. Ele chama ferramentas diretas do Windows, sem simular cliques e sem enviar capturas de tela para a nuvem. Exemplos:

- "abre o Excel", "abre a planilha orçamento licenças", "abre a pasta Downloads", "abre o site portal.pluro.com.br"
- "como está o computador?" (disco, memória, processador, placa de vídeo e tempo ligado)
- "pinga o servidor 10.0.0.5", "testa a porta 443 no fw01", "serviços parados", "status do serviço Spooler", "qual meu IP?"
- "verifica se tem atualizações", "instala todas as atualizações", "atualiza o Chrome", "abre o Windows Update"
- "organiza a pasta Downloads", "limpa os temporários"
- "escreve um e-mail para a Ana sobre a nota fiscal" (salva na pasta Rascunhos e nunca envia)
- "bloqueia o computador", "reinicia o computador", "cancelar desligamento"

**Segurança por nível de risco:**

- **Baixo** (abrir e consultar): executa na hora.
- **Médio** (organizar, limpar, rascunho): mostra o que vai fazer e espera confirmação, por clique ou dizendo "sim".
- **Alto** (instalar atualizações, reiniciar serviço, desligar): só com clique na tela, nunca por voz.

Arquivos executáveis nunca são abertos pela busca de arquivos, e a busca fica restrita às pastas de `acoes.pastas_busca`. Tudo fica registrado no histórico (botão **Ações**).

**Seus scripts de TI:** cadastre em `acoes.scripts` no config, com nome, descrição, risco e o comando em PowerShell. O exemplo `backup_servidor` mostra os últimos backups de uma pasta de rede; troque `SERVIDOR` pelo nome real. Depois é só dizer "roda o script backup_servidor". Parâmetros como host, porta e serviço são validados antes de entrar no comando.

**Atualizações automáticas:** o app verifica atualizações uma vez por dia (`verificar_atualizacoes_horas`) e mostra o resultado no Núcleo. Programas listados em `atualizar_automaticamente` (pelo ID do winget, por exemplo `"7zip.7zip"`) são atualizados sem perguntar, porque você já aprovou na configuração. As atualizações do Windows são instaladas pelo próprio Windows: o app avisa quando há atualizações, inclusive as de segurança, e abre a tela do Windows Update.

Reiniciar serviços e algumas atualizações exigem permissão de administrador. Se aparecer "acesso negado", abra o app com "Executar como administrador".

## Fontes da internet

Em **Fontes e envios**, você escolhe os sites e feeds RSS e o intervalo de cada um (de 1 hora a 1 semana). O app baixa as fontes em segundo plano, a IA local resume cada item e tudo é indexado localmente. As respostas citam a fonte e a data, e os itens com mais de 120 dias são descartados (`dias_artigos`).

A lista inicial (segurança, Microsoft 365, tecnologia, economia e marketing) é uma sugestão. Se alguma fonte mudar de endereço, ela aparece com erro na lista e pode ser removida ou trocada. Esse processo é só de leitura: nenhum dado seu sai do computador.

Para buscas que vão além das fontes, peça algo como "pesquise na internet o preço do Microsoft 365 Business". Nesse caso, a pesquisa é feita pelo Claude com busca na web: só o termo pesquisado sai do computador, e você confirma antes.

## Núcleo: o segundo cérebro (local primeiro)

Abra pelo menu ou com **Ctrl+K**. Exemplos do que ele resolve sem internet nem API:

- "anota: decidimos trocar o switch do 2º andar em dezembro" (classifica sozinho por tipo, projeto e pessoa)
- "me lembra de renovar o certificado do firewall amanhã às 9h"
- "lança conta de luz 230,50 dia 20 pessoal" e "paguei 89,90 do domínio da auralis"
- "quanto falta pagar?", "quanto gastei com licenças este mês?", "qual o saldo do mês?"
- "o que tenho amanhã?", "qual minha próxima reunião com a Equipe TI?"
- "minhas pendências"
- "prepara a reunião das 14h" (junta participantes, últimos e-mails, notas e o que está em aberto)
- "o que combinei com Ana sobre as licenças?" (busca nos seus e-mails e notas)

Tudo fica em `saida/memoria.db`, no seu computador. Os e-mails lidos nas atualizações entram nessa memória e são guardados por 365 dias (`dias_memoria_email`). Cada resposta mostra de onde veio. O mapa da memória liga pessoas e projetos. Para ajustar as palavras que identificam cada projeto, edite `cerebro.projetos` no config.

### Quando a API do Claude é usada

Só quando você clica em "Aprofundar com o Claude", "Perguntar ao Claude" ou "Pesquisar com o Claude". Com a IA local ativa, isso tende a ser raro. Antes de qualquer envio, o app:

1. separa só os trechos necessários (até 8, com no máximo 900 caracteres cada);
2. mascara CPF, CNPJ, cartões, telefones, e-mails, linhas digitáveis de boleto e senhas;
3. mostra o texto exato que vai sair e espera você clicar em "Enviar este texto";
4. registra o envio no "Histórico de envios ao Claude".

Os dados mascarados voltam ao normal só na resposta, dentro do app. Para desligar o envio de vez, use `"envio_no_nucleo": "nunca"` no config. O resumo da manhã também não usa a API, a não ser que você ligue `"resumo_automatico": true`.

### Configurar a chave da API (uma vez, quando quiser usar)

1. Acesse console.anthropic.com e entre ou crie sua conta.
2. Em Billing, adicione um cartão e um crédito inicial. A cobrança é por uso, separada da assinatura do Claude.
3. Em API Keys, clique em Create Key, dê o nome "Núcleo" e copie a chave, que começa com `sk-ant-`.
4. Com o app fechado, rode `python app.py --salvar-chave-claude` e cole a chave. Ela fica no cofre do sistema.

### Voz 100% local: ouvir e falar sem tokens

Toda a voz roda no seu computador. O reconhecimento do Chrome e do Edge não é usado, porque ele envia o áudio para a internet.

- **Ouvir: faster-whisper com o modelo large-v3-turbo**, na placa NVIDIA. Se a placa não puder ser usada, ele cai para o modelo `small` no processador. O app passa para o reconhecimento os nomes da sua memória (contatos, projetos e os termos de `voz.vocabulario`), para ele acertar nomes próprios.
- **Falar: Piper**, com vozes brasileiras abertas. A padrão é `faber`; troque por `cadu` ou `jeff` em `voz.voz_piper`, e ajuste `voz.velocidade` se quiser mais rápido ou mais devagar. Dinheiro, datas e horas são lidos por extenso ("3.487 reais e 90 centavos", "5 de novembro").

Há duas formas de falar com o Núcleo:

1. **Microfone:** clique, fale e clique de novo. A resposta aparece na tela, e o botão **Ouvir** lê em voz alta.
2. **Modo conversa (botão do fone):** fale à vontade, sem clicar. O app percebe quando você começa e para de falar, responde em voz com frases curtas e volta a escutar. Se você falar por cima, ele para e escuta. Para corrigir falando, diga "na verdade, …" ou "corrigindo, …". A correção vira aprendizado na hora.

Com caixas de som, o cancelamento de eco do navegador evita que ele escute a própria voz. Mesmo assim, um fone de ouvido deixa a conversa mais fluida.

**Placa de 8 GB:** a IA de conversa, o modelo de busca e o Whisper dividem a memória da placa. Se ficar lento, use `"dispositivo": "cpu"` em `voz` (o Whisper vai para o processador com o modelo `small`) ou troque o modelo de conversa por `qwen3:4b`. Com 12 GB ou mais, vale usar `qwen3:14b`.

Se o microfone não funcionar na janela própria, use `"janela": "navegador"` no config.

## Limites

- WhatsApp não tem acesso por IMAP; por isso há um lembrete fixo no resumo.
- Valores, datas e somas do financeiro e da agenda são sempre calculados por regras, nunca pela IA, para evitar números inventados. A IA local cuida da linguagem e das perguntas abertas.
- Um modelo local de 8B é muito bom para resumir e consultar a sua memória, mas erra mais que o Claude em raciocínios longos. Por isso o botão "Aprofundar com o Claude" continua disponível.
- No modo conversa, cada resposta leva de 1 a 3 segundos na placa de vídeo: transcrição, IA e voz rodam em sequência.
- As vozes Kokoro e Piper soam naturais, mas não no nível das vozes comerciais na nuvem. São as melhores opções abertas em português que rodam localmente. A Dora (Kokoro) é a única voz feminina aberta em português do Brasil com boa qualidade que encontrei.
- As ações funcionam no Windows 10 e 11. As consultas de sistema usam PowerShell, e as atualizações de programas usam o winget, que já vem no Windows 11.
- Dados de saúde, como no vídeo de referência, vêm do iPhone (Apple Saúde) e entram na fase do app para iPhone, via Atalhos.
- Com a escuta contínua ligada, o Whisper processa cada trecho de fala detectado. Em ambientes com muita conversa, isso ocupa a placa de vídeo com mais frequência.
- O atalho Ctrl+K funciona com o app em foco. Um atalho global do sistema não está incluído.
- O app só sabe que uma conta foi paga quando você marca como paga.
- As senhas ficam no cofre do sistema, nunca no config.json.
- O app só aceita conexões do próprio computador (127.0.0.1).
