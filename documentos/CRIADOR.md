> Rotina autônoma: reposição de fila, pautas com prazo e supervisor ao entrar no Windows estão documentados em [CATALOGO_CRIADOR.md](CATALOGO_CRIADOR.md).

> Ampliação atual: consulte [CATALOGO_CRIADOR.md](CATALOGO_CRIADOR.md). O catálogo distribuído agora é `catalogo_fontes.json`, cobre os três canais e aceita até 100 fontes. Referências abaixo ao catálogo inicial descrevem o primeiro teste. Novos cadastros podem ser importados como dados.

# Núcleo: produção contínua para YouTube e TikTok

Esta atualização reaproveita o editor da 0.22.0 e acrescenta uma fila persistente,
descoberta de pautas, agendamento e leitura de resultados. Não cria contas, não
contrata serviços e não promete aprovação de monetização nem crescimento.

## Fluxo implementado

1. Lê pastas locais de vídeos próprios, licenciados ou autorizados, incluindo pastas
   sincronizadas automaticamente por um serviço que você já utiliza.
2. Observa títulos recentes nos feeds oficiais dos canais que você cadastrar.
   Isso é uma amostra editorial; não mede volume de busca do YouTube ou TikTok.
3. Prioriza fontes por correspondência de pauta, diversidade e retenção própria
   quando há pelo menos três posts maduros com essa métrica disponível.
4. Transcreve uma vez por arquivo, seleciona trechos com IA local quando disponível
   e usa seleção por regras como reserva. Valida os tempos indicados pela IA.
5. Gera MP4 vertical com legenda em perfis separados por canal.
6. Hospeda somente o corte final no Cloudinary e agenda no Buffer. Nunca hospeda
   o vídeo-fonte, conversas, e-mails ou banco de dados.
7. Consulta o Buffer para distinguir agendamento de publicação e obter métricas.
   Nem todas as plataformas/contas expõem as mesmas métricas; ausência não é zero.

O TikTok Direct Post não é usado: suas diretrizes não permitem um cliente privado
cuja única finalidade é publicar nas contas da própria equipe. Buffer oferece
um fluxo de agendamento automático. Conectar YouTube/TikTok nesse serviço é um
passo inicial necessário e a compatibilidade depende da conta e do plano.

## Preparação inicial

Use uma versão atual de Python compatível com os pacotes de voz do projeto.
Na pasta do Núcleo atualizado:

```powershell
python -m pip install -r requirements.txt
Copy-Item -LiteralPath criador.exemplo.json -Destination criador.json
python criador_cli.py diagnostico
```

Não substitua um `criador.json` já existente. O exemplo começa desativado e não
contém contas, fontes autorizadas ou credenciais. `config.json` pessoal é preservado.

Conecte as contas desejadas no Buffer, obtenha a chave de API e configure Cloudinary.
Não é necessário informar chaves na conversa ou salvá-las no JSON:

```powershell
python criador_cli.py segredo --nome buffer_token
python criador_cli.py segredo --nome cloudinary_cloud
python criador_cli.py segredo --nome cloudinary_key
python criador_cli.py segredo --nome cloudinary_secret
python criador_cli.py conexoes
```

Os valores são solicitados com entrada oculta e ficam no cofre do sistema.
Alternativa para implantação: variáveis NUCLEO_BUFFER_TOKEN,
NUCLEO_CLOUDINARY_CLOUD, NUCLEO_CLOUDINARY_KEY e NUCLEO_CLOUDINARY_SECRET.

Preencha `buffer_channel_id` no respectivo canal de `criador.json`. Cada conta deve
aparecer uma única vez. O código verifica se o canal conectado corresponde a YouTube
ou TikTok antes de enviar qualquer mídia ao agendador.

## Fontes e direitos

Uma entrada de fonte tem este formato (exemplo; preencha com dados reais):

