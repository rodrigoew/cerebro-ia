"""
Ícone na bandeja do Windows, atalho global e notificações.

  - Ícone perto do relógio com menu: Abrir, Falar com o assistente, Briefing, Sair.
  - Atalho global (padrão Ctrl+Alt+Espaço): chama o assistente de qualquer programa.
  - Notificações nativas do Windows para lembretes, compromissos, contas e riscos.
  - Fechar a janela só esconde o app na bandeja (ele continua lembrando você).

Tudo é opcional: sem as bibliotecas (pystray, pillow, pynput), o app funciona
normalmente e as notificações aparecem só dentro dele.
"""
from __future__ import annotations

import threading
import time


class Bandeja:
    def __init__(self, app, abrir, focar, sair):
        self.app = app
        self.abrir = abrir          # mostra a janela
        self.focar = focar          # mostra a janela e foca o assistente (js opcional)
        self.sair = sair
        self.icone = None
        self.atalho = None
        self.pendentes: list[dict] = []     # notificações também exibidas dentro do app
        self._trava = threading.Lock()

    # ------------------------------------------------------------ ícone
    def _imagem(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, 60, 60), outline=(217, 168, 69, 255), width=4)
        d.ellipse((18, 18, 46, 46), fill=(255, 207, 110, 255))
        return img

    def iniciar(self) -> str:
        msgs = []
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem("Abrir", lambda *_: self.abrir(), default=True),
                pystray.MenuItem("Falar com o assistente", lambda *_: self.focar("nucleo")),
                pystray.MenuItem("Briefing do dia", lambda *_: self.focar("briefing")),
                pystray.MenuItem("Sair", lambda *_: self._sair()))
            self.icone = pystray.Icon("nucleo", self._imagem(), "Núcleo", menu)
            self.icone.run_detached()
            msgs.append("ícone na bandeja ativo")
        except Exception as erro:
            msgs.append(f"bandeja indisponível ({erro.__class__.__name__})")
        combinacao = self.app.cfg.get("atalho_global", "<ctrl>+<alt>+<space>")
        if combinacao:
            try:
                from pynput import keyboard
                self.atalho = keyboard.GlobalHotKeys({combinacao: lambda: self.focar("nucleo")})
                self.atalho.daemon = True
                self.atalho.start()
                msgs.append(f"atalho global {combinacao}")
            except Exception as erro:
                msgs.append(f"atalho global indisponível ({erro.__class__.__name__})")
        return ", ".join(msgs)

    def _sair(self):
        try:
            if self.icone:
                self.icone.stop()
        finally:
            self.sair()

    # ------------------------------------------------------------ notificações
    def notificar(self, titulo: str, texto: str, nivel: str = "normal", tela: str = "") -> None:
        with self._trava:
            self.pendentes.append({"titulo": titulo, "texto": texto, "nivel": nivel, "tela": tela,
                                   "quando": time.time()})
            self.pendentes = self.pendentes[-20:]
        if self.icone is not None:
            try:
                self.icone.notify(texto[:250], titulo[:60])
            except Exception:
                pass

    def retirar(self) -> list[dict]:
        with self._trava:
            saida, self.pendentes = self.pendentes, []
        return saida
