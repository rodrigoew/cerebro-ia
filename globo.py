"""
Globo 3D ao vivo (God's Eye View), como uma ação do Núcleo.

O globo é um projeto de terceiros (MIT), em vendor/gods-eye-view, rodado em Node.
Fica no seu computador; usa só dados públicos (voos, navios, satélites, incêndios,
terremotos, clima, câmeras de trânsito). Não busca pessoas.

O Núcleo não embute o globo: ele inicia o servidor do globo em segundo plano e
abre a tela certa (lugar + camada) a partir do que você pede por texto ou voz.
A tela do Núcleo mostra o globo numa aba, dentro do próprio app.
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# camada do app -> termo que o usuário fala
CAMADAS = {
    "flights": ("voo", "voos", "aviao", "avioes", "aeronave", "aereo", "aviacao", "trafego aereo"),
    "military": ("militar", "militares", "caca", "forca aerea"),
    "vessels": ("navio", "navios", "barco", "barcos", "embarcacao", "maritimo", "porto"),
    "satellites": ("satelite", "satelites", "iss", "estacao espacial", "orbita"),
    "earthquakes": ("terremoto", "terremotos", "abalo", "sismo", "tremor"),
    "fires": ("incendio", "incendios", "fogo", "queimada", "queimadas"),
    "cameras": ("camera", "cameras", "cftv", "cctv", "transito ao vivo"),
    "weather": ("clima", "tempo", "chuva", "radar", "nuvem", "nuvens"),
    "wind": ("vento", "ventos"),
    "cyclones": ("ciclone", "furacao", "tempestade tropical"),
    "radio": ("radio", "radios", "estacao de radio"),
    "traffic": ("transito", "trafego", "congestionamento"),
    "launches": ("lancamento", "foguete", "foguetes", "missao espacial"),
    "datacenters": ("datacenter", "data center", "datacenters"),
    "cables": ("cabo submarino", "cabos submarinos"),
    "dams": ("barragem", "barragens", "represa"),
}
ESTILOS = {
    "nvg": ("visao noturna", "noturno", "night vision"),
    "flir": ("termica", "termico", "flir", "infravermelho"),
    "crt": ("retro", "crt"),
    "noir": ("noir", "preto e branco"),
}


class Globo:
    def __init__(self, app):
        self.app = app
        self._iniciado = False

    @property
    def cfg(self) -> dict:
        d = {"ativo": False, "pasta": "vendor/gods-eye-view", "url": "http://127.0.0.1:4173",
             "iniciar_junto": False}
        d.update(self.app.cfg.get("globo", {}))
        return d

    def _pasta(self) -> Path:
        from app import AQUI
        p = self.cfg["pasta"]
        return (AQUI / p) if not Path(p).is_absolute() else Path(p)

    def disponivel(self) -> bool:
        return self.cfg["ativo"] and (self._pasta() / "package.json").exists()

    def estado(self) -> dict:
        base = self.cfg["url"].rstrip("/")
        rodando = False
        try:
            urllib.request.urlopen(base, timeout=2)
            rodando = True
        except urllib.error.HTTPError:
            rodando = True
        except Exception:
            rodando = False
        return {"ativo": self.cfg["ativo"], "instalado": (self._pasta() / "node_modules").exists(),
                "pasta_existe": self._pasta().exists(), "rodando": rodando, "url": base}

    def iniciar(self, forcar: bool = False) -> str:
        if not (self.cfg["ativo"] and (self.cfg["iniciar_junto"] or forcar)):
            return "Globo desativado."
        if self.estado()["rodando"]:
            self._iniciado = True
            return "O globo já está no ar."
        pasta = self._pasta()
        if not (pasta / "package.json").exists():
            return "Globo não baixado. No terminal: git submodule update --init vendor/gods-eye-view"
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if not (pasta / "node_modules").exists() or not npm:
            return "Globo não instalado. Rode scripts\\instalar_globo.bat (precisa do Node.js 24)."
        porta = urllib.parse.urlparse(self.cfg["url"]).port or 4173
        env = {**__import__("os").environ, "HOST": "127.0.0.1", "PORT": str(porta)}
        log = open(self.app.saida / "globo.log", "a", encoding="utf-8")
        opcoes = {"creationflags": 0x08000000} if platform.system() == "Windows" else {}
        subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(porta)],
                         cwd=str(pasta), env=env, stdout=log, stderr=log, **opcoes)
        self._iniciado = True
        return "Abrindo o globo em segundo plano (demora alguns segundos na primeira vez)."

    # ------------------------------------------------------------ interpretar o pedido
    def interpretar(self, texto: str) -> dict:
        """Transforma o pedido em instruções para a tela do globo (lugar, camadas, estilo)."""
        from cerebro import sem_acento
        t = sem_acento(texto)
        camadas = [cod for cod, termos in CAMADAS.items() if any(re.search(rf"\b{re.escape(x)}", t) for x in termos)]
        estilo = next((cod for cod, termos in ESTILOS.items() if any(x in t for x in termos)), None)
        lugar, coords = self._lugar(texto, t)
        return {"lugar": lugar, "coords": coords, "camadas": camadas, "estilo": estilo}

    def _lugar(self, texto: str, t: str) -> tuple[str | None, dict | None]:
        if re.search(r"\b(aqui|minha (cidade|regiao)|perto de mim|por aqui)\b", t):
            local = (self.app.cfg.get("clima", {}).get("locais") or [None])[0]
            if local:
                return local.get("cidade"), {"lat": local["latitude"], "lon": local["longitude"]}
        m = re.search(r"\b(?:sobre|perto de|proximo de|pr[oó]ximo de|em|no|na|de)\s+(?:o |a |os |as )?"
                      r"([A-Za-zÀ-ÿ][\wÀ-ÿ'\-]*(?:\s+(?:de|do|da|dos|das|e)\s+[\wÀ-ÿ'\-]+|\s+[A-Za-zÀ-ÿ][\wÀ-ÿ'\-]+)*)", texto)
        if not m:
            return None, None
        cidade = re.sub(r"(?i)\s+(agora|hoje|em (tempo real|visao|vista)|ao vivo|por favor|pra mim|para mim)\b.*$", "", m.group(1)).strip(" ,.?!")
        if len(cidade) < 2:
            return None, None
        try:
            import briefing
            achadas = briefing.buscar_cidade(cidade)
        except Exception:
            achadas = []
        if achadas:
            a = next((x for x in achadas if x["pais"] in ("Brasil", "Brazil")), achadas[0])
            return a["cidade"], {"lat": a["latitude"], "lon": a["longitude"]}
        return cidade, None
