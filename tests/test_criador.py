import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import cortes
from criador import BancoCriador, Criador, carregar_config, iso, proximo_horario
from publicacao import Buffer, EnvioIncerto, sha256


class EsteiraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inbox = self.root / "entrada"
        self.inbox.mkdir()
        self.out = self.root / "saida"
        self.out.mkdir()
        self.cfg = {"ativo":True,"publicar":True,"min_espaco_livre_mb":0,
            "fontes":[{"id":"fonte1","tema":"maromba","pasta":str(self.inbox),"direitos":"autorizado",
                       "comprovante":"autorizacao-2026","formato_revisado":True,"publicar_automaticamente":True}],
            "temas":[{"id":"maromba","palavras":["treino"],"feeds":[]}],
            "canais":[{"id":"youtube-maromba","tema":"maromba","plataforma":"youtube",
                       "buffer_channel_id":"conta123","horarios":["12:00","19:00"],"limite_dia":2,
                       "dur_min":15,"dur_max":60}]}
        self.save()
        (self.root/"fontes_online.json").write_text('{"ativo":false,"fontes":[]}',encoding="utf-8")
        self.app = SimpleNamespace(caminho_cfg=self.root/"config.json",saida=self.out,
                                  cfg={"cortes_dir":str(self.root/"cortes")},
                                  llm=SimpleNamespace(pode_conversar=lambda:False))
        self.pub = Mock()
        self.pub.agendar.return_value = {"id":"remoto123","status":"scheduled"}
        self.host = Mock()
        self.host.enviar.return_value = "https://res.cloudinary.com/test/video.mp4"
        self.c = Criador(self.app,publicador=self.pub,hospedagem=self.host)

    def save(self):
        (self.root/"criador.json").write_text(json.dumps(self.cfg),encoding="utf-8")

    def source(self, nome="treino.mp4", conteudo=b"video-fonte"):
        p = self.inbox/nome
        p.write_bytes(conteudo)
        os.utime(p,(time.time()-300,time.time()-300))
        return p

    def post(self):
        self.source()
        self.c.descobrir(self.c.config())
        f = self.c.banco.q("SELECT * FROM fontes")[0]
        video = self.out/"corte.mp4"
        video.write_bytes(b"video-renderizado")
        self.c.banco.x("""INSERT INTO posts(chave,fonte_id,canal,plataforma,tema,caminho,hash,duracao,titulo,descricao,criado)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",("corte1",f["id"],"youtube-maromba","youtube","maromba",str(video),sha256(video),30,"Treino","credito",iso()))
        return self.c.banco.q("SELECT * FROM posts")[0]

    def test_descoberta_deduplica_conteudo_renomeado(self):
        self.source()
        self.source("copia.mp4")
        self.c.descobrir(self.c.config())
        self.c.descobrir(self.c.config())
        self.assertEqual(1,len(self.c.banco.q("SELECT * FROM fontes")))

    def test_nao_ingere_fontes_sem_autorizacao(self):
        self.source()
        self.cfg["fontes"][0]["comprovante"]=""
        self.save()
        self.c.descobrir(self.c.config())
        self.assertEqual([],self.c.banco.q("SELECT * FROM fontes"))

    def test_aguarda_arquivo_estavel(self):
        (self.inbox/"copiando.mp4").write_bytes(b"a")
        self.c.descobrir(self.c.config())
        self.assertEqual([],self.c.banco.q("SELECT * FROM fontes"))

    def test_limita_backlog(self):
        for i in range(5):
            self.source(f"v{i}.mp4",bytes([i]))
        cfg=self.c.config();cfg["max_fontes_pendentes"]=2
        self.c.descobrir(cfg)
        self.assertEqual(2,len(self.c.banco.q("SELECT * FROM fontes")))

    def test_nao_publica_sem_optin(self):
        self.post()
        self.cfg["fontes"][0]["publicar_automaticamente"]=False
        self.save()
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called()
        self.host.enviar.assert_not_called()

    def test_nao_publica_formato_nao_revisado(self):
        self.post(); self.cfg["fontes"][0]["formato_revisado"]=False; self.save()
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called()

    def test_pausa_impede_hospedagem_e_post(self):
        self.post(); self.cfg["publicar"]=False; self.save()
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called(); self.host.enviar.assert_not_called()

    def test_agendado_nao_e_publicado_e_nao_duplica(self):
        self.post()
        self.c.publicar_um(self.c.config()); self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_called_once()
        self.assertEqual("agendado",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])

    def test_envio_incerto_nao_repete_apos_reinicio(self):
        self.post(); self.pub.agendar.side_effect=EnvioIncerto("conferir")
        self.c.publicar_um(self.c.config())
        self.c.banco.recuperar(); self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_called_once()
        self.assertEqual("verificar_envio",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])

    def test_recupera_crash_sem_repetir_upload(self):
        post=self.post()
        self.c.banco.x("UPDATE posts SET estado='enviando' WHERE id=?",(post["id"],))
        self.c.banco.x("UPDATE fontes SET estado='editando'")
        self.c.banco.recuperar()
        self.assertEqual("novo",self.c.banco.q("SELECT estado FROM fontes")[0]["estado"])
        self.assertEqual("verificar_envio",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])

    def test_corte_alterado_nao_e_enviado(self):
        post=self.post(); Path(post["caminho"]).write_bytes(b"alterado")
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called()
        self.assertEqual("bloqueado",self.c.banco.q("SELECT estado FROM posts")[0]["estado"])

    def test_limite_global_uploads(self):
        post=self.post()
        self.c.banco.x("UPDATE posts SET estado='agendado',enviado=?",(iso(),))
        self.c.banco.x("INSERT INTO posts(chave,fonte_id,canal,plataforma,tema,caminho,hash,duracao,titulo,descricao,criado) VALUES('outro',?,'outro','youtube','maromba',?,'outrohash',30,'x','x',?)",(post["fonte_id"],post["caminho"],iso()))
        self.cfg["max_uploads_dia"]=1; self.save()
        self.c.publicar_um(self.c.config())
        self.pub.canal.assert_not_called()

    def test_teto_hospedagem(self):
        self.post(); self.cfg["max_hospedagem_mb_dia"]=0; self.save()
        self.c.publicar_um(self.c.config())
        self.host.enviar.assert_not_called(); self.pub.agendar.assert_not_called()

    def test_metricas_so_confirmam_publicacao_apos_sent(self):
        self.post(); self.c.publicar_um(self.c.config())
        self.pub.consultar.return_value={"status":"sent","sentAt":iso(),"metrics":[{"type":"views","value":100}]}
        self.c.atualizar_metricas(self.c.config())
        post=self.c.banco.q("SELECT * FROM posts")[0]
        self.assertEqual("publicado",post["estado"])
        self.assertEqual(100,json.loads(post["metricas"])["views"])

    def test_ausencia_de_metrica_nao_vira_zero(self):
        self.post()
        self.c.banco.x("UPDATE posts SET estado='publicado',publicado=?,metricas='{}'",(iso(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=3)),))
        dados=self.c.feedback("maromba")[0]
        self.assertIsNone(dados["retencao_media"]); self.assertIsNone(dados["views_medias"])
        self.assertFalse(dados["evidencia_suficiente"])

    def test_edicao_zero_cortes_nao_cria_posts(self):
        self.source(); self.c.descobrir(self.c.config())
        with patch("cortes.produzir",return_value={"ok":False,"arquivos":[],"erros":["render falhou"]}):
            self.c.editar_um(self.c.config())
        self.assertEqual([],self.c.banco.q("SELECT * FROM posts"))
        self.assertEqual(1,self.c.banco.q("SELECT tentativas FROM fontes")[0]["tentativas"])

    def test_retentativa_edicao_tem_limite(self):
        self.source(); self.c.descobrir(self.c.config())
        with patch("cortes.produzir",return_value={"ok":False,"arquivos":[],"erros":["falhou"]}):
            for i in range(3):
                self.c.banco.x("UPDATE fontes SET proxima=0")
                self.c.editar_um(self.c.config())
        self.assertEqual("falha",self.c.banco.q("SELECT estado FROM fontes")[0]["estado"])

    def test_config_nao_aceita_string_false(self):
        self.cfg["publicar"]="false"; self.save()
        with self.assertRaises(ValueError):self.c.config()

    def test_conta_nao_pode_duplicar_em_dois_canais(self):
        self.cfg["canais"].append({**self.cfg["canais"][0],"id":"outra-conta"}); self.save()
        with self.assertRaises(ValueError):self.c.config()

    def test_trava_impede_dois_trabalhadores(self):
        outra=Criador(self.app)
        self.assertTrue(self.c._lock())
        self.addCleanup(self.c._lockfile.close)
        self.assertFalse(outra._lock())

    def test_fluxo_ingestao_edicao_agendamento_metricas(self):
        self.source()
        def render(app,fonte,nome,quantidade,dur_min,dur_max,legendar,**kwargs):
            dest=Path(app.cfg['cortes_dir'])/nome
            dest.mkdir(parents=True,exist_ok=True)
            arquivo=dest/'corte_01.mp4';arquivo.write_bytes(b'video-final')
            return {'ok':True,'erros':[],'arquivos':[{'caminho':str(arquivo),'inicio':0,'fim':30,
                    'duracao':30,'texto':'Uma história completa.','titulo':'Uma história'}]}
        self.pub.consultar.return_value={'status':'sent','sentAt':iso(),'metrics':[{'type':'views','value':500}]}
        with patch('cortes.produzir',side_effect=render):
            self.c.ciclo(self.c.config())
            self.c.banco.set('metricas_em',0)
            self.c.ciclo(self.c.config())
        self.pub.agendar.assert_called_once()
        self.assertEqual('concluido',self.c.banco.q('SELECT estado FROM fontes')[0]['estado'])
        self.assertEqual('publicado',self.c.banco.q('SELECT estado FROM posts')[0]['estado'])

    def test_revogacao_durante_hospedagem_impede_publicacao(self):
        self.post()
        def upload(*args):
            self.cfg['fontes'][0]['publicar_automaticamente']=False;self.save()
            return 'https://res.cloudinary.com/test/video.mp4'
        self.host.enviar.side_effect=upload
        self.c.publicar_um(self.c.config())
        self.pub.agendar.assert_not_called()

    def test_config_invalida_nao_quebra_inicio_do_aplicativo(self):
        self.cfg['publicar']='false';self.save()
        self.c.iniciar()
        self.assertIsNone(self.c._thread)
        self.assertIn('inválida',self.c.banco.get('ultimo_erro'))


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.words=[{"inicio":i,"fim":i+1,"texto":"Como treinar?" if i%10==0 else "fala." if i%5==0 else "treino"} for i in range(180)]

    def test_cortes_respeitam_perfil_tiktok_sem_sobreposicao(self):
        r=cortes.escolher_trechos(self.words,2,65,90)
        self.assertEqual(2,len(r))
        self.assertTrue(all(65<=x["fim"]-x["inicio"]<=90 for x in r))
        self.assertLessEqual(r[0]["fim"],r[1]["inicio"])

    def test_validacao_rejeita_tempos_inventados_pela_ia(self):
        for trechos in ([{"inicio":0,"fim":999}],[{"inicio":float('nan'),"fim":30}],
                        [{"inicio":0,"fim":30},{"inicio":15,"fim":45}]):
            with self.subTest(trechos=trechos),self.assertRaises(ValueError):
                cortes.validar_trechos(trechos,self.words,15,60,3)

    def test_zero_cortes_estrutura_falha(self):
        with tempfile.TemporaryDirectory() as t:
            arq=Path(t)/"v.mp4"; arq.write_bytes(b"video")
            app=SimpleNamespace(cfg={"cortes_dir":t},voz=object())
            with patch("cortes._ffmpeg",return_value="ffmpeg"),patch("cortes.transcrever_palavras",return_value=self.words),patch("cortes.gerar_corte",side_effect=RuntimeError("render falhou")):
                r=cortes.produzir(app,str(arq),"saida",1)
            self.assertFalse(r["ok"]); self.assertEqual([],r["arquivos"])

    def test_extracao_audio_le_wav_com_chunk_extra(self):
        import struct
        def run(cmd,**kwargs):
            p=Path(cmd[-1])
            with wave.open(str(p),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x01\x00'*1600)
            data=p.read_bytes()
            data=data[:12]+b'JUNK'+struct.pack('<I',4)+b'1234'+data[12:]
            data=data[:4]+struct.pack('<I',len(data)-8)+data[8:]
            p.write_bytes(data)
            return SimpleNamespace(returncode=0)
        modelo=Mock();modelo.transcribe.return_value=([SimpleNamespace(words=[SimpleNamespace(start=0,end=.1,word="teste")])],None)
        voz=SimpleNamespace(carregar_whisper=lambda:modelo)
        with patch('cortes._ffmpeg',return_value='ffmpeg'),patch('cortes.subprocess.run',side_effect=run):
            r=cortes.transcrever_palavras(voz,Path('fonte.mp4'))
        self.assertEqual('teste',r[0]['texto'])
        audio=modelo.transcribe.call_args.args[0]
        self.assertEqual(1600,len(audio))
        self.assertAlmostEqual(1/32768,float(audio[0]))

    def test_agenda_fuso_limite_e_ocupacao(self):
        instante=dt.datetime(2026,11,20,14,0,tzinfo=dt.timezone.utc) # 11h em São Paulo
        canal={"horarios":["12:00","19:00"],"limite_dia":1}
        primeiro=proximo_horario(canal,"America/Sao_Paulo",[],instante)
        segundo=proximo_horario(canal,"America/Sao_Paulo",[primeiro],instante)
        self.assertTrue(primeiro.startswith('2026-11-20T15:00'))
        self.assertTrue(segundo.startswith('2026-11-21T15:00'))


class PublicacaoTests(unittest.TestCase):
    def test_buffer_timeout_nao_e_repetido(self):
        pub=Buffer('token-teste')
        with patch.object(pub,'graphql',side_effect=TimeoutError()) as call:
            with self.assertRaises(EnvioIncerto):
                pub.agendar('canal','tiktok','titulo','texto','https://example.org/v.mp4','2026-12-01T12:00:00Z',{})
        call.assert_called_once()

    def test_buffer_separa_metadata_youtube_tiktok(self):
        pub=Buffer('token-teste')
        for plataforma in ('youtube','tiktok'):
            with self.subTest(plataforma=plataforma),patch.object(pub,'graphql',return_value={'createPost':{'post':{'id':'p1','status':'scheduled'}}}) as call:
                pub.agendar('canal',plataforma,'titulo','texto','https://example.org/v.mp4','2026-12-01T12:00:00Z',{})
                dados=call.call_args.args[1]['input']
                self.assertEqual('automatic',dados['schedulingType'])
                self.assertIn(plataforma,dados['metadata'])
                self.assertEqual('customScheduled',dados['mode'])


if __name__=='__main__':
    unittest.main()
