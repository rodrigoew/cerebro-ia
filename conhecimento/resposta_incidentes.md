# Blue team, resposta a incidentes e proteção do ambiente Núcleo

Consulta sobre investigação, contenção e recuperação. Diferencie incidente confirmado de suspeita e priorize preservar evidências e a continuidade do serviço. Não executa bloqueios ou coleta de dados por conta própria. Revisão: 20/11/2026.

## Triagem e linha do tempo
Registre o que foi observado, horário e fuso, ativos envolvidos, origem do alerta e impacto conhecido. Reúna logs relevantes antes de conclusões. Um login falho isolado ou um processo desconhecido não comprova comprometimento. Compare com instalações, atualizações e tarefas esperadas, incluindo o supervisor do Núcleo.

## Contenção e preservação
Escolha uma medida proporcional e reversível. Isolar uma máquina pode interromper publicação, acesso remoto e sincronização; confirme o efeito operacional antes de aplicar. Evite apagar arquivos ou reiniciar um equipamento apenas para eliminar o sintoma. Preserve cópias e hashes quando houver necessidade de investigação e restrinja acesso às evidências.

## MITRE ATT&CK e hipóteses de detecção
ATT&CK organiza comportamentos de adversários observados e ajuda a relacionar hipóteses, fontes de telemetria, detecções e mitigações. Uma técnica citada em um alerta é uma classificação, não prova de intrusão. Para cada hipótese, descreva qual evento seria esperado, qual fonte o registra e que comportamento legítimo pode se parecer com ele. Não transforme uma matriz em checklist de invasão automática.

## Diferenciar processo esperado de processo suspeito
Documente executável, argumentos, diretório, usuário, porta e tarefa de inicialização esperados. No Núcleo em código-fonte, `pythonw.exe` pode ser legítimo; valide o caminho do script e o projeto antes de encerrar qualquer processo. Nome e ícone não bastam para confiar nem para acusar. Não encerre todos os processos Python para resolver um único serviço.

## Credenciais, recuperação e prevenção de recorrência
Quando houver evidência de exposição, revogue o segredo afetado no serviço e substitua-o no cofre; mantenha os demais separados. Confirme reconexão das contas e reteste os controles envolvidos. Backups devem ser verificáveis e a restauração deve ser exercitada. Após a recuperação, documente causa provável, incertezas, correção e monitoramento necessário.

## Prioridades para o computador dos canais
Proteja contas Google/TikTok/Buffer com os métodos fortes disponíveis, mantenha sistema e dependências atualizados e evite misturar laboratórios com produção. Preserve projetos e configurações em backup; credenciais permanecem fora do Git. Qualquer investigação deve respeitar os dados pessoais das outras aplicações do computador.

## Referência oficial
MITRE ATT&CK: https://attack.mitre.org/
