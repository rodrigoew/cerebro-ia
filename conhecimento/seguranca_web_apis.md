# Segurança de aplicações web, APIs e revisão de código

Material de AppSec para projetos próprios, homologação e laboratórios. Foque em reproduzir, corrigir e testar regressões usando dados fictícios. Revisão: 20/11/2026.

## Autenticação, sessão e autorização de objetos
Autenticação identifica a pessoa; autorização determina o que ela pode fazer. A autorização deve ocorrer no servidor a cada operação relevante. Em homologação, crie usuários fictícios A e B e objetos separados. Verifique se A só consulta, altera e remove o que a regra de negócio permite. Esconder um botão ou usar IDs difíceis de adivinhar não substitui esse controle. Teste também acesso entre organizações e funções administrativas, sempre no ambiente autorizado.

## SQL injection, XSS e tratamento de entrada
Para SQL, use consultas parametrizadas e permissões mínimas da conta de banco; concatenar entrada em uma consulta é uma indicação de risco. Para conteúdo HTML, escolha a codificação adequada ao contexto e evite inserir entrada diretamente em APIs perigosas do DOM. Uma validação de formato não substitui parametrização ou escape contextual. O reteste deve verificar o caso corrigido e o fluxo legítimo que precisa continuar funcionando.

## Tokens, cookies, segredos e CORS
Não registre tokens completos em logs. Separe credenciais de desenvolvimento e produção, armazene-as em cofre e planeje rotação quando houver exposição. Avalie expiração, invalidação de sessão e atributos de cookies conforme o tipo de aplicação. CORS é um controle do navegador; não é autenticação nem bloqueio de clientes que fazem requisições diretamente.

## SSRF, integrações e serviços internos
Quando a aplicação busca uma URL indicada pelo usuário, examine protocolos permitidos, resolução de nomes, redirecionamentos e destino efetivo. Testes devem usar endpoints controlados pelo laboratório. Bloquear apenas uma string de localhost é insuficiente como defesa geral. Combine validação do destino com restrições de saída do serviço e evite enviar credenciais internas a destinos não aprovados.

## Revisão prática do próprio repositório
Inventarie endpoints, dependências, pontos de entrada, controles de acesso e armazenamento de segredos. Para cada mudança, relacione risco, código afetado, correção e um teste que diferencie o comportamento vulnerável do corrigido. Evite testes que apenas repitam a implementação. Não marque como seguro algo que não foi examinado.

## Referências oficiais
Guia OWASP WSTG v4.2: https://wstg.owasp.org/v4.2/
Exercícios e explicações por vulnerabilidade: https://portswigger.net/web-security
