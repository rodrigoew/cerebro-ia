# Privacidade (LGPD)

- **Onde ficam os dados:** no computador do usuário, em `%APPDATA%\Nucleo` na versão instalada ou na pasta do app na instalação manual. São eles a configuração, a memória (`memoria.db`), o financeiro (`financeiro.db`) e o histórico. As senhas e chaves ficam no cofre do Windows (Gerenciador de Credenciais).
- **O que o autor recebe:** nada. Não há telemetria, conta online nem servidor de ativação. A licença é verificada offline.
- **O que pode sair do computador, e quando:**
  - **E-mail:** a conexão com os seus provedores, para ler e salvar rascunhos.
  - **Agenda:** a leitura dos links de agenda que você cadastrar.
  - **Notícias:** o download das fontes que você escolher.
  - **Clima:** a consulta ao Open-Meteo, que recebe só as coordenadas ou o nome da cidade.
  - **IA na nuvem (opcional):** o envio de trechos ao provedor que você configurar, apenas depois de uma prévia e da sua confirmação, com dados sensíveis mascarados e registro no histórico.
- **Exclusão:** para apagar tudo, remova a pasta de dados e as credenciais "resumo-da-manha" no Gerenciador de Credenciais.
