# Redes, Wi-Fi e diagnóstico de segurança

Consulta técnica para redes próprias e redes administradas com autorização. Wi-Fi, senhas e acesso devem ser tratados separadamente: ver um SSID não significa poder entrar na rede. Revisão: 20/11/2026.

## Fundamentos de redes TCP IP DNS e TLS
Separe as camadas do diagnóstico: associação ao Wi-Fi, endereço IP, gateway, resolução DNS e conexão ao serviço. Estar conectado ao rádio não garante internet. Falha de DNS não comprova invasão. TLS protege o transporte, mas não elimina falhas da aplicação ou golpes em páginas legítimas. Registre horário, sintoma e teste que o reproduz.

## Diagnóstico local Windows
Consultas locais úteis: `Get-NetIPConfiguration`, `Get-DnsClientServerAddress` e `Get-NetTCPConnection -State Listen`. São leituras; não mudam firewall nem revelam senhas. Para testar o acesso normal a um serviço seu, use `Test-NetConnection localhost -Port 8765`. Resultados devem ser interpretados com o endereço e o contexto corretos: um serviço em 127.0.0.1 não equivale a um serviço publicado na internet.

## Wi-Fi próprio: configuração e recuperação de acesso
Prefira WPA3-Personal quando os dispositivos forem compatíveis ou WPA2 com AES nos ambientes que exigirem compatibilidade. Use frase de acesso longa e exclusiva, firmware atualizado, senha administrativa diferente da senha Wi-Fi e rede de convidados separada. Evite WEP, TKIP e WPS quando desnecessário. Para recuperar o acesso à própria rede, comece pelo painel administrativo autorizado ou pelo procedimento oficial do fabricante. Reset do roteador interrompe a rede e exige reconfiguração; não é ação automática de diagnóstico.

## Wireshark e leitura de capturas autorizadas
Capture somente interfaces e tráfego dentro do escopo. Filtros de exibição para aprender: `dns`, `tls` e `tcp.analysis.retransmission`. Filtro de exibição não impede a coleta dos demais pacotes. Uma captura pode conter sessões, endereços e conteúdo privado; minimize e masque antes de compartilhar. Retransmissões são um sintoma que precisa de contexto, não prova isolada de ataque.

## Segmentar e reduzir exposição
Separe dispositivos de convidados e IoT dos ativos administrativos. Liste serviços necessários, restrinja interfaces de escuta e mantenha o acesso remoto por métodos administrativos previstos. Antes de mexer em firewall ou roteamento, registre a configuração atual e uma forma de reversão para evitar se bloquear.

## Referência oficial
Manual Wireshark: https://www.wireshark.org/docs/wsug_html_chunked/
