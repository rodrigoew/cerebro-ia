# Usar o Núcleo nos seus 4 aparelhos, com uma memória só

A ideia: um dos computadores é o **central** (o que fica mais ligado; no seu caso, o PC gamer). Ele guarda a memória principal e fica acessível na sua rede. O notebook sincroniza com ele; o tablet e o iPhone acessam pelo navegador.

## 1. PC gamer (central)

1. Instale o Núcleo e abra normalmente.
2. Em **Ajustes > Seus aparelhos**, ligue a sincronização, escolha **Central** e defina uma **frase secreta** (invente uma frase longa; ela será a mesma em todos).
3. Em **Ajustes > Acesso na rede**, ligue o acesso pela rede (isso faz o app aceitar os outros aparelhos). O app mostra o endereço, por exemplo `http://192.168.0.10:8765`.
4. Deixe o PC ligado quando quiser sincronizar ou usar pelo celular. Com o **vigia** ligado e o app na bandeja, ele já fica disponível.

Dica: no roteador, fixe o IP do PC (reserva de DHCP) para o endereço não mudar. Se mudar, o app mostra o novo em Ajustes.

## 2. Notebook gamer (secundário, com memória própria)

1. Instale o Núcleo.
2. Em **Ajustes > Seus aparelhos**, ligue a sincronização, escolha **Secundário**, cole o endereço do central e a **mesma frase secreta**.
3. Clique em **Sincronizar agora**. A partir daí, ele sincroniza sozinho de tempos em tempos e também funciona offline: o que você criar longe de casa entra na próxima sincronização.

Assim o notebook tem a mesma memória do PC, mesmo sem rede no momento.

## 3. Tablet Sony (Android) e iPhone 17 Pro Max

Eles acessam o central pelo navegador, como um aplicativo:

1. Com o central ligado e o acesso na rede ativado, abra no navegador do aparelho o endereço mostrado em Ajustes (`http://192.168.0.10:8765`).
2. **iPhone (Safari):** toque em Compartilhar e em "Adicionar à Tela de Início". **Android (Chrome):** menu e "Adicionar à tela inicial". Vira um ícone, abre em tela cheia e tem microfone e voz.

Observações do celular:
- Fora de casa, use uma rede privada (Tailscale) para alcançar o central com segurança, sem abrir portas para a internet. O LEIAME explica em um parágrafo.
- O iOS não deixa nenhum app observar o que você faz em outros apps. Então o "vigia" e a captura de ações existem só nos computadores. O celular entra com o que você digita, dita ou manda pelo atalho Compartilhar.
- Um app nativo na App Store é possível no futuro, mas exige um Mac, o Xcode e a conta de desenvolvedor da Apple. O PWA resolve hoje, sem isso.

## Como a memória não se perde

- Cada aparelho tem um relógio por tabela; a sincronização troca só o que mudou.
- Se o mesmo item for editado em dois lugares, vence a edição mais recente.
- Exclusões são combinadas entre os aparelhos, nunca somem de um lado sem o outro saber.
- Tudo é cifrado com a sua frase secreta. O central valida quem tem a mesma frase sem nunca recebê-la.
