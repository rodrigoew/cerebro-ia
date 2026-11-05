# Como vender o Núcleo para amigos

## 1. Uma vez só (preparação)

1. **Suas chaves de licença.** Rode `python ferramentas_vendedor/gerar_chaves.py`. Guarde a `chave_privada.pem` com backup e nunca a entregue a ninguém. Cole a linha `CHAVE_PUBLICA = "..."` que o script mostrar no arquivo `licenca.py`.
2. **Edição comercial.** No `config.exemplo.json`, defina `"edicao": "comercial"`. Assim, só as vozes Kokoro são usadas (veja TERCEIROS.md).
3. **Contas Microsoft dos compradores.** Registre um aplicativo gratuito no Entra ID:
   1. Acesse entra.microsoft.com, depois **Aplicativos**, **Registros de aplicativo** e **Novo registro**. Use o nome "Núcleo" e, em tipos de conta, escolha "contas em qualquer diretório organizacional e contas pessoais da Microsoft".
   2. Em **Autenticação**, adicione a plataforma **Aplicativos móveis e da área de trabalho**, marque o endereço `https://login.microsoftonline.com/common/oauth2/nativeclient` e ative **Permitir fluxos de cliente público**.
   3. Em **Permissões de API**, escolha **Adicionar**, depois **Microsoft Graph** e **Delegadas**, e marque `IMAP.AccessAsUser.All` e `offline_access`.
   4. Copie o **ID do aplicativo (cliente)** e coloque em `"microsoft": {"client_id": "..."}` no `config.exemplo.json`.
   5. Contas de empresas podem exigir a aprovação do administrador da empresa. Contas pessoais (Outlook e Hotmail) funcionam direto.
4. **Empacotar.** No Windows, rode `empacotar\empacotar.bat` e depois compile `empacotar\nucleo.iss` no Inno Setup. O resultado é `dist\Nucleo-1.0.0-instalador.exe`.

## 2. A cada venda

1. Rode `python ferramentas_vendedor/gerar_licenca.py "Nome" email@amigo.com` (ou acrescente uma validade: `2027-12-31`).
2. Envie ao comprador o instalador e o arquivo `licenca-email.json`.
3. Ele instala, segue os primeiros passos e cola a licença em **Ajustes**, na seção **Licença**. Ele tem 14 dias de avaliação antes de precisar da licença.

## 3. O que dizer ao comprador

- **Requisitos:**
  - Windows 10 ou 11 e cerca de 15 GB livres.
  - Placa NVIDIA com 8 GB ou mais, recomendada. Sem ela, o app funciona com modelos menores e mais lentos.
- **O que ele precisa ter:**
  - As próprias contas de e-mail. No Gmail, ele cria uma senha de app.
  - Para a nuvem (opcional), a própria chave de API. Nunca compartilhe a sua.
- **Privacidade:** nada passa por você (PRIVACIDADE.md).

## 4. Cuidados

- **Impostos e formalização:** a venda de licenças de software é uma atividade comercial. Confirme com um contador o enquadramento (MEI, CNAE e nota fiscal).
- **Suporte:** combine com o comprador o que está incluído, como atualizações e ajuda na instalação.
- **Atualizações:** gere um novo instalador. A licença continua valendo porque não depende da versão.
