import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

import test_criador as fixtures
from fontes_auto import CATALOGO, YouTube, permissao
from publicacao import sha256
from regras_fontes import VACA_CAST, conferir_creditos, conferir_espera, origem_confere

UTC = dt.timezone.utc


class RegrasTests(unittest.TestCase):
    setUp = fixtures.EsteiraTests.setUp
    save = fixtures.EsteiraTests.save

    def preparar(self):
        self.cfg["publicar"] = False
        self.cfg["canais"][0]["ia_sintetica"] = True
        self.save()
        registro = {"ativo": True, "busca_por_tema": False, "fontes": [copy.deepcopy(VACA_CAST)]}
        (self.root/"fontes_online.json").write_text(json.dumps(registro), encoding="utf-8")
        t = Mock()
        t.listar.return_value = YouTube().listar(VACA_CAST)
        def baixar(f, v, pasta, cfg):
            arq = pasta/"video.mp4"
            arq.write_bytes(b"episodio real simulado")
            return arq, {"id": v, "title": "Rodrigo Goes no Vaca Cast", "duration": 4460,
                         "timestamp": (dt.datetime.now(UTC)-dt.timedelta(days=3)).timestamp()}
        t.baixar.side_effect = baixar
        self.c.online.transporte = t
        self.c.online.ciclo(self.c.config())
        self.c.descobrir(self.c.config())
        return t

    def post_real(self):
        self.preparar()
        fonte = self.c.banco.q("SELECT * FROM fontes")[0]
        arq = self.out/"real.mp4"; arq.write_bytes(b"corte real simulado")
        self.c.banco.x("""INSERT INTO posts(chave,fonte_id,canal,plataforma,tema,caminho,hash,duracao,titulo,descricao,criado)
          VALUES('real',?,'youtube-maromba','youtube','maromba',?,?,30,'Título próprio',?,?)""",
          (fonte["id"],str(arq),sha256(arq),fonte["descricao"],fonte["criado"]))
        return self.c.banco.q("SELECT * FROM posts")[0]

    def test_catalogo_cadastra_apenas_episodio_revisado(self):
        f = next(f for f in CATALOGO["fontes"] if f["id"] == VACA_CAST["id"])
        self.assertTrue(permissao(f))
        self.assertEqual(["7MY_ZpLqIkw"], f["videos_permitidos"])
        self.assertFalse(f["formato_revisado"])
        self.assertFalse(f["publicar_automaticamente"])

    def test_id_exato_nao_autoriza_resto_do_canal(self):
        self.assertTrue(origem_confere(VACA_CAST,{"id":"7MY_ZpLqIkw"}))
        self.assertFalse(origem_confere(VACA_CAST,{"id":"aaaaaaaaaaa"}))
        f = {**VACA_CAST, "videos_permitidos":[]}
        self.assertFalse(permissao(f))

    def test_descoberta_direta_nao_precisa_achar_episodio_na_aba_recente(self):
        itens = YouTube().listar(VACA_CAST)
        self.assertEqual(["7MY_ZpLqIkw"], [i["id"] for i in itens])

    def test_espera_48h_com_data_desconhecida_e_futura_bloqueadas(self):
        agora = dt.datetime(2026,11,20,21,tzinfo=UTC)
        for info in ({}, {"timestamp":agora.timestamp()}, {"timestamp":(agora+dt.timedelta(days=1)).timestamp()},
                     {"timestamp":(agora-dt.timedelta(hours=47)).timestamp()}):
            with self.assertRaises(ValueError): conferir_espera(VACA_CAST,info,agora)
        conferir_espera(VACA_CAST,{"timestamp":(agora-dt.timedelta(hours=48)).timestamp()},agora)

    def test_premiere_mais_recente_prevalece_sobre_upload(self):
        agora = dt.datetime.now(UTC)
        with self.assertRaises(ValueError):
            conferir_espera(VACA_CAST,{"timestamp":(agora-dt.timedelta(days=30)).timestamp(),
                "release_timestamp":agora.timestamp()},agora)

    def test_data_sem_horario_usa_fim_do_dia(self):
        with self.assertRaises(ValueError):
            conferir_espera(VACA_CAST,{"upload_date":"20261118"},dt.datetime(2026,11,20,0,tzinfo=UTC))
        conferir_espera(VACA_CAST,{"upload_date":"20261118"},dt.datetime(2026,11,21,0,tzinfo=UTC))

    def test_todos_os_creditos_obrigatorios(self):
        bom = VACA_CAST["credito"]+"\nhttps://www.youtube.com/watch?v=7MY_ZpLqIkw"
        conferir_creditos(VACA_CAST,bom)
        for trecho in VACA_CAST["creditos_obrigatorios"] + ["https://www.youtube.com/watch?v=7MY_ZpLqIkw"]:
            with self.assertRaises(ValueError): conferir_creditos(VACA_CAST,bom.replace(trecho,""))

    def test_importa_episodio_com_credito_e_data_preservados(self):
        t = self.preparar()
        t.baixar.assert_called_once()
        fonte = self.c.banco.q("SELECT * FROM fontes")[0]
        conferir_creditos(VACA_CAST,fonte["descricao"])
        p = Path(fonte["caminho"])
        meta = json.loads(p.with_suffix(p.suffix+".json").read_text(encoding="utf-8"))
        conferir_espera(VACA_CAST,meta)

    def test_rascunho_real_preserva_creditos_e_nao_chama_historia_ficticia(self):
        post = self.post_real()
        self.pub.agendar.return_value = {"id":"rascunho-real","status":"draft"}
        self.c.testar_rascunho(post["id"])
        args = self.pub.agendar.call_args.args
        conferir_creditos(VACA_CAST,args[3])
        self.assertNotIn("História fictícia",args[3])
        self.assertFalse(args[6]["ia_sintetica"])

    def test_rascunho_sem_creditos_nao_hospeda_nem_envia(self):
        post = self.post_real()
        self.c.banco.x("UPDATE posts SET descricao='sem créditos' WHERE id=?",(post["id"],))
        with self.assertRaises(ValueError): self.c.testar_rascunho(post["id"])
        self.host.enviar.assert_not_called(); self.pub.agendar.assert_not_called()

    def test_cadastro_nao_libera_publicacao_automaticamente(self):
        self.post_real()
        self.cfg["publicar"] = True; self.save()
        self.c.publicar_um(self.c.config())
        self.host.enviar.assert_not_called(); self.pub.agendar.assert_not_called()


if __name__ == "__main__": unittest.main()
