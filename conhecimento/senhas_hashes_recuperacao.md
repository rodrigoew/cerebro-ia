# Senhas, hashes e recuperação autorizada

Consulta sobre password cracking em laboratório e recuperação de dados próprios. O Núcleo deve distinguir aprendizado, redefinição de acesso e tentativa de descobrir um segredo. Não possui uma capacidade universal de revelar senhas. Revisão: 20/11/2026.

## Hash, criptografia, salt e pepper
Hash de senha serve para verificar um candidato, não para decifrar um texto por uma chave. Salt individual evita que senhas iguais gerem registros idênticos sob a mesma função. Pepper é um segredo adicional mantido separado do banco. Uma função rápida de hash de arquivos não é, por si, uma escolha adequada para armazenar senhas. Para um novo sistema, consulte as recomendações atuais de Argon2id e os parâmetros da implementação escolhida.

## Recuperar acesso a contas ou arquivos próprios
Prefira o fluxo oficial de redefinição, códigos de recuperação e backups do gerenciador de senhas. Redefinir uma senha pode não recuperar dados criptografados com a chave anterior. Antes de qualquer tentativa em arquivo próprio, preserve uma cópia íntegra e confirme o formato. Não tente adivinhar o algoritmo somente pelo comprimento de uma string; o sistema de origem e os metadados são relevantes.

## Hashcat e John the Ripper em laboratório
São ferramentas de auditoria e recuperação de senhas, não fontes de autorização sobre os dados. Para aprender a reconhecer formatos, consulte os hashes de exemplo oficiais. `hashcat --example-hashes` e `hashcat --help` são consultas informativas quando a ferramenta já estiver instalada. Exemplos oficiais de treinamento devem ser mantidos separados de hashes reais e de arquivos pessoais. Não envie hashes reais ou senhas para serviços públicos de identificação.

## Estimar esforço e controlar recursos
O custo depende de função, parâmetros, hardware e espaço de candidatos; não existe prazo universal. Caracteres adicionais só ajudam quando aumentam a imprevisibilidade. Antes de uma auditoria offline autorizada, defina tempo máximo, temperatura, limites de recursos e critério de parada. A GPU usada pelo Núcleo para transcrever e revisar vídeos não deve ser ocupada automaticamente por tarefas de auditoria.

## Proteção de credenciais do próprio Núcleo
Tokens de Buffer e segredos do Cloudinary não são material de exercício. Preserve o cofre do sistema e evite valores em prompts, capturas, commits ou logs. Caso um segredo tenha sido divulgado, a medida relevante é revogar/rotacionar pelo serviço, e não tentar esconder o texto já exposto.

## Referências oficiais
OWASP Password Storage: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
Hashcat, exemplos de treinamento: https://hashcat.net/wiki/doku.php?id=example_hashes
