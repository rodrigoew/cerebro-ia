"""
Vigia: o modo "sempre ativo" (widget), no Windows.

O que ele faz, em segundo plano e localmente:
  - Observa o TÍTULO da janela ativa (não lê o conteúdo, não grava a tela).
  - Quando vê um sinal de risco, avisa e dá uma dica: um site de compra numa
    hora em que você costuma gastar sem pensar, uma transferência bancária,
    um comando perigoso no terminal, uma configuração sensível.
  - Cruza com a sua situação (contas vencendo, saldo do mês) para o aviso ter
    contexto: "Você está numa página de compra e há 2 contas vencendo esta
    semana. Quer ver antes?".

Limites, por respeito à sua privacidade e às regras da plataforma:
  - Só títulos de janela, nunca o conteúdo digitado ou exibido.
  - Nada é enviado para fora. Tudo roda no seu computador.
  - Você liga e desliga quando quiser, e define os próprios gatilhos.
  - No macOS/Linux, a leitura de título depende de permissões; sem elas, o
    vigia fica inativo sem atrapalhar o resto.
"""
from __future__ import annotations

import platform
import re
import threading
import time

WINDOWS = platform.system() == "Windows"

GATILHOS_PADRAO = [
    {"id": "compra", "nivel": "atencao", "quando_gastando": True,
     "padrao": r"(checkout|carrinho|finalizar compra|pagamento|amazon|mercado ?livre|magazine|shopee|aliexpress|comprar agora)",
     "dica": "Você está numa página de compra. {financeiro} Vale a pena esperar 24 horas antes de decidir?"},
    {"id": "banco", "nivel": "atencao",
     "padrao": r"(transfer[êe]ncia|pix|ted|doc|internet banking|net empresa|pagar boleto|nova transa)",
     "dica": "Movimentação bancária à vista. Confira o valor e o destinatário com calma; golpes de Pix costumam ter pressa."},
    {"id": "terminal_perigoso", "nivel": "risco",
     "padrao": r"(rm -rf|format |del /s|drop database|diskpart|mkfs|shutdown /r|git push --force|rd /s)",
     "dica": "Comando potencialmente destrutivo no título da janela. Tem backup recente? Confirme o alvo antes de executar."},
    {"id": "config_sensivel", "nivel": "atencao",
     "padrao": r"(firewall|regras de entrada|usu[áa]rios e grupos|pol[íi]tica de grupo|registro do windows|regedit|"
               r"gerenciador de dispositivos|desinstalar programa|windows update)",
     "dica": "Você está mexendo numa configuração sensível do sistema. Crie um ponto de restauração antes, se puder."},
    {"id": "credencial", "nivel": "atencao",
     "padrao": r"(redefinir senha|recupera[çc][ãa]o de conta|autentica[çc][ãa]o em duas etapas|c[óo]digo de verifica)",
     "dica": "Troca de senha ou código de verificação. Confira se o site é mesmo o oficial antes de digitar."},
]


class Vigia:
    def __init__(self, app):
        self.app = app
        self.ligado = False
        self._thread = None
        self._parar = threading.Event()
        self._ultimo_titulo = ""
        self._avisado: dict[str, float] = {}

    @property
    def cfg(self) -> dict:
        return self.app.cfg.get("vigia", {})

    def gatilhos(self) -> list[dict]:
        extras = self.cfg.get("gatilhos", [])
        base = [g for g in GATILHOS_PADRAO if g["id"] not in self.cfg.get("desligados", [])]
        return base + extras

    def disponivel(self) -> tuple[bool, str]:
        if not WINDOWS:
            return False, "O widget sempre ativo observa janelas no Windows."
        try:
            import pygetwindow  # noqa: F401
            return True, ""
        except ImportError:
            return False, "Instale o suporte: pip install pygetwindow (ou rode o instalador)."

    # ------------------------------------------------------------ ligar/desligar
    def iniciar(self) -> str:
        ok, motivo = self.disponivel()
        if not ok:
            return motivo
        if self.ligado:
            return "O vigia já está ativo."
        self._parar.clear()
        self._thread = threading.Thread(target=self._rodar, daemon=True)
        self._thread.start()
        self.ligado = True
        return "Vigia ativo: observando apenas títulos de janela, neste computador."

    def parar(self) -> None:
        self._parar.set()
        self.ligado = False

    def estado(self) -> dict:
        ok, motivo = self.disponivel()
        return {"ligado": self.ligado, "disponivel": ok, "motivo": motivo,
                "janela": self._ultimo_titulo if self.cfg.get("mostrar_janela") else None,
                "gatilhos": len(self.gatilhos())}

    # ------------------------------------------------------------ laço
    def _titulo_ativo(self) -> str:
        try:
            import pygetwindow
            j = pygetwindow.getActiveWindow()
            return (getattr(j, "title", "") or "").strip()
        except Exception:
            return ""

    def _rodar(self) -> None:
        intervalo = max(2, int(self.cfg.get("intervalo_s", 4)))
        while not self._parar.wait(intervalo):
            titulo = self._titulo_ativo()
            if not titulo or titulo == self._ultimo_titulo:
                continue
            self._ultimo_titulo = titulo
            try:
                self._avaliar(titulo)
            except Exception:
                pass

    def _gastando_agora(self) -> bool:
        faixas = self.cfg.get("horas_de_impulso", [[22, 23], [0, 2]])
        h = self.app.agora().hour
        return any(ini <= h <= fim for ini, fim in faixas)

    def _contexto_financeiro(self) -> str:
        hoje = self.app.agora().date()
        urgentes = [t for _, t in self.app.contas_urgentes(hoje)]
        if urgentes:
            return f"Lembrete: há {len(urgentes)} conta(s) vencendo nos próximos dias."
        try:
            saldo = self.app.resumo_financeiro(hoje.strftime("%Y-%m"))["totais"]["saldo_previsto"]
            if saldo < 0:
                from app import formatar_reais
                return f"Atenção: o saldo previsto do mês está negativo em R$ {formatar_reais(saldo)}."
        except Exception:
            pass
        return "Dê uma olhada no seu financeiro antes."

    def _avaliar(self, titulo: str) -> None:
        t = titulo.lower()
        for g in self.gatilhos():
            if not re.search(g["padrao"], t, re.I):
                continue
            if g.get("quando_gastando") and not self._gastando_agora():
                continue
            if time.time() - self._avisado.get(g["id"], 0) < int(self.cfg.get("silencio_min", 20)) * 60:
                continue
            self._avisado[g["id"]] = time.time()
            dica = g["dica"].replace("{financeiro}", self._contexto_financeiro())
            self.app.notificar("Núcleo observou", dica, g.get("nivel", "atencao"), "nucleo")
            self.app.memoria.x(
                "INSERT INTO acoes_log(quando, ferramenta, parametros, risco, ok, resultado, origem) "
                "VALUES(?, 'vigia', '', ?, 1, ?, 'proativo')",
                (self.app.agora().isoformat(), g.get("nivel", "atencao"), dica[:300]))
            return
