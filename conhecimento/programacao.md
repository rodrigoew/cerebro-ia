# Desenvolvimento de software (várias linguagens)

O usuário é formado em Tecnologia. Quando ele pedir para "criar", "fazer" ou "montar" um projeto, use a ferramenta `criar_projeto` com o projeto completo e funcional; para mudar um projeto existente, `ver_projeto` primeiro. Nas respostas na tela, use blocos de código com a linguagem indicada.

## Estrutura mínima por linguagem (para criar_projeto)
- C# (.NET): `NomeDoProjeto.csproj` (Sdk="Microsoft.NET.Sdk", OutputType Exe, TargetFramework net8.0 ou superior) + `Program.cs` (top-level statements). Rodar: `dotnet run`. Web API: Sdk="Microsoft.NET.Sdk.Web", `app.MapGet(...)`. Testes: xUnit.
- Java: Maven (`pom.xml` com groupId, artifactId, maven.compiler.release 21; código em `src/main/java/pacote/App.java`; testes em `src/test/java`) ou Gradle. Rodar: `mvn -q compile exec:java` (com o plugin exec) ou `mvn package` e `java -jar`. Web: Spring Boot.
- Python: `main.py`, `requirements.txt` ou `pyproject.toml`, ambiente virtual (`python -m venv .venv`). Web: FastAPI/Flask. Testes: pytest.
- JavaScript/TypeScript (Node): `package.json` com scripts, `src/index.js` ou `index.ts` + `tsconfig.json`. Rodar: `npm install` e `npm start`. Front-end: Vite + React.
- Kotlin (Gradle), Go (`go.mod` + `main.go`, `go run .`), Rust (`Cargo.toml` + `src/main.rs`, `cargo run`), PHP (`composer.json`), SQL (scripts `.sql` com DDL e dados de exemplo).
- Sempre: README com pré-requisitos (ex.: .NET SDK, JDK 21, Python 3.11+, Node LTS) e comandos para rodar e testar; `.gitignore` adequado (bin/obj, target, node_modules, .venv).

## Boas práticas
- Código legível: nomes claros, funções pequenas, responsabilidade única (SOLID), tratamento de erros, sem segredos no código (variáveis de ambiente).
- Testes automatizados para o núcleo da lógica; versionamento com Git (commits pequenos e descritivos).
- Arquitetura: camadas (apresentação, aplicação, domínio, infraestrutura), injeção de dependência, APIs REST com status HTTP corretos, validação de entrada.
- Banco de dados: modelagem normalizada, índices nos campos de busca, migrações (EF Core, Flyway, Alembic), consultas parametrizadas (evita SQL injection).
- Segurança: OWASP Top 10 (injeção, autenticação quebrada, exposição de dados), hash de senha com bcrypt/Argon2, HTTPS.
- Performance: medir antes de otimizar; complexidade de algoritmos (O(n), O(n log n), O(n²)).

## Depuração (método)
1. Reproduzir o erro e ler a mensagem/stack trace inteira.
2. Isolar: menor caso que falha; conferir entradas e suposições.
3. Hipótese, teste, correção, teste de regressão.

## Ferramentas
- IDEs: Visual Studio / VS Code / Rider (C#), IntelliJ IDEA (Java/Kotlin), PyCharm/VS Code (Python).
- Docker para ambiente reproduzível; GitHub Actions para CI.
