"""
Ações locais do Núcleo: executa tarefas no computador sem teclado e mouse,
chamando ferramentas bem definidas (nada de simular cliques).

Níveis de risco:
  baixo  executa na hora (abrir programa, arquivo, site; consultas)
  medio  mostra o que vai fazer e pede confirmação (pode ser por voz)
  alto   só com clique na tela (instalar atualizações, reiniciar, desligar)

Scripts de TI vêm de uma lista aprovada (config "acoes.scripts"); parâmetros
são validados antes de qualquer execução. Toda ação fica no histórico.
"""
from __future__ import annotations

import datetime as dt
import email.message
import email.utils
import imaplib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import threading
import time
import unicodedata
import webbrowser
from pathlib import Path

WINDOWS = platform.system() == "Windows"
EXTENSOES_EXECUTAVEIS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi", ".scr", ".lnk", ".com", ".jar", ".reg"}
PS = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command"]

VALIDADORES = {
    "host": re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,252}$"),
    "servico": re.compile(r"^[A-Za-z0-9_.\- ]{1,80}$"),
    "porta": re.compile(r"^\d{1,5}$"),
    "texto": re.compile(r"^[\w\s.,:\-@/À-ÿ]{1,120}$"),
}

SCRIPTS_PADRAO = {
    "ping": {"descricao": "Testa se um servidor ou equipamento responde", "risco": "baixo",
             "parametros": {"alvo": "host"},
             "comando": "Test-Connection -TargetName {alvo} -Count 4 -ErrorAction Stop | "
                        "Select-Object Address, Status, Latency | Format-Table -AutoSize | Out-String -Width 160"},
    "porta": {"descricao": "Testa se uma porta está aberta em um servidor", "risco": "baixo",
              "parametros": {"alvo": "host", "porta": "porta"},
              "comando": "Test-NetConnection -ComputerName {alvo} -Port {porta} -WarningAction SilentlyContinue | "
                         "Select-Object ComputerName, RemotePort, TcpTestSucceeded | Format-List | Out-String"},
    "disco": {"descricao": "Mostra o espaço livre em cada disco", "risco": "baixo", "parametros": {},
              "comando": "Get-PSDrive -PSProvider FileSystem | Select-Object Name, "
                         "@{n='Usado (GB)';e={[math]::Round($_.Used/1GB,1)}}, @{n='Livre (GB)';e={[math]::Round($_.Free/1GB,1)}} | "
                         "Format-Table -AutoSize | Out-String"},
    "servicos_parados": {"descricao": "Lista serviços automáticos que estão parados", "risco": "baixo", "parametros": {},
                         "comando": "Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -ne 'Running'} | "
                                    "Select-Object Name, DisplayName, Status | Format-Table -AutoSize | Out-String -Width 160"},
    "status_servico": {"descricao": "Mostra o estado de um serviço do Windows", "risco": "baixo",
                       "parametros": {"nome": "servico"},
                       "comando": "Get-Service -Name {nome} -ErrorAction Stop | Select-Object Name, DisplayName, Status, StartType | "
                                  "Format-List | Out-String"},
    "rede": {"descricao": "Mostra IP, gateway e DNS das placas de rede", "risco": "baixo", "parametros": {},
             "comando": "Get-NetIPConfiguration | Select-Object InterfaceAlias, "
                        "@{n='IPv4';e={$_.IPv4Address.IPAddress}}, @{n='Gateway';e={$_.IPv4DefaultGateway.NextHop}}, "
                        "@{n='DNS';e={$_.DNSServer.ServerAddresses -join ', '}} | Format-List | Out-String"},
    "limpar_temporarios": {"descricao": "Apaga arquivos temporários do seu usuário", "risco": "medio", "parametros": {},
                           "comando": "$a=(Get-ChildItem $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue | "
                                      "Measure-Object Length -Sum).Sum; Remove-Item \"$env:TEMP\\*\" -Recurse -Force "
                                      "-ErrorAction SilentlyContinue; $d=(Get-ChildItem $env:TEMP -Recurse -Force "
                                      "-ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "
                                      "'Liberado: {0:N1} MB' -f (($a-$d)/1MB)"},
    "reiniciar_servico": {"descricao": "Reinicia um serviço do Windows (pode exigir administrador)", "risco": "alto",
                          "parametros": {"nome": "servico"},
                          "comando": "Restart-Service -Name {nome} -Force -ErrorAction Stop; "
                                     "Get-Service -Name {nome} | Select-Object Name, Status | Format-List | Out-String"},
}


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn").lower()


def _ps_literal(valor: str) -> str:
    return "'" + str(valor).replace("'", "''") + "'"


def _rodar(cmd: list[str], timeout: int = 90) -> tuple[bool, str]:
    try:
        opcoes = {"creationflags": 0x08000000} if WINDOWS else {}
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, **opcoes)
        saida = (r.stdout or b"") + (b"\n" + r.stderr if r.stderr else b"")
        texto = saida.decode("utf-8", errors="replace")
        if "\ufffd" in texto and WINDOWS:
            texto = saida.decode("cp850", errors="replace")
        texto = "\n".join(l.split("\r")[-1] for l in texto.splitlines())
        return r.returncode == 0, texto.strip()
    except subprocess.TimeoutExpired:
        return False, f"Tempo esgotado ({timeout} s)."
    except FileNotFoundError:
        return False, f"Comando não encontrado: {cmd[0]}"