```json
{
  "id": "originais-maromba",
  "tema": "maromba",
  "pasta": "C:/Videos/Autorizados/Maromba",
  "ativo": true,
  "direitos": "autorizado",
  "comprovante": "Caminho ou referência da autorização real",
  "credito": "Crédito e condições combinados com o criador",
  "formato_revisado": false,
  "publicar_automaticamente": false
}
```

As outras opções de `direitos` são `proprio` e `licenca_livre`. Os nomes dos famosos
nos temas não autorizam usar seus vídeos. Fontes locais continuam disponíveis.
O monitor online também pode baixar episódios de canais cadastrados, com escopo
de autorização explícito, usando `fontes_online.json` (veja abaixo). O catálogo
inicial observa canais e inclui um cadastro restrito ao episódio #203 do Vaca Cast,
baseado nas regras publicadas pelo próprio podcast. Isso não libera outros canais.

Um arquivo `video.mp4.json` ao lado de `video.mp4` pode informar `titulo` e `descricao`.
Sem ele, o nome do arquivo é usado como título da fonte. A fonte é deduplicada pelo
conteúdo, não apenas pelo nome. Aguarda dois minutos após a última alteração para
evitar ler arquivos que ainda estão sendo copiados.

O formato editorial precisa ser avaliado inicialmente. Após isso, marque
`formato_revisado` e `publicar_automaticamente` nessa fonte. Legendas, zoom e troca
de proporção não garantem originalidade ou monetização. A seleção semântica não é
uma revisão factual, médica ou de direitos autorais.

## Pautas e escala

### Descoberta e entrada automática de podcasts/lives

O trabalhador do aplicativo executa o monitor online junto da fila existente.
Não é preciso rodar comandos repetidamente: mantenha o Núcleo aberto e o PC ligado.
O monitor faz buscas por tema, além de acompanhar canais cadastrados. A aba de
Renato Cariani é apenas uma fonte inicial de metadados; não limita os criadores
que a busca pode encontrar. Não existe permissão de reutilização cadastrada para
esse canal no catálogo de exemplo.

Com `busca_por_tema: true` (padrão inclusive para configurações anteriores), examina
até três consultas por tema ativo a cada rodada. Maromba usa buscas gerais por
podcasts de musculação/fisiculturismo e entrevistas sobre treino, além de uma
palavra do tema em rodízio. Games usa lives, gameplay e streamers quando houver
um canal de games ativo. Novos temas usam seu nome mais podcast/entrevista.
Assim, novos criadores podem entrar na descoberta sem uma lista fixa de famosos.

São lidos até dez resultados por consulta, sem baixar os vídeos. O status inclui
`canais_encontrados` e os episódios descobertos. O programa registra o canal UC…
real do resultado e usa um identificador estável `achado-…`. Para autorizar uma
nova fonte, cadastre o canal e a permissão no arquivo pessoal abaixo. Uma fonte
já cadastrada é reconhecida pelo channel_id e tema e segue a fila existente;
uma fonte nova não recebe autorização só por aparecer na busca.

A busca é ordenada pela relevância retornada pelo YouTube e pelas palavras do
tema na fila. Resultados podem ser antigos ou de terceiros que republicaram um
episódio: encontrar um canal não comprova que ele é o titular. Não é uma medição
de tendências, volume de busca ou previsão de ganhos. Falhas de uma consulta
ficam no status e não impedem as outras consultas nem o monitor de canais.

Para cadastrar fontes reais, copie `fontes_online.exemplo.json` para
`fontes_online.json`, sem substituir um arquivo pessoal já existente. Esse arquivo
não vai para o Git. Os campos por fonte são:

