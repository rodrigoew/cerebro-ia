# Segurança do Núcleo

## O que já está no app

- **Só o seu computador, por padrão.** O servidor ouve em 127.0.0.1. O acesso pela rede é desligado e só liga quando você quer (para o celular e a sincronização).
- **Sessão por cookie httpOnly.** A credencial da interface não aparece no HTML nem fica ao alcance de scripts da página. A política de conteúdo (CSP) bloqueia scripts e conexões externas.
- **Proteção contra sites maliciosos (DNS rebinding).** O app só aceita pedidos cujo endereço de host seja localhost ou um IP privado da sua rede.
- **Anti-força bruta.** Dez tentativas de credencial erradas de um mesmo aparelho bloqueiam aquele aparelho por um minuto.
- **Senhas e chaves no cofre do sistema** (Gerenciador de Credenciais do Windows), nunca no config.json nem em texto.
- **Sincronização criptografada** (AES-GCM) com uma frase que só os seus aparelhos têm; o central valida por prova, sem receber a frase.
- **Ações com confirmação.** Nada é enviado, pago ou apagado sem o seu aval; ações de risco alto exigem clique, nunca voz.
- **Nuvem só com prévia.** Qualquer envio ao Claude ou a outro provedor mostra antes o texto exato, com CPF, cartões, telefones e e-mails mascarados, e fica no histórico.
- **Vigia que respeita a privacidade.** Observa só o título da janela, nunca o conteúdo, e nada sai do computador.

## O que você deve fazer

1. **Deixe o repositório do GitHub privado.** Em github.com/rodrigoew/cerebro-ia, vá em Settings, role até "Danger Zone" e use "Change repository visibility" para Private. O `.gitignore` já impede que dados pessoais, bancos de dados, senhas e a chave de licença entrem no Git, mas repositório privado é a proteção extra.
2. **Senha no computador.** A maior parte da proteção real vem do seu Windows ter uma senha de login e bloquear a tela quando você sai.
3. **Fora de casa, use Tailscale** em vez de abrir portas no roteador. Ele cria uma rede privada entre os seus aparelhos.
4. **Backup.** Copie de tempos em tempos a pasta de dados (`%APPDATA%\Nucleo`), onde ficam a memória e o financeiro.
5. **Antivírus.** Mantenha o Windows atualizado; o próprio Núcleo ajuda a verificar atualizações.

## Limites honestos

- O app confia em quem já está logado no computador. Ele não substitui a senha do sistema.
- A IA local pode errar. Confira valores, datas e decisões importantes.
- O acesso pela rede, mesmo protegido, é tão seguro quanto a sua rede. Em redes públicas, use Tailscale.
