"""Inicialização por usuário e supervisor local, sem senhas ou privilégios de administrador."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import uuid


def gravar(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temp = caminho.with_name(caminho.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(caminho)
    finally:
        temp.unlink(missing_ok=True)


def nome_tarefa(raiz):
    return "Nucleo-Criador-Autonomo-" + hashlib.sha256(str(Path(raiz).resolve()).casefold().encode()).hexdigest()[:10]


def literal_ps(texto):
    return "'" + str(texto).replace("'", "''") + "'"


def comando_registro(raiz, python):
    raiz = Path(raiz).resolve()
    argumentos = subprocess.list2cmdline([str(raiz/"iniciar_nucleo_autonomo.py"), "--pasta", str(raiz)])
    return f"""$ErrorActionPreference = 'Stop'
$usuarioNucleo = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$acaoNucleo = New-ScheduledTaskAction -Execute {literal_ps(python)} -Argument {literal_ps(argumentos)} -WorkingDirectory {literal_ps(raiz)}
$gatilhoNucleo = New-ScheduledTaskTrigger -AtLogOn -User $usuarioNucleo
$principalNucleo = New-ScheduledTaskPrincipal -UserId $usuarioNucleo -LogonType Interactive -RunLevel Limited
$opcoesNucleo = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName {literal_ps(nome_tarefa(raiz))} -Action $acaoNucleo -Trigger $gatilhoNucleo -Principal $principalNucleo -Settings $opcoesNucleo -Force | Out-Null
"""


def executar_ps(script, executor=subprocess.run):
    if os.name != "nt":
        raise RuntimeError("Inicialização automática disponível somente no Windows.")
    r = executor(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                  base64.b64encode(script.encode("utf-16le")).decode("ascii")],
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if r.returncode:
        raise RuntimeError("O Windows recusou o registro/alteração da tarefa automática. Código " + str(r.returncode))


def registrar(raiz, executor=subprocess.run):
    raiz = Path(raiz).resolve()
    if not (raiz/"app.py").is_file() or not (raiz/"iniciar_nucleo_autonomo.py").is_file():
        raise ValueError("Projeto/supervisor não encontrado.")
    if getattr(sys, "frozen", False):
        raise RuntimeError("Execute o cadastro pelo Python do projeto.")
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise RuntimeError("pythonw.exe não encontrado ao lado do Python usado.")
    executar_ps(comando_registro(raiz, pythonw), executor)
    gravar(raiz/"autonomia.json", {"ativo": True, "tarefa": nome_tarefa(raiz), "pythonw":str(pythonw)})
    # Inicia agora e também nos próximos logins; não abre outra janela do Núcleo.
    executar_ps("Start-ScheduledTask -TaskName " + literal_ps(nome_tarefa(raiz)), executor)
    return {"ativo":True,"tarefa":nome_tarefa(raiz),"iniciar_ao_entrar_no_windows":True}


def desativar(raiz, executor=subprocess.run):
    raiz = Path(raiz).resolve()
    # O supervisor abandona a monitoração sem encerrar um aplicativo que já está aberto.
    gravar(raiz/"autonomia.json", {"ativo":False,"tarefa":nome_tarefa(raiz)})
    executar_ps("$ErrorActionPreference='Stop'\nUnregister-ScheduledTask -TaskName " + literal_ps(nome_tarefa(raiz)) + " -Confirm:$false -ErrorAction SilentlyContinue",executor)
    return {"ativo":False,"mensagem":"Autoinício desativado. O aplicativo aberto não foi encerrado."}


def consultar(raiz):
    raiz = Path(raiz)
    config = raiz/"autonomia.json"
    estado = raiz/"saida"/"autonomia_estado.json"
    ultimo = json.loads(estado.read_text(encoding="utf-8")) if estado.is_file() else {}
    ultimo["sinal_recente"] = isinstance(ultimo.get("atualizado"),(int,float)) and 0 <= time.time()-ultimo["atualizado"] <= 135
    return {"config":json.loads(config.read_text(encoding="utf-8")) if config.is_file() else {"ativo":False},
            "supervisor":ultimo}


def servidor_nucleo(porta):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/ping", timeout=2) as r:
            return json.loads(r.read(2048)).get("app") == "resumo-da-manha"
    except Exception:
        return False


def porta_ocupada(porta):
    try:
        with socket.create_connection(("127.0.0.1",porta), timeout=1):
            return True
    except OSError:
        return False


class Supervisor:
    def __init__(self, raiz, verificar=servidor_nucleo, ocupada=porta_ocupada, iniciar=subprocess.Popen, relogio=time.time):
        self.raiz, self.verificar, self.ocupada = Path(raiz).resolve(), verificar, ocupada
        self.iniciar, self.relogio = iniciar, relogio
        self.processo = None
        self.reinicios = []

    def passo(self):
        cfg = json.loads((self.raiz/"autonomia.json").read_text(encoding="utf-8"))
        agora = self.relogio()
        if cfg.get("ativo") is not True:
            return False
        appcfg = json.loads((self.raiz/"config.json").read_text(encoding="utf-8-sig"))
        porta = int(appcfg.get("porta", 8765))
        if not 1 <= porta <= 65535:
            raise ValueError("Porta do Núcleo inválida.")
        self.reinicios = [t for t in self.reinicios if agora-t < 3600]
        estado = "servidor_disponivel"
        if not self.verificar(porta):
            if self.processo is not None and self.processo.poll() is None:
                estado = "aguardando_servidor_do_processo"
            elif self.ocupada(porta):
                estado = "porta_ocupada_por_outro_servico"
            elif len(self.reinicios) >= 3:
                estado = "aguardando_cota_de_reinicio"
            elif self.reinicios and agora-self.reinicios[-1] < 60:
                estado = "aguardando_reinicio"
            else:
                self.reinicios.append(agora)
                try:
                    self.processo = self.iniciar([cfg["pythonw"], str(self.raiz/"app.py"),
                        "--config",str(self.raiz/"config.json"),"--sem-janela"], cwd=str(self.raiz),
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    estado = "iniciado_em_segundo_plano"
                except OSError:
                    estado = "falha_ao_iniciar"
        gravar(self.raiz/"saida"/"autonomia_estado.json", {"atualizado":agora,"estado":estado,
               "reinicios_ultima_hora":len(self.reinicios),"tarefa":nome_tarefa(self.raiz)})
        return True


def rodar(raiz):
    import msvcrt
    raiz = Path(raiz).resolve()
    pasta = raiz/"saida"
    pasta.mkdir(exist_ok=True)
    with (pasta/"autonomia.lock").open("a+b") as trava:
        try:
            trava.seek(0)
            if trava.read(1) == b"":
                trava.write(b"0"); trava.flush()
            trava.seek(0)
            msvcrt.locking(trava.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return
        s = Supervisor(raiz)
        while s.passo():
            time.sleep(45)