| Campo | Preenchimento |
|---|---|
| `id` | Identificador único, letras minúsculas/números/hífen |
| `url` | Aba `/videos` ou `/streams` do canal no YouTube |
| `tema` | Tema já existente no criador.json, por exemplo maromba |
| `channel_id` | ID fixo UC… do canal abrangido pela permissão |
| `videos_permitidos` | Opcional: lista de IDs exatos para permissão restrita a episódios; não libera o canal inteiro |
| `aguardar_horas` | Prazo mínimo desde a publicação original; ausência de data bloqueia o download/envio |
| `creditos_obrigatorios` | Textos e links que devem permanecer na descrição enviada |
| `direitos` | `pendente` para observar; `proprio`, `autorizado` ou `licenca_livre` com base real para reutilizar |
| `comprovante` | Referência ao contrato, licença ou permissão e seu escopo; não invente autorização |
| `plataformas` | Lista de destinos abrangidos: youtube, tiktok ou ambos |
| `valido_ate` | Data/hora ISO com fuso, se houver término; vazio somente para permissão sem prazo |
| `credito` | Texto de crédito adicional exigido pelo titular |
| `formato_revisado` | true somente após revisar o formato editorial daquela fonte |
| `publicar_automaticamente` | Liberação de publicação daquela fonte; global publicar ainda precisa estar true |

A permissão deve abranger cortes e os episódios futuros monitorados. Para uma
campanha ou permissão limitada a determinados episódios, não libere o canal inteiro.
O cadastro é uma declaração do operador; o programa não autentica contratos.
Não presuma que um canal público, um canal de cortes existente ou um crédito no
vídeo autorizam a republicação. Regras da plataforma e condições do titular também
precisam permitir a obtenção e o uso pretendidos.

A cada seis horas são examinados até dez episódios recentes de cada aba cadastrada
(até 100 cadastros, quatro fontes por volta por padrão). Para lives, use `/streams`: o sistema aguarda a live acabar e
ser processada. Ordena candidatos por correspondência das palavras do tema,
evita repetir IDs e adiciona os títulos à análise editorial do Núcleo. Isso não
mede volume de buscas ou tendência global.

Somente fontes autorizadas entram no download. Confere o canal real, duração,
destinos permitidos e validade; baixa um vídeo por volta, até duas tentativas de
download por dia UTC (falhas também contam), três tentativas por episódio com espera.
Usa vídeo/áudio separados ou combinados até 720p, mantém o crédito e o link original e entrega o
arquivo concluído ao editor existente. Não usa cookies ou login do navegador.
Um bloqueio do YouTube fica registrado, sem tentativas de contornar o acesso.

Os limites existentes de tamanho/duração e espaço livre continuam valendo.
O cache de fontes online tem teto inicial de 12.000 MB, e a importação pausa com
16 cortes prontos ou a fila de fontes cheia. A limpeza pós-publicação dos vídeos
gerenciados é automática, conforme a seção abaixo. Arquivos pendentes ou com
problemas permanecem: espaço cheio pode exigir revisão antes de retomar downloads.
Não é um serviço de operação ilimitada sem supervisão.

Consultas opcionais, sem precisar repetir para a rotina funcionar:

```powershell
python criador_cli.py fontes
python criador_cli.py status
```

`fontes` mostra episódios encontrados, permissões pendentes e falhas de rede.
`buscar` executa uma volta de busca/importação sem editar nem publicar, respeitando
o intervalo e a trava: só funciona com o criador ativo e o app fechado.
O status também observa a trava do processo do app, corrigindo o falso
`trabalhador: false` que ocorria quando a consulta era feita por outro processo.

