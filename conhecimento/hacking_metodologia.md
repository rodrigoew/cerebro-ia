# Hacking ético, pentest e laboratórios CTF

Material de consulta sobre segurança ofensiva autorizada. Escopo, evidências, correção e reteste fazem parte do trabalho técnico. Não altera permissões nem executa ferramentas. Revisão: 20/11/2026.

## Planejar pentest, escopo e regras de engajamento
Defina ativo, proprietário, ambiente, contas de teste, prazo, técnicas permitidas, limites de tráfego, contato de emergência e condição de parada. Um domínio autorizado não libera automaticamente provedores, outras empresas ou todos os endereços ligados a ele. Registre o objetivo: demonstrar um risco com o mínimo de acesso necessário. Use dados fictícios e interrompa diante de instabilidade ou exposição inesperada de informações reais.

## Montar laboratório CTF isolado
Use uma VM descartável e uma rede interna/host-only, sem encaminhamento de portas para a internet. Crie snapshot antes dos exercícios. Separe a máquina de laboratório do computador que guarda tokens do Buffer, Cloudinary, contas Google e material pessoal. Use OWASP Juice Shop ou exercícios da PortSwigger Academy; a autorização do laboratório vale para seus desafios, não para sistemas encontrados fora dele. Instalações dependem de instrução específica e procedência oficial.

## Reconhecimento e enumeração no próprio ambiente
Comece pelo inventário e pela documentação. Diferencie equipamento, endereço, porta, serviço e versão. Uma porta aberta não comprova vulnerabilidade; uma versão aparente não comprova que determinado CVE seja explorável. Para estudar identificação de serviços no loopback de laboratório, o exemplo é `nmap -sV 127.0.0.1`, somente quando essa ferramenta já estiver instalada e o exercício estiver autorizado. Leia a saída antes de propor testes adicionais.

## Evidências, relatório e reteste
Para cada achado: ativo, condição inicial, comportamento esperado, comportamento observado, evidência mínima com dados mascarados, impacto demonstrado, limitações, correção proposta e resultado do reteste. Diferencie confirmado, hipótese e não testado. Scanner é uma fonte de pistas, não um veredito. Não invente CVE, severidade ou sucesso de exploração.

## Trilha de estudo e progresso
Ordem sugerida: redes e HTTP; Linux/Windows; programação e autenticação; laboratório web; leitura de logs; relatório; reteste. O Núcleo pode explicar resultados fornecidos e propor o próximo exercício. Conhecer uma técnica não autoriza executar ações automaticamente. Para um alvo real, verificar o escopo concreto da sessão.

## Referências oficiais
OWASP WSTG v4.2: https://wstg.owasp.org/v4.2/
Laboratório Juice Shop: https://owasp.org/projects/juice-shop
PortSwigger Academy: https://portswigger.net/web-security
