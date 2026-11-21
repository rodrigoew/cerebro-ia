# Catálogo: dois temas e três canais

O mesmo Núcleo atende YouTube maromba, TikTok maromba e YouTube games. TikTok games continua desativado. Esta ampliação preserva credenciais, contas, horários, cotas e posts existentes. Cadastros futuros podem mudar como dados, sem nova versão Python.

## Ampliação

`catalogo_fontes.json` contém 13 cadastros e 19 consultas gerais em rodízio, além das palavras pessoais dos temas. Dez cadastros são monitores sem autorização presumida para baixar/publicar. Os assuntos incluem treino, nutrição, fisiculturismo, gameplay, GTA RP e esports.

| Fonte com escopo autorizado | Destinos | Restrição |
|---|---|---|
| `vacacast-rodrigo-goes-203` | YouTube/TikTok maromba | ID exato existente, histórico preservado |
| `vacacast-maromba-serie` | YouTube/TikTok maromba | Perfil oficial, série e palavra temática; mínimo 10 minutos; espera 48h |
| `gaules-cs-arquivo` | YouTube games | Dois IDs históricos específicos; não autoriza o canal inteiro |

Vaca Cast: https://www.vacacast.com.br/tenha-um-canal-de-cortes autoriza trechos próprios, exige contexto, títulos/capas próprios, créditos e espera de 48 horas. O novo cadastro confere `uploader_id: @evelynregly`, título da série e assunto nos metadados completos antes de baixar e novamente no sidecar antes de publicar. Não libera os vlogs da apresentadora. Exclui o episódio #203 já importado.

Gaules: as descrições oficiais de https://www.youtube.com/watch?v=cfaCODAGmmE e https://www.youtube.com/watch?v=uvXK_xE0aQc autorizam conteúdo das lives após 24h do encerramento da VOD. Os dois vídeos são de setembro/2023 e julho/2024. O encerramento da transmissão original é inferido dessa antiguidade; não foi consultado o horário exato no provedor da VOD. O cadastro também exige 48h desde a publicação no YouTube. Não se estende a novas lives, retransmissões de torneios ou outros criadores.

PodPeople não foi liberado: comunicado oficial revogou a permissão geral a partir de 01/01/2026: https://draanabeatriz.com.br/wp-content/uploads/2025/12/COMUNICADO-OFICIAL-PODPEOPLE.pdf . Listas de terceiros não comprovam consentimento.

Verificação das regras: 20/11/2026. O programa não detecta automaticamente mudanças futuras nas páginas dos titulares. Revogação/expiração cadastrada impede novos downloads e envios. Autorização de uso e revisão automática não garantem monetização nem aprovação pelas plataformas.

## Operação

O trabalhador relê o catálogo. Consulta até quatro fontes por volta e percorre as consultas do tema em rodízio, mantendo intervalos e cotas. Alterna tema/origem nos downloads elegíveis; um ID já importado não é baixado sob outro cadastro. Um título pode ser reformulado uma vez e precisa passar por nova avaliação do texto exato antes da capa/envio. Posts já agendados não são alterados.

Deixe Núcleo e computador ligados, com rede e IA local disponíveis. Não precisa rodar comandos a cada busca/corte. O pacote agora registra uma tarefa por usuário para iniciar o supervisor ao entrar no Windows, sem senha nem elevação. Não é um servidor externo.

Os novos cadastros precisam completar download, transcrição e revisão no ambiente real após aplicar. Os testes automatizados simulam transporte e publicação. O conjunto inicial de games é finito: novas origens precisam de autorização documentada, que pode ser cadastrada como dados. Agendado não significa publicado.

A limpeza local existente só age após todos os posts da fonte terem publicação confirmada. Cortes reprovados/pendentes podem reter arquivos; cotas interrompem downloads quando necessário. Nada existente é apagado por esta atualização; mídias remotas do Cloudinary continuam preservadas.

## Atualizar cadastros sem atualizar código

O padrão distribuído é `catalogo_fontes.json`. Um `fontes_online.json` pessoal antigo continua substituindo-o completamente, preservando pausas. Com `mesclar_catalogo: true`, o arquivo pessoal sobrepõe cadastros por ID e preserva os demais do catálogo distribuído. O objeto de uma fonte é substituído inteiro, sem herdar permissões inadvertidas.

Para consultar a configuração efetiva:

```powershell
python criador_cli.py catalogo
python criador_cli.py fontes
```

`fontes` mostra `cobertura_canais`: fontes autorizadas por destino ativo. Ainda são necessárias revisão, cotas e conexão antes de enviar.

Para importar um catálogo completo preparado/revisado, sem senhas:

```powershell
python criador_cli.py importar-catalogo --arquivo "C:\caminho\catalogo-novo.json"
python criador_cli.py importar-catalogo --arquivo "C:\caminho\catalogo-novo.json" --aplicar
```

O primeiro apenas valida e mostra prévia. O segundo grava atomicamente e cria backup se já existir arquivo pessoal. Dados inválidos não substituem a configuração. Não precisa reiniciar para importar dados; esses comandos são ferramentas para cadastros futuros, não rotina manual.

