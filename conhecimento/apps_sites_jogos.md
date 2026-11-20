# Desenvolvimento de aplicativos, sites e jogos

Quando o usuário pedir um app, site ou jogo, crie o projeto completo com `criar_projeto` (estrutura, código, README com como rodar). Comece pela versão mais simples que funciona e ofereça os próximos passos. Pergunte só o essencial (plataforma e objetivo) se não estiver claro.

## Sites
- Página simples ou landing page: HTML + CSS + JavaScript puro, um `index.html`; abre direto no navegador. Hospedagem grátis: GitHub Pages, Netlify, Vercel, Cloudflare Pages.
- Site/app web moderno: Vite + React (ou Vue/Svelte) com TypeScript. `npm create vite@latest`, `npm install`, `npm run dev`.
- Site com páginas renderizadas no servidor, SEO e rotas de API: Next.js (React) ou Astro (conteúdo).
- Back-end/API: ASP.NET Core (C#), Spring Boot (Java), FastAPI (Python), Express/Fastify (Node). Banco: PostgreSQL, SQLite para começar, MongoDB se for documento.
- Autenticação: provedores prontos (Auth0, Clerk, Supabase Auth, Firebase Auth) ou ASP.NET Identity / Spring Security; nunca guardar senha em texto puro.
- Back-end pronto como serviço: Supabase (Postgres + auth + storage) e Firebase, ótimos para MVP.
- Boas práticas: responsivo (mobile first), acessibilidade (contraste, textos alternativos, navegação por teclado), desempenho (imagens otimizadas, carregamento sob demanda), HTTPS.

## Aplicativos móveis
- Flutter (Dart): um código para Android e iOS, interface rica; `flutter create app`, `flutter run`.
- React Native com Expo (JavaScript/TypeScript): ótimo para quem já conhece React; `npx create-expo-app`, testar no celular pelo app Expo Go.
- .NET MAUI (C#): Android, iOS, Windows e macOS com C#.
- Nativo: Kotlin + Jetpack Compose (Android), Swift + SwiftUI (iOS, exige Mac para compilar).
- Publicação: Google Play (taxa única de cadastro de desenvolvedor) e App Store (assinatura anual, exige Mac/Xcode). Política de privacidade obrigatória.
- PWA: site instalável como app, sem loja; bom para começar.

## Desktop
- WPF ou WinUI (C#, Windows), .NET MAUI, Electron ou Tauri (web no desktop), JavaFX, Python com PySide/Tkinter.

## Jogos
- Godot (GDScript ou C#): leve, gratuito e de código aberto; ótimo para 2D e bom para 3D. Estrutura: cenas (`.tscn`), scripts (`.gd`), `project.godot`.
- Unity (C#): o mais usado em jogos indie e mobile; 2D e 3D; loja de assets enorme. Scripts herdam de MonoBehaviour (`Start`, `Update`).
- Unreal Engine (C++ e Blueprints): gráficos de ponta, 3D AAA; mais pesado.
- Jogos web: Phaser (JavaScript, 2D), Three.js / Babylon.js (3D no navegador), ou canvas puro para jogos simples (cobrinha, pong, tetris) num único `index.html`.
- Python: Pygame para aprender e prototipar.
- Conceitos: loop de jogo (entrada → atualizar → desenhar), delta time, colisão (AABB, círculos), física, máquina de estados, sprites e animação, áudio, salvar progresso.
- Mod/servidores: Counter-Strike 2 usa a Source 2; mapas e modos podem ser feitos com as ferramentas oficiais (Workshop).

## Do zero ao lançamento
1. Ideia e escopo mínimo (o que é a versão 1).
2. Protótipo funcional (o Núcleo gera com `criar_projeto`).
3. Testes com usuários reais; ajustes.
4. Publicação (loja, hospedagem) e métricas.
5. Monetização: assinatura, compra única, anúncios, compras dentro do app.
