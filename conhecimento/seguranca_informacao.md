# Segurança da informação, hacking e a diferença para o crime

O usuário é da área de tecnologia e quer debater segurança. Trate como formação: conceitos, metodologia, as ferramentas e o que cada uma faz, defesa, carreira e a lei. Regras firmes para o Núcleo (o próprio Claude também recusa): não escrever malware, ransomware, exploit funcional ou phishing; não dar roteiro de ataque a sistema de terceiros; não ensinar a quebrar licença/DRM nem a pirataria; não ajudar a invadir conta, rede ou dispositivo de outra pessoa. Pode e deve: explicar como as coisas funcionam, apontar riscos, ensinar defesa, revisar a segurança de código do próprio usuário e orientar laboratório legal e carreira. A linha é simples: aprender e defender, sim; atacar alvo real sem autorização, não.

## Hacker x cracker (a cultura)
- Hacker, no sentido original, é quem entende um sistema a fundo e o explora com curiosidade; não é crime por si.
- "Chapéu branco" (white hat): segurança ofensiva com autorização (pentester, bug bounty). "Chapéu preto" (black hat) ou cracker: invade e causa dano de forma ilegal. "Chapéu cinza": age sem autorização mesmo sem querer causar dano, o que já é ilegal.
- "Cracker" também é usado para quem quebra proteção de software para pirataria. O Núcleo não ajuda nisso.
- A diferença entre o profissional e o criminoso é uma só: autorização por escrito do dono do sistema (escopo, contrato, regras de engajamento).

## A lei no Brasil (consultar sempre, porque muda)
- Lei 12.737/2012 (Carolina Dieckmann): criou o crime de invasão de dispositivo informático (art. 154-A do Código Penal).
- Lei 14.155/2021: endureceu as penas; a invasão de dispositivo passou a 1 a 4 anos de reclusão mais multa, e criou agravantes para furto e estelionato praticados por meio eletrônico.
- Marco Civil da Internet (Lei 12.965/2014) e LGPD (Lei 13.709/2018, dados pessoais): regem uso de dados e responsabilidades.
- Invadir conta, rede, celular ou computador de outra pessoa sem autorização é crime, ainda que "só para testar" ou "para mostrar a falha". Teste só o que é seu ou o que você foi contratado por escrito para testar.

## Fundamentos de segurança da informação
- Tríade CIA: Confidencialidade, Integridade e Disponibilidade. Mais autenticidade, não repúdio e privacidade.
- Defesa em profundidade (camadas), menor privilégio, confiança zero (zero trust), segregação de redes.
- Gestão de risco: identificar ativos, ameaças, vulnerabilidades, impacto e probabilidade; tratar, mitigar, transferir ou aceitar.
- Criptografia: simétrica (AES) e assimétrica (RSA, curvas elípticas), hash (SHA-256), assinatura digital, TLS/HTTPS, VPN. Senha nunca em texto puro: usar hash forte com sal (bcrypt, Argon2).
- Autenticação: senhas fortes, gerenciador de senhas, segundo fator (2FA/MFA), chaves de acesso (passkeys).

## Principais classes de vulnerabilidade (OWASP Top 10, para saber se defender)
- Injeção (SQL injection, comandos), quebra de controle de acesso, falhas de autenticação, exposição de dados sensíveis, XSS (scripts no navegador), CSRF, SSRF, configuração insegura, componentes desatualizados, desserialização insegura.
- Defesa: validar e tratar toda entrada, consultas parametrizadas, controle de acesso no servidor, atualizar dependências, cabeçalhos de segurança, revisão de código e testes.

## Metodologia de pentest (teste de intrusão autorizado)
1. Planejamento e autorização (escopo e contrato por escrito).
2. Reconhecimento (informações públicas, OSINT).
3. Varredura e enumeração (portas, serviços, versões).
4. Exploração (dentro do escopo).
5. Pós-exploração e avaliação de impacto.
6. Relatório com correções e reteste.
- Frameworks: PTES, OWASP Testing Guide, MITRE ATT&CK (táticas e técnicas de atacantes, usado também pela defesa).

## Ferramentas conhecidas (o que são; uso legítimo com autorização ou no próprio ambiente)
- Reconhecimento/varredura: Nmap (portas e serviços), Shodan (dispositivos expostos), theHarvester, Maltego (OSINT).
- Análise de rede: Wireshark (captura de pacotes), tcpdump.
- Aplicações web: Burp Suite e OWASP ZAP (proxy e testes), Nikto, sqlmap (testa injeção SQL).
- Exploração/plataforma: Metasploit (framework de exploração e estudo).
- Senhas (testar a força das suas, auditar, recuperar o que é seu): Hashcat e John the Ripper (quebra de hash), Hydra (força bruta em serviços).
- Wi-Fi (só na sua rede): suíte Aircrack-ng.
- Distribuições: Kali Linux e Parrot OS reúnem essas ferramentas para estudo.
- Para a defesa (blue team): SIEM (Wazuh, Splunk), IDS/IPS (Suricata, Snort), antivírus/EDR, firewalls, cofres de segredo, análise de vulnerabilidade (OpenVAS, Nessus).

## Como praticar de forma legal
- Laboratório próprio com máquinas virtuais isoladas; alvos feitos para treino: DVWA, OWASP Juice Shop, Metasploitable, VulnHub.
- Plataformas: Hack The Box, TryHackMe, PortSwigger Web Security Academy (gratuita), CTFs.
- Programas de bug bounty (HackerOne, Bugcrowd): pagam para você achar falhas, dentro das regras de cada empresa; é o caminho legal para "hackear" sistemas reais.

## Carreira e certificações
- Áreas: pentest/red team, defesa/blue team, resposta a incidentes, análise de malware, segurança de aplicações (AppSec), nuvem, governança (GRC).
- Certificações: CompTIA Security+ (base), CEH, OSCP (prática e reconhecida em ofensiva), certificações de nuvem e as da ISC2 (CISSP, para gestão).

## Higiene de segurança pessoal (vale para o usuário e a família)
- Gerenciador de senhas, 2FA em tudo que for importante, sistema e apps atualizados, backup (regra 3-2-1), cuidado com phishing (links e anexos), rede Wi-Fi com senha forte (WPA2/WPA3), reduzir exposição de dados nas redes sociais, atenção a golpes de Pix e falsas centrais de atendimento.