Para o primeiro caso real foi cadastrado o episódio com Rodrigo Goes (#203) do
Vaca Cast: https://www.youtube.com/watch?v=7MY_ZpLqIkw . A página do próprio podcast
https://www.vacacast.com.br/fake-natty-com-rodrigo-goes identifica esse episódio.
As condições estão em https://www.vacacast.com.br/tenha-um-canal-de-cortes .

O cadastro `vacacast-rodrigo-goes-203` fica em `regras_fontes.py` e no catálogo
padrão. Quando não existe `fontes_online.json` pessoal, já funciona após aplicar
a atualização e reiniciar o Núcleo. Se você já usa esse arquivo pessoal, ele é
preservado: a fonte só aparece quando incluída nele com suas regras.
O arquivo de exemplo atualizado contém o mesmo cadastro completo.

O sistema reconhece o ID exato desse vídeo e não precisa conceder permissão a todo
o canal da Evelyn Regly. Outros episódios devem ser avaliados antes de ampliar a
lista. O monitor encontra o episódio mesmo que ele não apareça entre os uploads
mais recentes. Confere o prazo de 48 horas pela data do YouTube (usando o horário
mais recente entre upload e estreia, se disponíveis). Só uma data diária é tratada
conservadoramente como fim daquele dia. Sem data confiável, não baixa.

O crédito inclui o episódio completo, canal oficial de cortes e perfil oficial do
Vaca Cast no Instagram. Esses links são conferidos antes da hospedagem/envio,
inclusive no rascunho real. Datas da origem ficam no sidecar e são reconferidas
antes do envio. O rascunho real conserva os créditos e não recebe a descrição de
história fictícia usada no teste sintético. A fonte usa `ia_sintetica: false` para
o material real, independentemente do padrão dos canais criado para o teste antigo.

As exigências de título, capa e descrição próprios, contexto fiel, respeito ao
convidado e revisão das regras atuais estão registradas para revisão editorial.
O programa não verifica automaticamente a veracidade do título nem se uma capa
cumpre a política do titular. Por isso `formato_revisado` e
`publicar_automaticamente` começam false; o global `publicar` pessoal permanece
inalterado (nesta configuração de teste, false). Download e edição podem ocorrer,
mas postagem automática depende da revisão inicial e liberação desses campos.

O teste de rascunho sintético já validou Buffer/Cloudinary. O primeiro corte real
ainda precisa ser gerado e revisado; o cadastro das regras não afirma que esse
teste foi concluído nem garante elegibilidade para monetização.

### Publicação com revisão automática

Para episódios longos, a transcrição agora lê janelas de 120 segundos com até dois
segundos adicionais de contexto de cada lado. O WAV completo fica apenas no disco
temporário; não é convertido inteiro em um array para o Whisper. Isso evita a
alocação gigante de recursos de áudio observada no primeiro podcast real. O modelo
é carregado uma vez, e os tempos das palavras são ajustados para a posição original
do episódio. A sobreposição é filtrada pelo ponto médio de cada palavra.
Ainda é necessário espaço temporário para o áudio PCM e memória para cada janela.

Após aplicar a correção, o próximo início do trabalhador recupera uma única vez
jobs com a falha conhecida `Unable to allocate`. Reutiliza o vídeo baixado, sem
zerar outras falhas ou reenviar posts já criados. A configuração de publicação,
contas e regras permanece como estava antes desta correção.

É possível optar por revisão automática por fonte, em vez de declarar uma revisão
manual que não ocorreu. A atualização de ativação ajusta `publicar: true` e:

```json
"publicacao_automatica": {
  "ativo": true,
  "fontes": ["online-vacacast-rodrigo-goes-203"]
}
```

O trecho acima é uma propriedade do JSON existente, não um comando PowerShell.
O cadastro da fonte também precisa permitir `revisao_automatica: true`.
Os campos de revisão manual não são marcados true pelo robô. O episódio #203 é
a fonte da lista legada; novos opt-ins online estão no catálogo de dados; a fonte sintética `teste-maromba` permanece
bloqueada para publicação e os demais canais descobertos não recebem permissão.

Antes de hospedar/enviar, o trabalhador confere direitos cadastrados, ID do
episódio, prazo de 48 horas, créditos, limites diários e conexão do canal. Usa a
IA local para avaliar o título proposto e a transcrição do corte: contexto claro,
fidelidade ao trecho, ausência de alegações inventadas e adequação à publicação.
Essa avaliação textual não comprova fatos externos nem substitui a interpretação
das condições do titular. As regras editoriais cadastradas são fornecidas ao
revisor; mudanças futuras da página de regras exigem atualizar o cadastro.

O FFmpeg decodifica vídeo e áudio, mede a duração e verifica o quadro vertical.
Uma faixa visual própria com o título é incorporada aos primeiros 2,5 segundos,
e uma capa PNG própria é salva ao lado. O Buffer envia o vídeo com essa abertura;
não há chamada de API para selecionar uma miniatura personalizada de Shorts.
Portanto, a plataforma ainda pode escolher outro quadro para a miniatura exibida.

Somente o corte aprovado segue para o agendamento. `reprovado_automatico` não
é publicado e não fica ocupando a contagem de posts prontos. Arquivos reprovados
permanecem locais para diagnóstico e podem exigir limpeza; não entram na limpeza
pós-publicação como se tivessem sido publicados. A IA indisponível ou uma resposta
JSON inválida deixam a revisão aguardando nova tentativa com espera progressiva,
sem solicitar aprovação manual a cada corte. A análise e os motivos aparecem em
`status.revisao_automatica`; decisões aprovadas são vinculadas à mídia/configuração.
Alterações na mídia ou na configuração invalidam a revisão anterior.

As regras e a pausa global são reconferidas após hospedar, antes de criar o post.
Uma resposta incerta do Buffer ainda fica em `verificar_envio` sem repetir o POST:
esse caso excepcional requer reconciliação para não duplicar publicações.
Agendado só vira publicado após confirmação do provedor; a limpeza de mídias
publicadas segue a política de 24 horas já configurada.

A publicação automática não equivale a aprovação de monetização: o produto atual
continua baseado em cortes, com revisão de texto e abertura visual própria. Isso
não comprova transformação criativa suficiente para os programas das plataformas.
Continuam existindo limites de armazenamento, gastos, disponibilidade e requisitos
de originalidade. Não é uma promessa de renda ou operação ilimitada sem supervisão.

O downloader passa a habilitar o Node.js instalado e aceitar áudio/vídeo separados,
mesclados pelo FFmpeg. A distribuição pip do yt-dlp usa `yt-dlp-ejs`, que precisa
ter a versão exigida pelo próprio pacote. O instalador de ativação verifica Node
22+ e instala somente esse componente oficial pelo pip, antes de alterar código
ou ativar a publicação. Se isso falhar, a ativação não é aplicada. As dependências
do Python podem ter sido parcialmente instaladas; o instalador não as desinstala.
Reinicie o aplicativo após atualizar. Erros conhecidos de formatos, JavaScript,
rede e acesso passam a ter diagnóstico sem expor URLs temporárias ou cookies.
Após corrigir EJS, erros antigos podem ter a espera antecipada uma única vez,
preservando as cotas diárias e o número de tentativas. Login/cookies do navegador
não são usados para superar restrições do YouTube.

Maromba e games já possuem perfis de exemplo. Em `temas[].feeds`, cadastre URLs no
formato `https://www.youtube.com/feeds/videos.xml?channel_id=ID_REAL_DO_CANAL`.
Os feeds são usados para observar assuntos, sem declarar que um tema é tendência
global. Novos temas exigem cadastro; não são criadas dezenas de contas sozinhas.

O exemplo agenda duas publicações por canal/dia, em horário de São Paulo, com teto
global de oito envios/dia e três dias de programação antecipada. Isso é uma hipótese
inicial de operação, não uma frequência garantida de crescimento. A adaptação muda
a prioridade de produção; não aumenta o teto de publicações ou gastos sozinha.

TikTok usa cortes de 65–90 segundos no exemplo; YouTube usa 25–60. Duração por si
só não torna cortes de terceiros elegíveis ao programa de recompensas.

Há limites de tamanho de fonte/corte, duração, espaço livre e hospedagem por dia.
Esses limites não equivalem a um teto financeiro em reais: configure limites e
alertas de cobrança também nos provedores. A seleção em segundo plano usa IA local;
não ativa provedores pagos do Núcleo sem você pedir.

## Ativar e acompanhar

### Limpeza pós-publicação e lembretes

Sem alterar sua configuração, a política padrão agora é limpar os vídeos locais
gerenciados **24 horas após a publicação confirmada de todos os cortes daquela
fonte**. Agendamento, hospedagem e rascunho não contam como publicação.
É necessário estado publicado, ID remoto e horário de publicação confirmado
pelo Buffer. O Núcleo precisa estar aberto para atualizar esse estado e limpar.

Remove apenas os MP4/arquivos de vídeo gerados nos perfis automáticos do editor
e os vídeos de origem baixados e registrados pelo monitor online. Nunca apaga
o original de uma pasta local fornecida por você. Confere o hash de cada mídia
e o caminho gerenciado antes de apagar, sem exclusão recursiva de diretórios.
Arquivos alterados, ocupados ou compartilhados com posts pendentes são preservados.
O histórico, os créditos, manifestos, legendas e metadados pequenos permanecem.
Arquivos hospedados no Cloudinary e publicações no YouTube/TikTok são preservados;
esta limpeza trata do disco local.

A publicação incompleta de qualquer corte mantém as mídias daquela fonte.
Uma mídia com erro de remoção gera pendência e lembrete no Núcleo; o trabalhador
pode tentar novamente nas próximas voltas. Os lembretes são deduplicados e
concluídos quando a limpeza correspondente é detectada.

Opcionalmente, adicione este objeto ao `criador.json` para apenas propor limpeza:

```json
"limpeza": {"modo": "propor", "reter_horas": 24}
```

Esse trecho é uma propriedade dentro do JSON existente, não um comando PowerShell.
Em `propor`, o Núcleo cria um lembrete e mostra os arquivos elegíveis, sem apagá-los.
Se você remover os arquivos manualmente, o sistema reconhece a limpeza e conclui
o lembrete. `modo: automatico` executa a exclusão após o prazo; `desativado` pausa
a limpeza. `reter_horas` permite ajustar o prazo, inclusive 0 para a próxima volta
após a confirmação. Pausar o criador também pausa a limpeza.

Para consultar o plano sem apagar nada:

```powershell
python criador_cli.py limpeza
```

O status do criador também inclui `limpeza`, com bytes liberados e pendências.

Comece com `ativo: true` e `publicar: false` para testar os arquivos. Depois da
configuração inicial das contas, fontes e formato, `publicar: true` habilita o fluxo
automático. O Núcleo precisa permanecer aberto e o computador ligado/conectado.
O programa ainda não foi validado como serviço do Windows sem usuário conectado.

Pergunte ao assistente "como está a fila de vídeos?" ou "analise os temas dos canais".
As ferramentas `estado_criador` e `analisar_temas` consultam o estado real.
Também existem consultas autenticadas `/api/criador` e `/api/criador/temas`.

```powershell
python criador_cli.py status
python criador_cli.py temas
```

Para pausar próximos envios, defina `publicar: false`. Isso não cancela posts já
agendados no Buffer: pause a fila também no serviço para interrompê-los.

Falhas de edição têm até três tentativas com espera crescente. Se houver queda
durante a criação de um post, a fila entra em `verificar_envio`; não repete o POST.
Confira no Buffer e associe o ID confirmado, sem criar outra publicação:

```powershell
python criador_cli.py reconciliar --post 12 --remoto-id ID_CONFIRMADO_NO_BUFFER
```

Erros definitivos ficam visíveis na fila; reconexão ou alteração de permissões pode
exigir intervenção. Arquivos e dados da fila não são apagados automaticamente.

## Documentação dos provedores consultada

- https://developers.buffer.com/examples/create-video-post.html
- https://developers.buffer.com/examples/create-scheduled-post.html
- https://developers.buffer.com/guides/hosting-media.html
- https://developers.buffer.com/reference.html
- https://cloudinary.com/documentation/django_image_and_video_upload
- https://developers.tiktok.com/docs/en/content-sharing-guidelines
- https://support.google.com/youtube/answer/1311392?hl=pt-BR

Integrações externas foram desenvolvidas contra a documentação; exigem validação
com suas contas antes da operação pública. Nenhum post foi enviado durante o desenvolvimento.