Uma fonte online autorizada precisa de `publicacao_catalogo: true` e `revisao_automatica: true` para aderir ao fluxo automático já ativado pelo operador. O `publicar` global e `publicacao_automatica.ativo` continuam podendo pausar. Fontes locais e vídeos sintéticos de teste não herdam esse opt-in. Para apenas monitorar, mantenha `direitos: "pendente"` e sem liberação automática.


## Rotina autônoma e início com o Windows

A rotina começa junto com o aplicativo, sem pedidos no chat. A cada 30 minutos verifica o estoque publicável dos três canais. Abaixo de dois posts por canal, antecipa buscas no máximo uma vez por hora. Vídeos sintéticos de teste e agendamentos vencidos não simulam estoque disponível. Os limites continuam valendo; o catálogo passa a permitir quatro tentativas de download por dia UTC, inclusive falhas, com teto local de 12 GB e reserva de disco de 5 GB. O plano aparece em `status.rotina`.

GTA VI foi confirmado como disponível em 19/11/2026 pela Rockstar: https://www.rockstargames.com/newswire/article/39akk424a9oo53/grand-theft-auto-vi-now-available . Até 20/12/2026, entram no rodízio dicas iniciais sem spoilers, mecânicas, exploração e primeiras impressões. Pautas têm início/fim no JSON e expiram sem nova versão. Recorrência de termos em pelo menos três canais distintos encontrados nas últimas 24h também pode gerar consultas. Isso é sinal editorial interno, não medição de volume de pesquisas ou audiência externa. Buscar GTA VI não concede autorização para copiar qualquer live ou material de outro canal.

O Núcleo notifica localmente problemas de conta, falta de fonte elegível e envios incertos, sem repetir o mesmo motivo mais de uma vez por dia. Não envia mensagens a terceiros, não inventa permissões e não repete uploads de estado incerto. Revisão, agenda, métricas e limpeza continuam no trabalhador existente.

O instalador registra `Nucleo-Criador-Autonomo-<id-da-pasta>` no Agendador de Tarefas, para o usuário atual. Inicia o supervisor agora e nos próximos logins. O supervisor verifica a cada 45 segundos se há um servidor Núcleo disponível; se não houver, abre o app com `pythonw`, sem janela. Não abre outra instância quando já encontra o servidor. Se o processo que ele iniciou sair, tenta novamente com pelo menos um minuto de intervalo, até três partidas por hora durante a execução desse supervisor. Não encerra processos de outros serviços, não mata um app que esteja apenas demorando para iniciar e não garante recuperação de qualquer travamento interno.

O Windows pode impedir o registro por política/permissão. Nesse caso o instalador informa falha: o código aplicado continua com backup e pode rodar ao abrir o Núcleo, mas não se deve considerar o autoinício instalado. O registro real da tarefa e o funcionamento após login precisam ser confirmados no computador do operador; os testes simulam o Agendador.

Consulta opcional (não é comando de rotina):

```powershell
python criador_cli.py autonomia
```

Para parar o autoinício/monitoramento, mantendo um app já aberto:

```powershell
python criador_cli.py autonomia --desativar
```

Para reativar:

```powershell
python criador_cli.py autonomia --ativar
```

`autonomia.json` é configuração pessoal ignorada pelo Git. O estado do supervisor fica em `saida/autonomia_estado.json` e no status do criador. O projeto unificado e o catálogo público continuam no mesmo repositório. Computador desligado, suspenso, sem login ou sem rede não produz novos vídeos; o Buffer pode publicar o que já foi agendado remotamente. Nenhuma rotina garante monetização.


## Acesso rápido compacto

O indicador flutuante ocupa 176 × 40 pixels em todos os estados. Mostra somente o estado do assistente, botão de conversa e botão de abrir a aplicação principal. Relógio, próximo compromisso, legendas e atalho de briefing saem do widget; essas funções continuam na aplicação. Texto longo/alertas não expandem a janela; o detalhe pode ser consultado na aplicação e na dica ao passar o mouse. Os temas/cores existentes são mantidos.

Não há canvas com animação contínua. O indicador consulta presença a cada segundo em vez de a cada 300 ms. A pulsação discreta de escuta respeita a preferência do sistema por movimento reduzido. O botão de abrir funciona com um clique; dois cliques na área de estado também abrem o Núcleo. Continua aparecendo ao minimizar a janela e desaparecendo ao restaurar. A rotina de produção de vídeos não depende dele estar visível.


## Ícone e identidade no Windows

O início do aplicativo define `Nucleo.SegundoCerebro` antes de criar interfaces e fornece `static/icone.ico` diretamente ao `webview.start`. O backend WinForms passa a usar esse ICO em vez de extrair o ícone de `pythonw.exe`. Foi removida a troca posterior por título/handles Win32, que era frágil e podia falhar silenciosamente. O arquivo ICO contém os tamanhos 16, 24, 32, 48, 64, 128 e 256 pixels.

A mudança aparece na próxima abertura do aplicativo. Um atalho antigo fixado para o próprio Python pode continuar com sua identidade/ícone e precisar ser removido e fixado novamente a partir do Núcleo aberto. A execução por código-fonte continua utilizando Python internamente, inclusive no Gerenciador de Tarefas; esta correção trata a apresentação da janela, não substitui o interpretador ou recompila o executável do projeto.
