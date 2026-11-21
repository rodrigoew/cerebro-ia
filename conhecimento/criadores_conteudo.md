# Ganhar dinheiro com canais e cortes (TikTok e YouTube) com o máximo de automação

Automatize edição, legenda, fila e agendamento depois da configuração inicial das contas, fontes e formato editorial.
Não prometa receita ou crescimento, nem diga que um vídeo foi publicado sem confirmação do provedor.
As regras de monetização mudam; consulte a documentação oficial antes de informar requisitos.

## Requisitos de monetização (conferir na plataforma)
- YouTube (Programa de Parcerias): consulte os requisitos atuais na Central de Ajuda e no YouTube Studio. Não trate números antigos deste pacote como regras vigentes. Fonte: https://support.google.com/youtube/answer/72851?hl=pt-BR
- YouTube reprime "conteúdo inautêntico"/repetitivo (vídeos em massa quase iguais, só IA sem valor agregado) e reutilizado sem transformação: isso derruba a monetização.
- TikTok: confirme elegibilidade e requisitos no programa disponível à conta. O Programa de Recompensas exige originalidade; prolongar um corte de terceiros não resolve esse requisito. Fonte: https://support.tiktok.com/pt_BR/business-and-creator/creator-rewards-program/creator-rewards-program

## Modelos de negócio
1. Cortes de outros criadores (podcasts, lives): só com autorização. Muitos criadores têm programa oficial de cortes com divisão de receita; sem permissão, há derrubada por direitos autorais (Content ID) e strike.
2. Canal "dark"/sem rosto: narração (voz própria ou IA), imagens de banco licenciadas, roteiros pesquisados. Nichos: curiosidades, histórias, finanças, tecnologia, futebol (sem usar imagens de jogos, que são protegidas).
3. Afiliados: link de produto (Amazon, Mercado Livre, Shopee, TikTok Shop) em vídeos de review/achadinhos.
4. Venda de serviço: oferecer cortes e edição para criadores (B2B), muitas vezes mais previsível que monetizar o próprio canal.
5. Produto próprio: e-book, curso, comunidade, depois que houver audiência.

## Esteira automatizada (exemplo)
1. Fonte: vídeo longo autorizado ou roteiro gerado e revisado.
2. Cortes automáticos com IA: ferramentas como OpusClip, Vizard, Klap (detectam momentos fortes, enquadram em vertical, legendam).
3. Edição/legenda: CapCut (legenda automática), templates próprios.
4. Voz: própria ou sintetizada (ElevenLabs e similares) — avisar quando o conteúdo é feito com IA, se a plataforma pedir.
5. Publicação agendada: Meta Business Suite, agendadores (Metricool, Later) ou o próprio agendamento das plataformas.
6. Métricas: retenção nos 3 primeiros segundos, tempo médio assistido, taxa de cliques da capa; dobrar o que funciona.

## Boas práticas
- Gancho forte nos primeiros 2-3 segundos, legenda grande, ritmo rápido, formato vertical 9:16 para Shorts/TikTok.
- Constância (1 a 3 vídeos por dia em vídeos curtos), testar títulos e capas.
- Evitar música e imagens sem licença; usar a biblioteca de áudio da plataforma.

## Ferramenta de cortes embutida
- O Núcleo tem a ação `criar_cortes`: a partir de um arquivo de vídeo (ou um link, se o yt-dlp estiver instalado), ele transcreve, acha os melhores trechos, recorta em vertical 9:16 com legenda embutida e salva em Documentos/Nucleo/Cortes. Ele não publica e não cria contas; entrega os arquivos prontos para você revisar e postar.
- Direito autoral é automático e independe de aviso na tela: baixar e republicar vídeo de terceiros para monetizar gera reivindicação (Content ID) e derruba o canal. Use a ferramenta com o que é seu, autorizado ou de licença livre.

## Esteira contínua de YouTube e TikTok

- O editor `cortes.py` continua responsável somente pelos arquivos. O coordenador `criador.py` pode agendar sua publicação via Buffer após configuração inicial; usa Cloudinary para hospedar somente os cortes finais.
- Consulte `estado_criador` para fila/erros e `analisar_temas` para sinais observados e desempenho próprio. Não confunda frequência em feeds com volume total de pesquisa.
- Os temas de exemplo são maromba e games. Fontes de celebridades precisam de autorização real: um nome na lista de temas não concede direitos.
- Arquivos originais entram por pastas locais cadastradas. Não há download automático de vídeos do YouTube pela esteira.
- Configuração e limitações: documentos/CRIADOR.md. Não afirme que contas foram conectadas ou que monetização foi aprovada sem confirmação.

## Como o Núcleo pode ajudar
- Montar roteiros, títulos e descrições; organizar calendário de postagem (lembretes/agenda); fazer contas de receita estimada com `calcular`; criar scripts de automação com `criar_projeto` (ex.: renomear, legendar ou cortar vídeos em lote com ffmpeg/Python).
