import base64
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from autonomia_windows import Supervisor, comando_registro, consultar, desativar, executar_ps, nome_tarefa, registrar
from fontes_auto import CATALOGO
from rotina_criador import configuracao, extrair_sinais, pautas_ativas
import test_criador as fixtures


class RotinaTests(unittest.TestCase):
    setUp = fixtures.EsteiraTests.setUp
    save = fixtures.EsteiraTests.save
    source = fixtures.EsteiraTests.source
    post = fixtures.EsteiraTests.post

    def preparar(self):
        c = copy.deepcopy(CATALOGO)
        c["fontes"] = []
        c["rotina"] = {"ativo":True,"intervalo_min":30,"reposicao_min":60,"min_posts_canal":2,
            "pautas":[{"tema":"games","consulta":"GTA VI dicas sem spoilers","inicio":"2026-11-19","fim":"2026-12-20"}]}
        self.app.notificar = Mock()
        self.c.online.transporte = Mock()
        self.c.online.transporte.pesquisar.return_value = []
        self.c.online.transporte.listar.return_value = []
        return c

    def test_fila_baixa_antecipa_busca_sozinha_sem_comando(self):
        c = self.preparar()
        self.c.banco.set("online_tema_maromba", 9999999999)
        self.c.rotina.ciclo(self.c.config(), c)
        self.assertEqual("0", self.c.banco.get("online_tema_maromba"))
        self.assertEqual(["maromba"],self.c.rotina.status()["reposicao_temas"])
        self.assertEqual(2,self.c.rotina.status()["canais"][0]["faltam"])
        self.app.notificar.assert_not_called()

    def test_cadencia_nao_reinicia_buscas_a_cada_minuto(self):
        c = self.preparar()
        self.c.rotina.ciclo(self.c.config(),c)
        self.c.banco.set("online_tema_maromba", 999)
        self.c.banco.set("rotina_ultima", 0)
        self.c.rotina.ciclo(self.c.config(),c)
        self.assertEqual("999",self.c.banco.get("online_tema_maromba"))
        self.app.notificar.assert_not_called()

    def test_pausa_nao_reativa_rotina_nem_publicacao(self):
        c = self.preparar()
        cfg = self.c.config();cfg["ativo"]=False
        self.c.rotina.ciclo(cfg,c)
        self.assertEqual({},self.c.rotina.status())
        self.pub.agendar.assert_not_called()
        self.app.notificar.assert_not_called()

    def test_avisos_de_conta_bloqueada_nao_se_repetem_toda_volta(self):
        c=self.preparar()
        cfg=self.c.config();cfg["canais"][0]["buffer_channel_id"]=""
        self.c.rotina.ciclo(cfg,c)
        self.c.banco.set("rotina_ultima",0)
        self.c.rotina.ciclo(cfg,c)
        self.app.notificar.assert_called_once()

    def test_fila_com_dois_posts_elegiveis_nao_forca_reposicao(self):
        c = self.preparar()
        post = self.post()
        self.c.banco.x("INSERT INTO posts(chave,fonte_id,canal,plataforma,tema,caminho,hash,duracao,titulo,descricao,criado) SELECT 'segunda',fonte_id,canal,plataforma,tema,caminho,'hash-segundo',duracao,titulo,descricao,criado FROM posts WHERE id=?",(post["id"],))
        self.c.rotina.ciclo(self.c.config(),c)
        self.assertEqual([],self.c.rotina.status()["reposicao_temas"])

    def test_video_de_teste_nao_simula_estoque_publicavel(self):
        c=self.preparar();self.post()
        self.cfg["fontes"][0].update(formato_revisado=False,publicar_automaticamente=False)
        self.save();self.c.rotina.ciclo(self.c.config(),c)
        self.assertEqual(0,self.c.rotina.status()["canais"][0]["fila"])

    def test_pauta_expira_sem_edicao_de_codigo(self):
        c=self.preparar()
        self.assertTrue(pautas_ativas(c,"games","2026-11-20"))
        self.assertEqual([],pautas_ativas(c,"games","2027-01-01"))
        self.assertEqual([],pautas_ativas(c,"maromba","2026-11-20"))

    def test_detecta_recorrencia_em_tres_canais_e_nao_repeticao_de_um(self):
        um=[{"titulo":"GTA 6 novas mecânicas","fonte":"achado-1"}]*20
        self.assertEqual([],extrair_sinais(um))
        varios=[{"titulo":"GTA 6 novas mecânicas","fonte":"achado-"+str(i)} for i in range(3)]
        self.assertIn("gta 6",extrair_sinais(varios))

    def test_rotina_alimenta_busca_automaticamente_sem_liberar_direitos(self):
        c=self.preparar()
        cfg=self.c.config();cfg["canais"][0]["tema"]="games"
        cfg["temas"].append({"id":"games","palavras":["gameplay"]})
        c["rotina"]["pautas"][0].update(inicio="2000-01-01",fim="2099-01-01")
        self.c.rotina.ciclo(cfg,c)
        self.c.online.buscar_temas(cfg,c)
        self.assertIn("GTA VI dicas sem spoilers",[x.args[0] for x in self.c.online.transporte.pesquisar.call_args_list])
        self.c.online.transporte.baixar.assert_not_called()

    def test_parametros_invalidos_rejeitados(self):
        for r in ({"ativo":"sim"},{"ativo":True,"reposicao_min":0},{"ativo":True,"pautas":[{}]}):
            with self.assertRaises((ValueError,KeyError)):configuracao({"rotina":r})


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"config.json").write_text('{"porta":8765}',encoding="utf-8")
        (self.root/"autonomia.json").write_text('{"ativo":true,"pythonw":"pythonw.exe"}',encoding="utf-8")
        self.verificar=Mock(return_value=False);self.ocupada=Mock(return_value=False)
        self.iniciar=Mock(return_value=SimpleNamespace(poll=lambda:None))
        self.agora=10000
        self.s=Supervisor(self.root,self.verificar,self.ocupada,self.iniciar,lambda:self.agora)

    def test_aplicativo_existente_nao_gera_segunda_instancia(self):
        self.verificar.return_value=True
        self.assertTrue(self.s.passo());self.iniciar.assert_not_called()

    def test_estado_antigo_nao_e_apresentado_como_supervisor_recente(self):
        self.s.passo()
        with patch("autonomia_windows.time.time",return_value=self.agora+10):
            self.assertTrue(consultar(self.root)["supervisor"]["sinal_recente"])
        with patch("autonomia_windows.time.time",return_value=self.agora+200):
            self.assertFalse(consultar(self.root)["supervisor"]["sinal_recente"])

    def test_processo_iniciado_sem_janela_e_sem_shell(self):
        self.s.passo();self.s.passo()
        self.iniciar.assert_called_once()
        args=self.iniciar.call_args.args[0]
        self.assertIn("--sem-janela",args)
        self.assertNotIn("shell",self.iniciar.call_args.kwargs)
        self.assertEqual(self.root,Path(self.iniciar.call_args.kwargs["cwd"]))

    def test_reinicio_respeita_espera_e_limite_por_hora(self):
        self.iniciar.return_value=SimpleNamespace(poll=lambda:1)
        self.s.passo();self.s.passo();self.assertEqual(1,self.iniciar.call_count)
        for n in range(4):self.agora+=61;self.s.passo()
        self.assertEqual(3,self.iniciar.call_count)
        self.agora+=3601;self.s.passo()
        self.assertEqual(4,self.iniciar.call_count)

    def test_outro_servico_na_porta_nao_e_encerrado(self):
        self.ocupada.return_value=True
        self.s.passo();self.iniciar.assert_not_called()
        estado=json.loads((self.root/"saida"/"autonomia_estado.json").read_text(encoding="utf-8"))
        self.assertEqual("porta_ocupada_por_outro_servico",estado["estado"])

    def test_desativar_nao_encerra_aplicativo_aberto(self):
        self.s.passo()
        with patch("autonomia_windows.executar_ps"):
            desativar(self.root)
        self.assertFalse(self.s.passo())
        self.assertEqual(1,self.iniciar.call_count)

    def test_registro_sem_senha_sem_elevacao_e_com_caminhos_citados(self):
        script=comando_registro(self.root/"João d'Ávila",r"C:\Python\pythonw.exe")
        self.assertIn("-LogonType Interactive",script)
        self.assertIn("-RunLevel Limited",script)
        self.assertIn("d''Ávila",script)
        self.assertNotIn("-Password",script)
        executar=Mock(return_value=SimpleNamespace(returncode=0))
        executar_ps(script,executar)
        encoded=executar.call_args.args[0][-1]
        self.assertEqual(script,base64.b64decode(encoded).decode("utf-16le"))

    def test_falha_no_registro_nao_declara_autonomia_ativa(self):
        (self.root/"app.py").write_text("# teste")
        (self.root/"iniciar_nucleo_autonomo.py").write_text("# teste")
        (self.root/"autonomia.json").unlink()
        with patch("autonomia_windows.executar_ps",side_effect=RuntimeError("negado")):
            with self.assertRaises(RuntimeError):registrar(self.root)
        self.assertFalse((self.root/"autonomia.json").exists())


if __name__ == "__main__":unittest.main()
