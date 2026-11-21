import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cortes
import test_criador as fixtures
from fontes_auto import diagnostico_download, YouTube
from publicacao import sha256
from revisao_automatica import habilitada, criar_capa, validar_midia, executar


class AutomaticaTests(unittest.TestCase):
    setUp = fixtures.EsteiraTests.setUp
    save = fixtures.EsteiraTests.save
    source = fixtures.EsteiraTests.source
    post = fixtures.EsteiraTests.post

    def preparar(self):
        self.cfg["publicacao_automatica"] = {"ativo":True,"fontes":["fonte1"]}
        self.cfg["fontes"][0].update(formato_revisado=False,publicar_automaticamente=False,revisao_automatica=True)
        self.save()
        post = self.post()
        self.c.banco.x("UPDATE posts SET titulo='Como comecei a jogar no computador' WHERE id=?", (post["id"],))
        post["titulo"] = "Como comecei a jogar no computador"
        perfil = hashlib.sha256(post["canal"].encode()).hexdigest()[:12]
        pasta = cortes._pasta(self.app)/f"auto-{post['fonte_id']}-{perfil}"
        pasta.mkdir(parents=True)
        (pasta/"manifesto.json").write_text(json.dumps({"ok":True,"arquivos":[{
            "caminho":post["caminho"],"inicio":0,"fim":30,"texto":
            "Eu comecei a jogar no computador quando era pequeno e treinava com meus amigos. Depois decidi estudar e gostei de trabalhar com jogos."}]}),encoding="utf-8")
        self.resposta = {"contexto_claro":True,"titulo_fiel":True,"sem_alegacoes_inventadas":True,
                         "adequado_para_publicacao":True,"titulo":post["titulo"],"motivo":"Contexto claro"}
        self.app.llm = SimpleNamespace(pode_conversar=lambda:True,json=Mock(return_value=self.resposta),modelo="teste-local")
        self.addCleanup(patch.stopall)
        self.midia = patch("revisao_automatica.validar_midia",return_value={"duracao_real":30}).start()
        self.capa = patch("revisao_automatica.criar_capa",side_effect=lambda arq,titulo:str(arq)+".capa.png").start()
        return post

    def test_aprova_e_agenda_sem_fingir_revisao_manual(self):
        self.preparar(); self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_called_once(); self.host.enviar.assert_called_once()
        self.assertEqual("agendado",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])
        fonte = self.c.config()["fontes"][0]
        self.assertIs(fonte["formato_revisado"],False)
        self.assertIs(fonte["publicar_automaticamente"],False)
        self.assertEqual("aprovado",self.c.revisor.status()["resumo"][0]["estado"])

    def test_sem_optin_da_fonte_nao_publica(self):
        self.preparar()
        self.cfg["publicacao_automatica"]["fontes"] = []
        self.save(); self.c.publicar_um(self.c.config())
        self.host.enviar.assert_not_called(); self.app.llm.json.assert_not_called()

    def test_titulo_reformulado_exige_segunda_revisao_e_envia_texto_exato(self):
        post = self.preparar()
        novo = "Como os jogos mudaram minha escolha de profissão"
        self.app.llm.json.side_effect = [{**self.resposta, "titulo": novo}, {**self.resposta, "titulo": "outro texto ignorado"}]
        self.c.publicar_um(self.c.config())
        self.assertEqual(2, self.app.llm.json.call_count)
        segundo = json.loads(self.app.llm.json.call_args_list[1].args[0][0]["content"])
        self.assertEqual(novo, segundo["titulo_proposto"])
        self.assertEqual(novo, self.pub.agendar.call_args.args[2])
        self.assertEqual(novo, self.c.banco.q("SELECT titulo FROM posts WHERE id=?", (post["id"],))[0]["titulo"])

    def test_reformulacao_recusada_nao_hospeda(self):
        self.preparar()
        self.app.llm.json.side_effect = [{**self.resposta, "titulo": "Um novo título sem contexto"},
                                       {**self.resposta, "titulo_fiel": False}]
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called()
        self.host.enviar.assert_not_called()

    def test_fonte_sem_direitos_nao_entra_no_revisor(self):
        self.preparar()
        self.cfg["fontes"][0]["direitos"] = "pendente"
        self.save();self.c.publicar_um(self.c.config())
        self.app.llm.json.assert_not_called();self.pub.agendar.assert_not_called()

    def test_global_pausado_nao_avalia_ou_hospeda(self):
        self.preparar(); self.cfg["publicar"] = False
        self.save();self.c.publicar_um(self.c.config())
        self.app.llm.json.assert_not_called(); self.host.enviar.assert_not_called()

    def test_reprovado_editorial_nao_publica_nem_lota_fila_pronta(self):
        self.preparar(); self.resposta["titulo_fiel"] = False
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called();self.host.enviar.assert_not_called()
        self.assertEqual("reprovado_automatico",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])

    def test_ia_offline_reagenda_revisao_sem_aprovacao_manual(self):
        self.preparar();self.app.llm.pode_conversar=lambda:False
        self.c.publicar_um(self.c.config())
        r = self.c.banco.q("SELECT * FROM revisoes_publicacao")[0]
        self.assertEqual("aguardando",r["estado"])
        self.assertGreater(r["proxima"],r["quando"])
        self.assertEqual("pronto",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])
        self.pub.agendar.assert_not_called()

    def test_json_de_revisao_invalido_nao_e_aprovado(self):
        self.preparar();self.resposta["titulo_fiel"] = "true"
        self.c.publicar_um(self.c.config())
        self.assertEqual("aguardando",self.c.banco.q("SELECT estado FROM revisoes_publicacao")[0]["estado"])
        self.pub.agendar.assert_not_called()

    def test_video_invalido_nao_e_enviado(self):
        self.preparar();self.midia.side_effect=ValueError("sem áudio")
        self.c.publicar_um(self.c.config())
        self.host.enviar.assert_not_called();self.pub.agendar.assert_not_called()

    def test_corte_modificado_recusado(self):
        post = self.preparar(); Path(post["caminho"]).write_bytes(b"outro")
        self.c.publicar_um(self.c.config())
        self.app.llm.json.assert_not_called();self.host.enviar.assert_not_called()

    def test_aprovacao_cache_e_invalidacao_por_configuracao(self):
        post = self.preparar(); cfg = self.c.config(); fonte=cfg["fontes"][0];canal=cfg["canais"][0]
        self.assertTrue(self.c.revisor.avaliar(post,fonte,canal,cfg))
        self.assertTrue(self.c.revisor.avaliar(post,fonte,canal,cfg))
        self.assertEqual(1,self.app.llm.json.call_count)
        fonte = {**fonte,"credito":"crédito revisado"}
        self.assertTrue(self.c.revisor.avaliar(post,fonte,canal,cfg))
        self.assertEqual(2,self.app.llm.json.call_count)

    def test_revogacao_durante_hospedagem_impede_post(self):
        self.preparar()
        def hospedar(*args):
            self.cfg["publicacao_automatica"]["ativo"] = False;self.save()
            return "https://res.cloudinary.com/test/video.mp4"
        self.host.enviar.side_effect=hospedar
        self.c.publicar_um(self.c.config());self.pub.agendar.assert_not_called()

    def test_titulo_muito_curto_recusado(self):
        self.preparar();self.c.banco.x("UPDATE posts SET titulo='oi'")
        self.resposta["titulo"] = "oi"
        self.c.publicar_um(self.c.config());self.host.enviar.assert_not_called()

    def test_download_diagnostica_sem_vazar_texto_bruto(self):
        for texto,parte in (("Requested format not available token=segredo","Formato"),
            ("Sign in to confirm not a bot token=segredo","autenticação"),
            ("getaddrinfo failed token=segredo","rede"),
            ("HTTP Error 403 token=segredo","restringiu")):
            resposta = diagnostico_download(RuntimeError(texto))
            self.assertIn(parte,resposta); self.assertNotIn("segredo",resposta)

    def test_node_explicitamente_habilitado_quando_disponivel(self):
        with patch("fontes_auto.shutil.which",return_value=r"C:\node\node.exe"):
            self.assertEqual(r"C:\node\node.exe",YouTube.opcoes()["js_runtimes"]["node"]["path"])


class MidiaRealTests(unittest.TestCase):
    def test_ffmpeg_valida_e_aplica_capa_sem_perder_audio(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"video.mp4"
            executar([cortes._ffmpeg(),"-v","error","-y","-f","lavfi","-i","color=c=blue:s=320x568:r=24",
                "-f","lavfi","-i","sine=frequency=440:sample_rate=44100","-t","1.5",
                "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",str(p)])
            canal={"dur_min":1,"dur_max":3}
            self.assertTrue(validar_midia(p,canal,1.5)["audio_decodificado"])
            antes=sha256(p)
            capa=criar_capa(p,"Como comecei a jogar no computador")
            self.assertTrue(Path(capa).is_file());self.assertNotEqual(antes,sha256(p))
            self.assertTrue(validar_midia(p,canal,1.5)["audio_decodificado"])
            with self.assertRaises(ValueError):validar_midia(p,{"dur_min":20,"dur_max":60},1.5)


if __name__ == "__main__":unittest.main()