# ================================================================ winget

def interpretar_winget(saida: str) -> list[dict]:
    """Lê a tabela do 'winget upgrade' (qualquer idioma) pelas posições das colunas."""
    linhas = [l.rstrip() for l in saida.splitlines()]
    for i, l in enumerate(linhas):
        if re.fullmatch(r"-{10,}", l.strip()) and i > 0:
            cab = linhas[i - 1]
            inicios = [m.start() for m in re.finditer(r"(?:(?<=\s)|^)\S", cab)]
            if len(inicios) < 4:
                continue
            pacotes = []
            for linha in linhas[i + 1:]:
                if len(linha) < inicios[2]:
                    continue
                cols = [linha[a:b].strip() for a, b in zip(inicios, inicios[1:] + [None])]
                nome, ident, versao, disponivel = cols[0], cols[1], cols[2], cols[3] if len(cols) > 3 else ""
                if not ident or " " in ident or "." not in ident or not disponivel:
                    continue
                pacotes.append({"nome": nome, "id": ident, "versao": versao, "disponivel": disponivel})
            return pacotes
    return []


# ================================================================ ferramentas

# Ações do próprio Núcleo (além das ações no computador). Todas perguntam até você dizer "sempre" ou "nunca".
ACOES_NUCLEO = {
    "evento": ("Adicionar compromissos à agenda", "baixo"),
    "lembrete": ("Criar lembretes", "baixo"),
    "lancamento": ("Lançar contas no Financeiro", "medio"),
    "nota": ("Fazer anotações", "baixo"),
    "memoria": ("Guardar fatos sobre você na memória", "baixo"),
    "guardar_itens": ("Guardar tarefas, ideias e decisões organizadas", "baixo"),
    "tarefa": ("Registrar como tarefa o que ainda não sei fazer sozinho", "baixo"),
    "rascunho_email": ("Salvar rascunhos de resposta de e-mail (nunca envia)", "medio"),
    "pagar": ("Marcar contas como pagas no Financeiro", "medio"),
    "concluir_lembrete": ("Marcar lembretes como concluídos", "baixo"),
}


