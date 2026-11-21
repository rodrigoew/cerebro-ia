import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cortes
from criador import BancoCriador


class AudioSimulado:
    def __init__(self, duracao, leituras):self.frames=int(duracao*16000);self.leituras=leituras
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def getnframes(self):return self.frames
    def getframerate(self):return 16000
    def getnchannels(self):return 1
    def getsampwidth(self):return 2
    def setpos(self,pos):self.pos=pos
    def readframes(self,n):
        self.leituras.append(n)
        if n>124*16000:raise AssertionError("Áudio integral solicitado à memória")
        return b"\x01\x00"*n


class BlocosTests(unittest.TestCase):
    def transcrever(self,duracao,modelo,bloco=120,limite=7200):
        leituras=[]
        voz=SimpleNamespace(carregar_whisper=Mock(return_value=modelo),_whisper_gpu=False)
        with patch("cortes._ffmpeg",return_value="ffmpeg"),patch("cortes.subprocess.run",return_value=SimpleNamespace(returncode=0)),\
             patch("cortes.wave.open",side_effect=lambda *a,**k:AudioSimulado(duracao,leituras)):
            palavras=cortes.transcrever_palavras(voz,Path("episodio.mp4"),max_duracao_seg=limite,bloco_seg=bloco)
        return palavras,leituras,voz

    def test_podcast_75_minutos_nao_vira_um_array_integral(self):
        tamanhos=[]
        def inferir(audio,**kwargs):
            tamanhos.append(len(audio))
            self.assertEqual("float32",str(audio.dtype))
            self.assertAlmostEqual(1/32768,float(audio[0]))
            return iter([]),None
        modelo=SimpleNamespace(transcribe=Mock(side_effect=inferir))
        _,leituras,voz=self.transcrever(4500,modelo)
        self.assertEqual(math.ceil(4500/120),len(tamanhos))
        self.assertLessEqual(max(leituras),124*16000)
        self.assertLessEqual(max(tamanhos),124*16000)
        voz.carregar_whisper.assert_called_once()

    def test_tempos_absolutos_e_sobreposicao_sem_repetir_palavra_da_borda(self):
        chamada=[0]
        deslocamentos=[0,1.5,3.5]
        palavras=[(1.9,2.1,"borda dois"),(3.9,4.1,"borda quatro"),(5.8,6.0,"última")]
        def inferir(audio,**kwargs):
            i=chamada[0];chamada[0]+=1;inicio=deslocamentos[i]
            termos=[SimpleNamespace(start=a-inicio,end=b-inicio,word=t) for a,b,t in palavras
                    if a>=inicio and b<=inicio+len(audio)/16000]
            return [SimpleNamespace(words=termos)],None
        modelo=SimpleNamespace(transcribe=inferir)
        resultado,_,_=self.transcrever(6,modelo,bloco=2)
        self.assertEqual(["borda dois","borda quatro","última"],[p["texto"] for p in resultado])
        self.assertAlmostEqual(1.9,resultado[0]["inicio"])
        self.assertAlmostEqual(4.1,resultado[1]["fim"])
        self.assertAlmostEqual(6.0,resultado[2]["fim"])

    def test_recusa_video_longo_antes_de_carregar_modelo(self):
        modelo=Mock()
        with self.assertRaises(ValueError):self.transcrever(121,modelo,limite=120)
        modelo.transcribe.assert_not_called()

    def test_janela_invalida_e_recusada(self):
        for tamanho in (0,-1,301,float("nan")):
            with self.assertRaises(ValueError):
                cortes.transcrever_palavras(SimpleNamespace(),Path("fonte"),bloco_seg=tamanho)

    def test_palavras_sem_tempo_finito_nao_entram_na_saida(self):
        modelo=SimpleNamespace(transcribe=lambda *a,**k:([SimpleNamespace(words=[
            SimpleNamespace(start=float("nan"),end=1,word="inválida"),
            SimpleNamespace(start=.2,end=.5,word="válida")])],None))
        resultado,_,_=self.transcrever(1,modelo)
        self.assertEqual(["válida"],[p["texto"] for p in resultado])

    def test_recuperacao_reinicia_apenas_falha_de_memoria_e_so_uma_vez(self):
        with tempfile.TemporaryDirectory() as temp:
            banco=BancoCriador(Path(temp)/"criador.db")
            for ident,erro in ((1,"Unable to allocate 1.33 GiB for an array"),(2,"Outro erro de edição")):
                banco.x("""INSERT INTO fontes(id,chave,caminho,hash,fonte_id,tema,titulo,descricao,estado,tentativas,proxima,erro,criado)
                    VALUES(?,?,'arquivo','hash','fonte','maromba','teste','','falha',3,9999999999,?,'hoje')""",(ident,str(ident),erro))
            banco.recuperar()
            a,b=banco.q("SELECT * FROM fontes ORDER BY id")
            self.assertEqual(("novo",0,0,None),(a["estado"],a["tentativas"],a["proxima"],a["erro"]))
            self.assertEqual("falha",b["estado"])
            banco.x("UPDATE fontes SET estado='falha',tentativas=3,erro='Unable to allocate novamente' WHERE id=1")
            banco.recuperar()
            self.assertEqual("falha",banco.q("SELECT estado FROM fontes WHERE id=1")[0]["estado"])


if __name__=="__main__":unittest.main()
