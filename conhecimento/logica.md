# Lógica, raciocínio e resolução de problemas

Para desafios de lógica, enigmas e contas: pense passo a passo, mostre o raciocínio de forma organizada na tela e confira o resultado. Para qualquer conta, use a ferramenta `calcular` em vez de calcular de cabeça.

## Método geral
1. Entender: o que é dado, o que se pede, quais as restrições.
2. Representar: tabela, diagrama, equação, árvore de casos.
3. Resolver por partes; testar casos pequenos; procurar padrões.
4. Conferir: a resposta satisfaz todas as condições? Existe outra solução?

## Lógica proposicional
- Conectivos: não (¬), e (∧), ou (∨), se...então (→), se e somente se (↔).
- "Se P então Q" só é falsa quando P é verdadeira e Q falsa. Equivalente à contrapositiva "se não Q então não P". Não equivale à recíproca "se Q então P".
- Leis de De Morgan: não (P e Q) = (não P) ou (não Q); não (P ou Q) = (não P) e (não Q).
- Negação de "todo A é B": "algum A não é B". Negação de "algum A é B": "nenhum A é B".
- Falácias comuns: afirmar o consequente, negar o antecedente, generalização apressada, falso dilema, ataque à pessoa, apelo à autoridade.

## Lógica de programação
- Sequência, decisão (if/else, switch), repetição (for, while), funções, recursão (caso base + passo recursivo).
- Estruturas de dados: listas, pilhas, filas, dicionários/mapas, conjuntos, árvores, grafos.
- Algoritmos clássicos: busca binária (lista ordenada, O(log n)), ordenações (merge sort, quick sort), BFS/DFS em grafos, programação dinâmica (subproblemas sobrepostos), algoritmos gulosos.

## Matemática para o dia a dia
- Porcentagem: aumento de x% = valor × (1 + x/100); desconto = valor × (1 − x/100). Aumentos sucessivos se multiplicam (10% + 10% = 21%).
- Juros compostos: M = C × (1 + i)^n. Regra prática dos 72: anos para dobrar ≈ 72 ÷ taxa anual (%).
- Regra de três, média ponderada, probabilidade (casos favoráveis ÷ casos possíveis; eventos independentes se multiplicam).

## Tipos de enigma
- Verdadeiros/mentirosos: montar a tabela de hipóteses e eliminar contradições.
- Grade de associação (quem mora onde, quem tem o quê): tabela cruzada com X e ✓.
- Sequências: diferenças entre termos, razões, padrões alternados, quadrados, Fibonacci.
- Pesagens e travessias: pensar no pior caso e no estado do problema a cada passo.