class Acoes:
    def __init__(self, app):
        self.app = app
        cfg = app.cfg.get("acoes", {})
        self.cfg = cfg
        self.scripts = {**SCRIPTS_PADRAO, **cfg.get("scripts", {})}
        for nome in cfg.get("scripts_desligados", []):
            self.scripts.pop(nome, None)
        self.desligadas = set(cfg.get("ferramentas_desligadas", []))
        home = Path.home()
        self.pastas = [Path(os.path.expandvars(p)).expanduser() for p in cfg.get("pastas_busca", [])] or \
            [home / "Desktop", home / "Documents", home / "Downloads", home / "OneDrive"]
        self.planos: dict[str, dict] = {}
        self.tarefas: dict[str, dict] = {}
        self._apps_cache: tuple[float, list] = (0, [])
        self._trava = threading.Lock()
        mem = app.memoria
        with mem.trava, mem._con() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS acoes_log(
                id INTEGER PRIMARY KEY, quando TEXT, ferramenta TEXT, parametros TEXT, risco TEXT,
                ok INTEGER, resultado TEXT, origem TEXT)""")
            con.execute("""CREATE TABLE IF NOT EXISTS permissoes_acoes(
                ferramenta TEXT PRIMARY KEY, decisao TEXT NOT NULL, quando TEXT, vezes INTEGER DEFAULT 0)""")

    # ------------------------------------------------------------ catálogo
    def catalogo(self) -> list[dict]:
        base = [
            ("abrir_programa", "Abre um programa instalado pelo nome", "baixo", {"nome": "texto"}),
            ("abrir_arquivo", "Procura um arquivo pelo nome nas suas pastas e abre", "baixo", {"busca": "texto"}),
            ("abrir_pasta", "Abre uma pasta (Downloads, Documentos, Área de Trabalho ou caminho)", "baixo", {"pasta": "texto"}),
            ("abrir_site", "Abre um site no navegador", "baixo", {"endereco": "texto"}),
            ("info_sistema", "Mostra disco, memória, processador, placa de vídeo e tempo ligado", "baixo", {}),
            ("verificar_atualizacoes", "Lista atualizações de programas (winget) e do Windows", "baixo", {}),
            ("aplicar_atualizacoes", "Instala atualizações de programas pelo winget", "alto", {"ids": "lista ou 'todas'"}),
            ("abrir_windows_update", "Abre o Windows Update e pede uma nova verificação", "baixo", {}),
            ("organizar_downloads", "Organiza a pasta Downloads em subpastas por tipo", "medio", {}),
            ("rascunho_email", "Salva um rascunho de e-mail (nunca envia)", "medio",
             {"conta": "apelido", "para": "e-mail", "assunto": "texto", "corpo": "texto"}),
            ("bloquear_tela", "Bloqueia o computador", "baixo", {}),
            ("desligar", "Desliga ou reinicia o computador em 60 segundos", "alto", {"modo": "desligar|reiniciar"}),
            ("cancelar_desligamento", "Cancela um desligamento agendado", "baixo", {}),
        ]
        itens = [{"nome": n, "descricao": d, "risco": r, "parametros": p} for n, d, r, p in base if n not in self.desligadas]
        for nome, s in self.scripts.items():
            itens.append({"nome": f"script:{nome}", "descricao": s["descricao"], "risco": s.get("risco", "medio"),
                          "parametros": s.get("parametros", {})})
        return itens

    def risco_de(self, nome: str) -> str:
        return next((i["risco"] for i in self.catalogo() if i["nome"] == nome), "alto")

    # ------------------------------------------------------------ permissões por ação (com memória)
    def permissao(self, nome: str) -> str:
        """'sempre', 'nunca' ou 'perguntar' (padrão)."""
        linha = self.app.memoria.q("SELECT decisao FROM permissoes_acoes WHERE ferramenta = ?", (nome,))
        return linha[0]["decisao"] if linha else "perguntar"

    def definir_permissao(self, nome: str, decisao: str) -> None:
        if decisao not in ("sempre", "nunca", "perguntar"):
            raise ValueError("Decisão inválida.")
        if decisao == "perguntar":
            self.app.memoria.x("DELETE FROM permissoes_acoes WHERE ferramenta = ?", (nome,))
        else:
            self.app.memoria.x("""INSERT INTO permissoes_acoes(ferramenta, decisao, quando, vezes) VALUES(?,?,?,0)
                                  ON CONFLICT(ferramenta) DO UPDATE SET decisao = excluded.decisao,
                                  quando = excluded.quando""", (nome, decisao, self.app.agora().isoformat()))

    def _contar_uso(self, nome: str) -> None:
        self.app.memoria.x("UPDATE permissoes_acoes SET vezes = vezes + 1 WHERE ferramenta = ?", (nome,))

    def permissoes(self) -> list[dict]:
        memo = {l["ferramenta"]: l for l in self.app.memoria.q("SELECT * FROM permissoes_acoes")}
        saida = []
        for tipo, (descricao, risco) in ACOES_NUCLEO.items():
            l = memo.get(f"nucleo:{tipo}")
            saida.append({"nome": f"nucleo:{tipo}", "descricao": descricao, "risco": risco,
                          "decisao": l["decisao"] if l else "perguntar", "vezes": l["vezes"] if l else 0})
        for item in self.catalogo():
            l = memo.get(item["nome"])
            saida.append({"nome": item["nome"], "descricao": item["descricao"], "risco": item["risco"],
                          "decisao": l["decisao"] if l else "perguntar", "vezes": l["vezes"] if l else 0})
        return saida

    # ------------------------------------------------------------ planejar / executar
    def planejar(self, nome: str, parametros: dict, origem: str = "texto") -> dict:
        if not any(i["nome"] == nome for i in self.catalogo()):
            raise ValueError("Ação desconhecida ou desligada.")
        parametros = self._validar(nome, dict(parametros or {}))
        risco = self.risco_de(nome)
        descricao = self.descrever(nome, parametros)
        permissao = self.permissao(nome)
        # você já disse "nunca" para esta ação
        if permissao == "nunca":
            return {"tipo": "acao_resultado", "titulo": "Não vou fazer isso.", "ok": False, "local": True, "itens": [],
                    "linhas": [f"Você pediu para eu nunca {descricao['titulo'][0].lower()}{descricao['titulo'][1:]}. "
                               "Posso voltar a perguntar em Ajustes > Permissões."]}
        # você já autorizou sempre: faz direto (risco alto nunca entra aqui, por segurança)
        if permissao == "sempre" and risco != "alto":
            self._contar_uso(nome)
            r = self.executar_agora(nome, parametros, origem + " (autorizado)")
            r.setdefault("linhas", []).append("Feito automaticamente porque você autorizou esta ação. "
                                              "Para rever, vá em Ajustes > Permissões.")
            return r
        # risco baixo sem decisão: continua instantâneo (abrir programa, pasta, site…)
        if risco == "baixo" and permissao == "perguntar":
            return self.executar_agora(nome, parametros, origem)
        # primeira vez (ou você escolheu "perguntar"): pede permissão, com opção de lembrar
        token = secrets.token_urlsafe(10)
        self.planos[token] = {"nome": nome, "parametros": parametros, "risco": risco, "criado": time.time(),
                              "origem": origem}
        self._limpar_planos()
        pode_lembrar = risco != "alto"       # "sempre" não vale para risco alto
        linhas = list(descricao["linhas"])
        if risco == "alto":
            linhas.append("Esta é uma ação delicada: confirme com um clique, sempre.")
        return {"tipo": "confirmar", "titulo": descricao["titulo"], "linhas": linhas, "itens": [],
                "local": True, "risco": risco, "pergunta_permissao": True,
                "acao": {"tipo": "ferramenta", "rotulo": descricao.get("botao", "Executar"), "token": token,
                         "risco": risco, "ferramenta": nome, "pode_lembrar": pode_lembrar}}

    def ultimo_plano_por_voz(self) -> dict | None:
        self._limpar_planos()
        recentes = [(v["criado"], k, v) for k, v in self.planos.items() if time.time() - v["criado"] < 120]
        return max(recentes)[1:] if recentes else None

    def confirmar(self, token: str, por_voz: bool = False, lembrar: bool = False) -> dict:
        plano = self.planos.get(token)
        if not plano:
            raise ValueError("Essa confirmação expirou. Peça a ação de novo.")
        if por_voz and plano["risco"] == "alto":
            raise PermissionError("Ações de risco alto só podem ser confirmadas com um clique na tela.")
        self.planos.pop(token, None)
        if lembrar and plano["risco"] != "alto":
            self.definir_permissao(plano["nome"], "sempre")
        r = self.executar_agora(plano["nome"], plano["parametros"], plano["origem"] + (" (voz)" if por_voz else ""))
        if lembrar and plano["risco"] != "alto":
            r.setdefault("linhas", []).append("Combinado: não pergunto mais para esta ação.")
        return r

    def recusar(self, token: str, nunca: bool = False) -> dict:
        plano = self.planos.pop(token, None)
        if plano and nunca:
            self.definir_permissao(plano["nome"], "nunca")
            return {"tipo": "acao_resultado", "titulo": "Não vou fazer, e não pergunto mais.", "ok": True, "local": True,
                    "itens": [], "linhas": ["Pode reativar em Ajustes > Permissões."]}
        return {"tipo": "acao_resultado", "titulo": "Tudo bem, não fiz nada.", "ok": True, "local": True, "itens": [], "linhas": []}

    def executar_agora(self, nome: str, parametros: dict, origem: str) -> dict:
        if nome in ("aplicar_atualizacoes", "verificar_atualizacoes", "organizar_downloads") or \
                (nome.startswith("script:") and nome[7:] in ("limpar_temporarios",)):
            return self._em_segundo_plano(nome, parametros, origem)
        ok, titulo, linhas = self._executar(nome, parametros)
        self._registrar(nome, parametros, ok, titulo + "\n" + "\n".join(linhas), origem)
        return {"tipo": "acao_resultado", "titulo": titulo, "linhas": linhas, "itens": [], "local": True, "ok": ok}

    def _em_segundo_plano(self, nome: str, parametros: dict, origem: str) -> dict:
        id_ = secrets.token_urlsafe(8)
        self.tarefas[id_] = {"estado": "rodando", "titulo": self.descrever(nome, parametros)["titulo"], "linhas": [],
                             "inicio": time.time()}

        def rodar():
            try:
                ok, titulo, linhas = self._executar(nome, parametros, id_)
            except Exception as erro:
                ok, titulo, linhas = False, "A ação falhou.", [str(erro)]
            self.tarefas[id_].update({"estado": "concluida" if ok else "erro", "titulo": titulo, "linhas": linhas})
            self._registrar(nome, parametros, ok, titulo + "\n" + "\n".join(linhas), origem)
        threading.Thread(target=rodar, daemon=True).start()
        return {"tipo": "acao_resultado", "titulo": self.tarefas[id_]["titulo"], "linhas": ["Em andamento…"],
                "itens": [], "local": True, "tarefa": id_}

    def _registrar(self, nome, parametros, ok, resultado, origem):
        self.app.memoria.x("INSERT INTO acoes_log(quando, ferramenta, parametros, risco, ok, resultado, origem) "
                           "VALUES(?,?,?,?,?,?,?)",
                           (self.app.agora().isoformat(), nome, json.dumps(parametros, ensure_ascii=False),
                            self.risco_de(nome), 1 if ok else 0, resultado[:4000], origem))

    def _limpar_planos(self):
        for k in [k for k, v in self.planos.items() if time.time() - v["criado"] > 600]:
            self.planos.pop(k, None)

    # ------------------------------------------------------------ validação e descrição
    def _validar(self, nome: str, p: dict) -> dict:
        if nome.startswith("script:"):
            script = self.scripts[nome[7:]]
            limpos = {}
            for chave, tipo in script.get("parametros", {}).items():
                valor = str(p.get(chave, "")).strip()
                if not VALIDADORES.get(tipo, VALIDADORES["texto"]).fullmatch(valor):
                    raise ValueError(f"Valor inválido para “{chave}”: {valor or '(vazio)'}")
                limpos[chave] = valor
            return limpos
        if nome == "abrir_site":
            end = str(p.get("endereco", "")).strip()
            if not re.match(r"^https?://", end):
                end = "https://" + end
            if not re.fullmatch(r"https?://[\w.\-]+(:\d+)?(/[^\s]*)?", end):
                raise ValueError("Endereço inválido.")
            return {"endereco": end}
        if nome == "desligar":
            return {"modo": "reiniciar" if str(p.get("modo", "")).startswith("rein") else "desligar"}
        if nome == "aplicar_atualizacoes":
            ids = p.get("ids", "todas")
            if isinstance(ids, str) and ids != "todas":
                ids = [i.strip() for i in ids.split(",") if i.strip()]
            if ids != "todas":
                ids = [i for i in ids if re.fullmatch(r"[\w.\-+]{2,120}", i)]
                if not ids:
                    raise ValueError("Nenhum pacote válido informado.")
            return {"ids": ids}
        if nome == "rascunho_email":
            para = str(p.get("para", "")).strip()
            if para and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", para):
                raise ValueError("E-mail do destinatário inválido.")
            return {"conta": str(p.get("conta", "")), "para": para, "assunto": str(p.get("assunto", ""))[:200],
                    "corpo": str(p.get("corpo", ""))[:8000]}
        return {k: str(v)[:300] for k, v in p.items()}

    def descrever(self, nome: str, p: dict) -> dict:
        if nome.startswith("script:"):
            s = self.scripts[nome[7:]]
            extra = ", ".join(f"{k}: {v}" for k, v in p.items())
            return {"titulo": s["descricao"] + (f" ({extra})" if extra else ""),
                    "linhas": [f"Script aprovado “{nome[7:]}”. Risco {s.get('risco', 'medio')}."], "botao": "Executar"}
        textos = {
            "aplicar_atualizacoes": ("Instalar atualizações de programas",
                                     ["Pacotes: " + ("todos com atualização disponível" if p.get("ids") == "todas"
                                                     else ", ".join(p.get("ids", [])))
                                      , "Os programas podem fechar durante a atualização."], "Instalar atualizações"),
            "organizar_downloads": ("Organizar a pasta Downloads", self._previa_downloads(), "Organizar"),
            "rascunho_email": ("Salvar este rascunho de e-mail",
                               [f"Conta: {p.get('conta') or 'principal'}. Para: {p.get('para') or '(definir depois)'}",
                                f"Assunto: {p.get('assunto')}", p.get("corpo", "")[:600],
                                "Ele fica na pasta Rascunhos. Nada é enviado."], "Salvar rascunho"),
            "desligar": (f"{'Reiniciar' if p.get('modo') == 'reiniciar' else 'Desligar'} o computador em 60 segundos",
                         ["Salve o que estiver aberto. Para cancelar, diga “cancelar desligamento”."],
                         "Reiniciar" if p.get("modo") == "reiniciar" else "Desligar"),
            "verificar_atualizacoes": ("Verificando atualizações de programas e do Windows", [], ""),
        }
        if nome in textos:
            t, l, b = textos[nome]
            return {"titulo": t, "linhas": l, "botao": b}
        return {"titulo": nome.replace("_", " ").capitalize(), "linhas": [], "botao": "Executar"}

    # ------------------------------------------------------------ execução
    def _executar(self, nome: str, p: dict, tarefa: str | None = None) -> tuple[bool, str, list[str]]:
        if nome.startswith("script:"):
            return self._script(nome[7:], p)
        metodo = getattr(self, "_f_" + nome, None)
        if not metodo:
            return False, "Ação não implementada.", []
        return metodo(p, tarefa) if tarefa is not None else metodo(p)

    def _script(self, nome: str, p: dict):
        if not WINDOWS:
            return False, "Scripts de TI funcionam no Windows.", []
        s = self.scripts[nome]
        comando = s["comando"]
        for chave, valor in p.items():
            comando = comando.replace("{" + chave + "}", _ps_literal(valor))
        ok, saida = _rodar(PS + [comando], timeout=int(s.get("tempo_limite", 90)))
        linhas = [l for l in saida.splitlines() if l.strip()][:60]
        return ok, (s["descricao"] + (": concluído" if ok else ": falhou")), linhas or ["(sem saída)"]

    def _apps_iniciar(self) -> list[dict]:
        if time.time() - self._apps_cache[0] < 600:
            return self._apps_cache[1]
        ok, saida = _rodar(PS + ["Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"], 40)
        apps = []
        if ok:
            try:
                dados = json.loads(saida)
                apps = dados if isinstance(dados, list) else [dados]
            except json.JSONDecodeError:
                apps = []
        self._apps_cache = (time.time(), apps)
        return apps

    def _f_abrir_programa(self, p):
        nome = sem_acento(p.get("nome", "")).strip()
        apelidos = {"navegador": "edge", "explorador": "explorador de arquivos", "arquivos": "explorador de arquivos",
                    "calculadora": "calculadora", "terminal": "terminal", "configuracoes": "configuracoes"}
        apelidos.update({sem_acento(k): sem_acento(v) for k, v in self.cfg.get("apelidos_programas", {}).items()})
        nome = apelidos.get(nome, nome)
        if not nome:
            return False, "Qual programa abrir?", []
        if not WINDOWS:
            return False, "Abrir programas pelo nome funciona no Windows.", []
        apps = self._apps_iniciar()
        candidatos = []
        for a in apps:
            n = sem_acento(a.get("Name", ""))
            if n == nome:
                candidatos.insert(0, a)
            elif nome in n or all(t in n for t in nome.split()):
                candidatos.append(a)
        if not candidatos:
            return False, f"Não encontrei “{p.get('nome')}” entre os programas instalados.", []
        alvo = sorted(candidatos[:8], key=lambda a: (sem_acento(a["Name"]) != nome, len(a["Name"])))[0]
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{alvo['AppID']}"])
        return True, f"Abrindo {alvo['Name']}.", []

    TIPOS_ARQUIVO = {"planilha": {".xlsx", ".xls", ".csv", ".ods"}, "pdf": {".pdf"},
                     "documento": {".docx", ".doc", ".pdf", ".odt", ".txt"}, "apresentacao": {".pptx", ".ppt", ".odp", ".pdf"},
                     "contrato": {".pdf", ".docx", ".doc"}, "relatorio": {".pdf", ".docx", ".xlsx"}, "proposta": {".pdf", ".docx", ".pptx"}}

    def buscar_arquivos(self, busca: str, limite: int = 6, tipo: str = "") -> list[Path]:
        termos = [t for t in re.findall(r"[\w]+", sem_acento(busca)) if len(t) > 1 and t not in ("de", "do", "da", "o", "a")]
        if not termos:
            return []
        achados, vistos = [], 0
        for raiz in self.pastas:
            if not raiz.exists():
                continue
            for pasta, subpastas, arquivos in os.walk(raiz):
                subpastas[:] = [s for s in subpastas if not s.startswith((".", "$")) and s not in ("node_modules", "AppData")]
                if pasta.count(os.sep) - str(raiz).count(os.sep) > 5:
                    subpastas[:] = []
                for a in arquivos:
                    vistos += 1
                    n = sem_acento(a)
                    ext = Path(a).suffix.lower()
                    if all(t in n for t in termos) and ext not in EXTENSOES_EXECUTAVEIS and \
                            (not self.TIPOS_ARQUIVO.get(tipo) or ext in self.TIPOS_ARQUIVO[tipo]):
                        achados.append(Path(pasta) / a)
                if vistos > 60000:
                    break
        achados.sort(key=lambda c: c.stat().st_mtime if c.exists() else 0, reverse=True)
        return achados[:limite]

    def _abrir_caminho(self, caminho: Path):
        if WINDOWS:
            os.startfile(str(caminho))  # noqa: S606 (abre com o programa padrão)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(caminho)])
        else:
            subprocess.Popen(["xdg-open", str(caminho)])

    def _f_abrir_arquivo(self, p):
        caminho = p.get("caminho")
        if caminho:
            c = Path(caminho)
            if not any(str(c.resolve()).startswith(str(r.resolve())) for r in self.pastas if r.exists()):
                return False, "Esse arquivo está fora das pastas permitidas.", []
            if c.suffix.lower() in EXTENSOES_EXECUTAVEIS:
                return False, "Por segurança, não abro programas ou scripts por aqui.", []
            self._abrir_caminho(c)
            return True, f"Abrindo {c.name}.", []
        achados = self.buscar_arquivos(p.get("busca", ""), tipo=sem_acento(p.get("tipo", "")))
        if not achados and p.get("tipo"):
            achados = self.buscar_arquivos(p.get("busca", ""))
        if not achados:
            return False, f"Não encontrei arquivos com “{p.get('busca')}” nas suas pastas.", \
                [f"Procurei em: {', '.join(str(x) for x in self.pastas)}"]
        if len(achados) == 1:
            self._abrir_caminho(achados[0])
            return True, f"Abrindo {achados[0].name}.", [str(achados[0].parent)]
        self._abrir_caminho(achados[0])
        return True, f"Abrindo {achados[0].name} (o mais recente). Outros encontrados:", \
            [f"{a.name}  —  {a.parent}" for a in achados[1:]]

    def _f_abrir_pasta(self, p):
        nome = sem_acento(p.get("pasta", ""))
        home = Path.home()
        mapa = {"download": home / "Downloads", "document": home / "Documents", "area de trabalho": home / "Desktop",
                "desktop": home / "Desktop", "imagens": home / "Pictures", "onedrive": home / "OneDrive"}
        alvo = next((v for k, v in mapa.items() if k in nome), None)
        if alvo is None and nome:
            c = Path(os.path.expandvars(p.get("pasta", ""))).expanduser()
            alvo = c if c.is_dir() else None
        if not alvo or not alvo.exists():
            return False, "Não encontrei essa pasta.", []
        self._abrir_caminho(alvo)
        return True, f"Abrindo {alvo}.", []

    def _f_abrir_site(self, p):
        webbrowser.open(p["endereco"])
        return True, f"Abrindo {p['endereco']}.", []

    def _f_info_sistema(self, p):
        linhas = []
        for raiz in (["C:\\"] if WINDOWS else ["/"]) + [str(x) for x in self.cfg.get("discos_extras", [])]:
            try:
                u = shutil.disk_usage(raiz)
                linhas.append(f"Disco {raiz}: {u.free / 1e9:.0f} GB livres de {u.total / 1e9:.0f} GB "
                              f"({u.used * 100 / u.total:.0f}% usado)")
            except OSError:
                pass
        if WINDOWS:
            ok, saida = _rodar(PS + ["$o=Get-CimInstance Win32_OperatingSystem; $c=Get-CimInstance Win32_Processor | Select -First 1; "
                                     "'Memória: {0:N1} GB livres de {1:N1} GB' -f ($o.FreePhysicalMemory/1MB),($o.TotalVisibleMemorySize/1MB); "
                                     "'Processador: {0}% em uso ({1})' -f $c.LoadPercentage,$c.Name.Trim(); "
                                     "'Ligado há: {0:%d} dia(s) e {0:%h} hora(s)' -f ((Get-Date)-$o.LastBootUpTime)"], 40)
            if ok:
                linhas += [l for l in saida.splitlines() if l.strip()]
        if shutil.which("nvidia-smi"):
            ok, saida = _rodar(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                                "--format=csv,noheader,nounits"], 20)
            if ok and saida:
                n, usado, total, uso, temp = [x.strip() for x in saida.splitlines()[0].split(",")]
                linhas.append(f"Placa de vídeo: {n}, {usado}/{total} MB em uso, {uso}% de uso, {temp} °C")
        return True, "Situação do computador", linhas

    # atualizações
    def verificar_atualizacoes_sync(self) -> dict:
        resultado = {"programas": [], "windows": [], "erro": None, "quando": self.app.agora().isoformat()}
        if not WINDOWS:
            resultado["erro"] = "Verificação de atualizações disponível no Windows."
            return resultado
        if shutil.which("winget"):
            ok, saida = _rodar(["winget", "upgrade", "--include-unknown", "--accept-source-agreements",
                                "--disable-interactivity"], 180)
            resultado["programas"] = interpretar_winget(saida)
        else:
            resultado["erro"] = "winget não encontrado (instale o Instalador de Aplicativo pela Microsoft Store)."
        script = ("$s=New-Object -ComObject Microsoft.Update.Session; $r=$s.CreateUpdateSearcher().Search("
                  "'IsInstalled=0 and IsHidden=0'); @($r.Updates | ForEach-Object { [pscustomobject]@{titulo=$_.Title;"
                  "seguranca=[bool]($_.Categories | Where-Object { $_.Name -match 'Security|Segurança' });"
                  "mb=[math]::Round($_.MaxDownloadSize/1MB)} }) | ConvertTo-Json -Compress")
        ok, saida = _rodar(PS + [script], 300)
        if ok and saida.strip():
            try:
                dados = json.loads(saida)
                resultado["windows"] = dados if isinstance(dados, list) else [dados]
            except json.JSONDecodeError:
                pass
        self.app.aprendizado.gravar_estado("atualizacoes", json.dumps(resultado, ensure_ascii=False))
        return resultado

    def _f_verificar_atualizacoes(self, p, tarefa=None):
        r = self.verificar_atualizacoes_sync()
        if r["erro"] and not r["programas"]:
            return False, r["erro"], []
        linhas = [f"{x['nome']}: {x['versao']} → {x['disponivel']}  ({x['id']})" for x in r["programas"]]
        linhas += [f"Windows: {w['titulo']}" + (" (segurança)" if w.get("seguranca") else "") for w in r["windows"]]
        seg = sum(1 for w in r["windows"] if w.get("seguranca"))
        titulo = (f"{len(r['programas'])} programa(s) e {len(r['windows'])} atualização(ões) do Windows"
                  + (f", {seg} de segurança" if seg else ""))
        if not linhas:
            titulo = "Tudo atualizado."
        else:
            linhas.append("Para instalar, diga: “instalar todas as atualizações” ou “atualizar o <programa>”.")
        return True, titulo, linhas

    def _f_aplicar_atualizacoes(self, p, tarefa=None):
        if not WINDOWS or not shutil.which("winget"):
            return False, "O winget não está disponível neste computador.", []
        ids = p["ids"]
        if ids == "todas":
            ultima = json.loads(self.app.aprendizado.ler_estado("atualizacoes", "{}") or "{}")
            ids = [x["id"] for x in ultima.get("programas", [])] or None
        resultados, ok_total = [], True
        alvos = ids if ids else ["--all"]
        for i, ident in enumerate(alvos, 1):
            if tarefa:
                self.tarefas[tarefa]["linhas"] = [f"Atualizando {i} de {len(alvos)}: {ident}…"] + resultados[-8:]
            cmd = ["winget", "upgrade", "--silent", "--accept-source-agreements", "--accept-package-agreements",
                   "--disable-interactivity"] + (["--all", "--include-unknown"] if ident == "--all" else ["--id", ident, "-e"])
            ok, saida = _rodar(cmd, 1800)
            ok_total &= ok
            ultima_linha = next((l for l in reversed(saida.splitlines()) if l.strip()), "")
            resultados.append(f"{'OK' if ok else 'Falhou'}: {ident}  {ultima_linha[:120]}")
        self.app.aprendizado.gravar_estado("atualizacoes", json.dumps({"programas": [], "windows": [], "erro": None,
                                                                        "quando": self.app.agora().isoformat()}))
        return ok_total, ("Atualizações instaladas." if ok_total else "Algumas atualizações falharam."), resultados

    def _f_abrir_windows_update(self, p):
        if not WINDOWS:
            return False, "Disponível no Windows.", []
        subprocess.Popen(["explorer.exe", "ms-settings:windowsupdate"])
        _rodar(["UsoClient.exe", "StartInteractiveScan"], 20)
        return True, "Abrindo o Windows Update e pedindo uma nova verificação.", \
            ["A instalação de atualizações do Windows é feita pelo próprio Windows, com permissão de administrador."]

    # organizar downloads
    CATEGORIAS = {"Documentos": {".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".md"},
                  "Planilhas": {".xls", ".xlsx", ".csv", ".ods"}, "Apresentações": {".ppt", ".pptx", ".odp"},
                  "Imagens": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".svg", ".bmp"},
                  "Vídeos": {".mp4", ".mov", ".avi", ".mkv", ".webm"}, "Áudios": {".mp3", ".wav", ".m4a", ".ogg", ".opus"},
                  "Compactados": {".zip", ".rar", ".7z", ".tar", ".gz"},
                  "Instaladores": {".exe", ".msi", ".msix", ".iso"}}

    def _plano_downloads(self) -> list[tuple[Path, Path]]:
        pasta = Path(os.path.expandvars(self.cfg.get("pasta_downloads", ""))).expanduser() if self.cfg.get("pasta_downloads") \
            else Path.home() / "Downloads"
        movimentos = []
        if not pasta.exists():
            return movimentos
        for item in pasta.iterdir():
            if not item.is_file() or item.name.startswith(".") or item.suffix.lower() in (".crdownload", ".part", ".tmp"):
                continue
            categoria = next((c for c, exts in self.CATEGORIAS.items() if item.suffix.lower() in exts), "Outros")
            movimentos.append((item, pasta / categoria / item.name))
        return movimentos

    def _previa_downloads(self) -> list[str]:
        mov = self._plano_downloads()
        if not mov:
            return ["A pasta Downloads já está organizada."]
        contagem: dict[str, int] = {}
        for _, destino in mov:
            contagem[destino.parent.name] = contagem.get(destino.parent.name, 0) + 1
        return [f"{len(mov)} arquivo(s) serão movidos:"] + [f"{n} para {c}" for c, n in sorted(contagem.items())] + \
            ["Nada é apagado; arquivos com o mesmo nome ganham um número."]

    def _f_organizar_downloads(self, p, tarefa=None):
        movidos = 0
        for origem, destino in self._plano_downloads():
            destino.parent.mkdir(exist_ok=True)
            final, n = destino, 1
            while final.exists():
                final = destino.with_name(f"{destino.stem} ({n}){destino.suffix}")
                n += 1
            try:
                shutil.move(str(origem), str(final))
                movidos += 1
            except OSError:
                pass
        return True, f"Downloads organizada: {movidos} arquivo(s) movidos.", []

    # e-mail
    def _f_rascunho_email(self, p):
        contas = self.app.cfg.get("contas", [])
        conta = next((c for c in contas if sem_acento(c["apelido"]) == sem_acento(p.get("conta", ""))), None) \
            or (contas[0] if contas else None)
        if not conta:
            return False, "Nenhuma conta de e-mail configurada.", []
        msg = montar_rascunho(conta["usuario"], p.get("para", ""), p.get("assunto", ""), p.get("corpo", ""))
        import coletor as c
        m = c.conectar(conta)
        try:
            pasta = pasta_rascunhos(m)
            if not pasta:
                return False, "Não encontrei a pasta de rascunhos nessa conta.", []
            tipo, _ = m.append(f'"{pasta}"', "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), msg)
            if tipo != "OK":
                return False, "O servidor recusou o rascunho.", []
        finally:
            try:
                m.logout()
            except Exception:
                pass
        return True, f"Rascunho salvo em {conta['apelido']}, pasta {pasta}.", ["Revise e envie pelo seu e-mail quando quiser."]

    def _f_bloquear_tela(self, p):
        if not WINDOWS:
            return False, "Disponível no Windows.", []
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        return True, "Computador bloqueado.", []

    def _f_desligar(self, p):
        if not WINDOWS:
            return False, "Disponível no Windows.", []
        ok, saida = _rodar(["shutdown", "/r" if p["modo"] == "reiniciar" else "/s", "/t", "60"], 15)
        return ok, ("Reiniciando em 60 segundos." if p["modo"] == "reiniciar" else "Desligando em 60 segundos."), \
            ["Diga “cancelar desligamento” para impedir."]

    def _f_cancelar_desligamento(self, p):
        if not WINDOWS:
            return False, "Disponível no Windows.", []
        ok, _ = _rodar(["shutdown", "/a"], 15)
        return True, "Desligamento cancelado." if ok else "Não havia desligamento agendado.", []

    # ------------------------------------------------------------ rotina diária de atualizações
    def rotina_atualizacoes(self) -> None:
        ultima = json.loads(self.app.aprendizado.ler_estado("atualizacoes", "{}") or "{}")
        horas = int(self.cfg.get("verificar_atualizacoes_horas", 24))
        if ultima.get("quando"):
            try:
                if self.app.agora() - dt.datetime.fromisoformat(ultima["quando"]) < dt.timedelta(hours=horas):
                    return
            except ValueError:
                pass
        r = self.verificar_atualizacoes_sync()
        automaticos = set(self.cfg.get("atualizar_automaticamente", []))
        alvo = [x["id"] for x in r["programas"] if x["id"] in automaticos]
        if alvo:
            ok, titulo, linhas = self._f_aplicar_atualizacoes({"ids": alvo})
            self._registrar("aplicar_atualizacoes", {"ids": alvo}, ok, titulo + "\n" + "\n".join(linhas),
                            "rotina (atualização automática aprovada)")


def montar_rascunho(de: str, para: str, assunto: str, corpo: str) -> bytes:
    msg = email.message.EmailMessage()
    msg["From"] = de
    if para:
        msg["To"] = para
    msg["Subject"] = assunto or "(sem assunto)"
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid()
    msg.set_content(corpo or "")
    return msg.as_bytes()


def pasta_rascunhos(m: imaplib.IMAP4_SSL) -> str | None:
    tipo, linhas = m.list()
    candidatas = []
    for bruto in linhas or []:
        linha = bruto.decode(errors="replace") if isinstance(bruto, bytes) else str(bruto)
        achou = re.match(r'\((?P<f>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<n>.+)$', linha)
        if not achou:
            continue
        nome = achou.group("n").strip().strip('"')
        if "\\Drafts" in achou.group("f"):
            return nome
        if re.search(r"(draft|rascunho)", nome, re.I):
            candidatas.append(nome)
    return candidatas[0] if candidatas else None
