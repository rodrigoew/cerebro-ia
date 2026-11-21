import datetime as dt
import hashlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import test_criador as fixtures
from limpeza_criador import configuracao
from publicacao import sha256


class LimpezaTests(unittest.TestCase):
    setUp = fixtures.EsteiraTests.setUp
    save = fixtures.EsteiraTests.save
    source = fixtures.EsteiraTests.source
    post = fixtures.EsteiraTests.post

    def preparar(self, online=False):
        post = self.post()
        fonte = self.c.banco.q("SELECT * FROM fontes")[0]
        perfil = hashlib.sha256(post["canal"].encode()).hexdigest()[:12]
        pasta = Path(self.app.cfg["cortes_dir"]) / f"auto-{fonte['id']}-{perfil}"
        pasta.mkdir(parents=True)
        corte = pasta / "corte.mp4"
        Path(post["caminho"]).replace(corte)
        self.c.banco.x("UPDATE posts SET caminho=?,estado='publicado',remoto_id='confirmado',publicado=? WHERE id=?",
            (str(corte), (dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=2)).isoformat(), post["id"]))
        self.c.banco.x("UPDATE fontes SET estado='concluido' WHERE id=?", (fonte["id"],))
        original = Path(fonte["caminho"])
        if online:
            pasta = self.c.online.entrada / "cariani-monitor"
            pasta.mkdir(parents=True)
            alvo = pasta / "aaaaaaaaaaa.mp4"
            original.replace(alvo); original = alvo
            self.c.banco.x("UPDATE fontes SET caminho=?,fonte_id='online-cariani-monitor' WHERE id=?", (str(alvo), fonte["id"]))
            self.c.banco.x("""INSERT INTO descobertas(fonte,video,titulo,tema,pontuacao,estado,criado,caminho)
                VALUES('cariani-monitor','aaaaaaaaaaa','Teste','maromba',0,'importado',0,?)""", (str(alvo),))
        return corte, original

    def test_remove_corte_e_original_online_apenas_depois_da_confirmacao(self):
        corte, original = self.preparar(True)
        self.c.limpeza.ciclo(self.c.config())
        self.assertFalse(corte.exists()); self.assertFalse(original.exists())
        self.assertEqual(2, self.c.limpeza.status(self.c.config())["resumo"][0]["arquivos"])

    def test_preserva_original_local(self):
        corte, original = self.preparar()
        self.c.limpeza.ciclo(self.c.config())
        self.assertFalse(corte.exists()); self.assertTrue(original.exists())

    def test_nao_remove_agendados_rascunhos_erros_ou_envios_incertos(self):
        corte, original = self.preparar(True)
        for estado in ("pronto", "agendado", "rascunho_teste", "verificar_envio", "falha_publicacao", "enviando"):
            self.c.banco.x("UPDATE posts SET estado=?", (estado,))
            self.c.limpeza.ciclo(self.c.config())
            self.assertTrue(corte.exists(), estado); self.assertTrue(original.exists(), estado)

    def test_sem_id_ou_horario_confirmado_preserva(self):
        corte, _ = self.preparar()
        self.c.banco.x("UPDATE posts SET remoto_id=NULL")
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())
        self.c.banco.x("UPDATE posts SET remoto_id='id',publicado=NULL")
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())

    def test_aguarda_publicacao_de_todos_os_cortes(self):
        corte, original = self.preparar(True)
        p = self.c.banco.q("SELECT * FROM posts")[0]
        self.c.banco.x("""INSERT INTO posts(chave,fonte_id,canal,plataforma,tema,caminho,hash,duracao,titulo,descricao,criado)
            VALUES('pendente',?,'tiktok-maromba','tiktok','maromba',?,?,60,'teste','',?)""",
            (p["fonte_id"], str(self.out/"outro.mp4"), "b"*64, p["criado"]))
        self.c.limpeza.ciclo(self.c.config())
        self.assertTrue(corte.exists()); self.assertTrue(original.exists())

    def test_respeita_retencao_24h(self):
        corte, _ = self.preparar()
        self.c.banco.x("UPDATE posts SET publicado=?", (dt.datetime.now(dt.timezone.utc).isoformat(),))
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())

    def test_edicao_incompleta_preserva_original_e_cortes(self):
        corte, original = self.preparar(True)
        self.c.banco.x("UPDATE fontes SET estado='erro'")
        self.c.limpeza.ciclo(self.c.config())
        self.assertTrue(corte.exists()); self.assertTrue(original.exists())

    def test_arquivo_modificado_vira_revisao_sem_exclusao(self):
        corte, _ = self.preparar()
        corte.write_bytes(b"conteudo alterado")
        self.c.limpeza.ciclo(self.c.config())
        self.assertTrue(corte.exists())
        self.assertEqual("revisar", self.c.limpeza.status(self.c.config())["pendencias"][0]["estado"])

    def test_fora_da_pasta_gerenciada_nao_apaga(self):
        corte, _ = self.preparar()
        fora = self.root/"arquivo-pessoal.mp4"
        corte.replace(fora)
        self.c.banco.x("UPDATE posts SET caminho=?", (str(fora),))
        self.c.limpeza.ciclo(self.c.config())
        self.assertTrue(fora.exists())

    def test_nao_apaga_arquivo_compartilhado_com_post_pendente(self):
        corte, _ = self.preparar()
        self.c.banco.x("""INSERT INTO fontes(chave,caminho,hash,fonte_id,tema,titulo,descricao,estado,criado)
            VALUES('outra','outro',?,'fonte1','maromba','teste','','concluido','hoje')""", ("b"*64,))
        self.c.banco.x("""INSERT INTO posts(chave,fonte_id,canal,plataforma,tema,caminho,hash,duracao,titulo,descricao,criado)
            VALUES('pendente',2,'outro','tiktok','maromba',?,?,60,'teste','','hoje')""", (str(corte), sha256(corte)))
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())

    def test_modo_propor_cria_um_lembrete_e_nao_apaga(self):
        corte, _ = self.preparar()
        self.cfg["limpeza"] = {"modo": "propor"}; self.save()
        memoria = sqlite3.connect(":memory:")
        memoria.row_factory = sqlite3.Row
        self.addCleanup(memoria.close)
        memoria.execute("CREATE TABLE lembretes(id INTEGER PRIMARY KEY,texto TEXT,data TEXT,hora TEXT,criado_em TEXT,feito INTEGER DEFAULT 0)")
        def x(sql, args):
            with memoria: return memoria.execute(sql, args).lastrowid
        self.app.memoria = SimpleNamespace(q=lambda sql,args: [dict(r) for r in memoria.execute(sql,args)], x=x)
        self.app.notificar = Mock()
        self.c.limpeza.ciclo(self.c.config()); self.c.limpeza.ciclo(self.c.config())
        self.assertTrue(corte.exists())
        self.assertEqual(1, memoria.execute("SELECT COUNT(*) FROM lembretes").fetchone()[0])
        self.app.notificar.assert_called_once()
        corte.unlink()
        self.c.limpeza.ciclo(self.c.config())
        self.assertEqual(1, memoria.execute("SELECT feito FROM lembretes").fetchone()[0])

    def test_desativado_preserva_arquivos(self):
        corte, _ = self.preparar()
        self.cfg["limpeza"] = {"modo": "desativado"}; self.save()
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())

    def test_criador_pausado_preserva_arquivos(self):
        corte, _ = self.preparar()
        self.cfg["ativo"] = False; self.save()
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())

    def test_arquivo_ocupado_nao_e_considerado_apagado(self):
        corte, _ = self.preparar()
        with patch.object(Path, "unlink", side_effect=PermissionError("ocupado")):
            self.c.limpeza.ciclo(self.c.config())
        self.assertTrue(corte.exists())
        self.assertEqual("revisar", self.c.limpeza.status(self.c.config())["pendencias"][0]["estado"])

    def test_limpeza_repetida_nao_conta_espaco_duas_vezes(self):
        self.preparar(True)
        self.c.limpeza.ciclo(self.c.config())
        antes = self.c.limpeza.status(self.c.config())["resumo"]
        self.c.limpeza.ciclo(self.c.config())
        self.assertEqual(antes, self.c.limpeza.status(self.c.config())["resumo"])

    def test_hash_invalido_ou_modo_invalido_rejeitado(self):
        corte, _ = self.preparar()
        self.c.banco.x("UPDATE posts SET hash='invalido'")
        self.c.limpeza.ciclo(self.c.config()); self.assertTrue(corte.exists())
        for cfg in ({"modo": "qualquer"}, {"reter_horas": -1}, {"reter_horas": float("nan")}):
            with self.assertRaises(ValueError): configuracao({"limpeza": cfg})


if __name__ == "__main__": unittest.main()
