import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from catalogo_criador import carregar, importar, validar
from fontes_auto import CATALOGO, permissao
from regras_fontes import conferir_publicacao, origem_confere
from revisao_automatica import habilitada
import test_criador as fixtures

SEED = Path(__file__).resolve().parents[1] / "catalogo_fontes.json"


class CatalogoTests(unittest.TestCase):
    setUp = fixtures.EsteiraTests.setUp
    save = fixtures.EsteiraTests.save

    def preparar(self):
        (self.root / "catalogo_fontes.json").write_bytes(SEED.read_bytes())
        (self.root / "fontes_online.json").unlink()
        return carregar(self.root, CATALOGO)

    def serie(self):
        return next(f for f in self.preparar()["fontes"] if f["id"] == "vacacast-maromba-serie")

    def test_cobre_tres_destinos_com_fontes_licenciadas(self):
        c = self.preparar()
        for tema, plataforma in [("maromba", "youtube"), ("maromba", "tiktok"), ("games", "youtube")]:
            fontes = [f for f in c["fontes"] if f["tema"] == tema and plataforma in f["plataformas"] and permissao(f)]
            self.assertTrue(fontes, (tema, plataforma))
        for f in c["fontes"]:
            if f["direitos"] == "pendente":
                self.assertFalse(permissao(f))
                self.assertFalse(f.get("publicacao_catalogo", False))

    def test_serie_bloqueia_repost_vlog_outro_assunto_e_video_ja_importado(self):
        f = self.serie()
        bom = {"id": "a"*11, "title": "Nutricionista - Vaca Cast #999", "uploader_id": "@EvelynRegly", "duration": 1800}
        self.assertTrue(origem_confere(f, bom))
        for alteracao in ({"uploader_id": "@outro"}, {"title": "Vlog da nutricionista"},
                          {"title": "Vaca Cast entrevista de novela"}, {"duration": 60},
                          {"title": "Cortes Vaca Cast nutricionista"}, {"id": "7MY_ZpLqIkw"}):
            self.assertFalse(origem_confere(f, {**bom, **alteracao}), alteracao)

    def test_publicacao_confere_escopo_novamente_no_sidecar(self):
        f = self.serie()
        p = self.root / "original.mp4"
        meta = {"id": "a"*11, "origem": "a"*11, "title": "Vaca Cast nutricionista",
                "uploader_id": "@evelynregly", "duration": 1800,
                "timestamp": (dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=3)).timestamp()}
        sidecar = p.with_suffix(".mp4.json")
        sidecar.write_text(json.dumps(meta), encoding="utf-8")
        credito = f["credito"] + "\nhttps://www.youtube.com/watch?v=" + "a"*11
        conferir_publicacao(f, credito, p)
        meta["uploader_id"] = "@repost"
        sidecar.write_text(json.dumps(meta), encoding="utf-8")
        with self.assertRaises(ValueError):
            conferir_publicacao(f, credito, p)

    def test_recarrega_cadastro_sem_reiniciar_ou_mudar_codigo(self):
        c = self.preparar()
        primeiro = len(self.c.online.config()["fontes"])
        c["fontes"].append({**copy.deepcopy(c["fontes"][0]), "id": "outro-monitor"})
        entrada = self.root / "novo.json"
        entrada.write_text(json.dumps(c), encoding="utf-8")
        self.assertFalse(importar(self.root, entrada, CATALOGO)["aplicado"])
        self.assertFalse((self.root / "fontes_online.json").exists())
        importar(self.root, entrada, CATALOGO, True)
        self.assertEqual(primeiro+1, len(self.c.online.config()["fontes"]))
        importar(self.root, entrada, CATALOGO, True)
        self.assertEqual(1, len(list(self.root.glob("fontes_online.backup-*.json"))))

    def test_importacao_invalida_nao_altera_cadastro(self):
        self.preparar()
        p = self.root / "fontes_online.json"
        original = '{"ativo":false,"fontes":[]}'
        p.write_text(original, encoding="utf-8")
        entrada = self.root / "invalido.json"
        entrada.write_text('{"ativo":true,"fontes":[{"id":"../escape"}]}', encoding="utf-8")
        with self.assertRaises(ValueError): importar(self.root, entrada, CATALOGO, True)
        self.assertEqual(original, p.read_text(encoding="utf-8"))

    def test_pausa_local_antiga_e_sobreposicao_por_id_preservadas(self):
        self.preparar()
        p = self.root / "fontes_online.json"
        p.write_text('{"ativo":false,"fontes":[]}', encoding="utf-8")
        self.assertEqual([], carregar(self.root, CATALOGO)["fontes"])
        p.write_text(json.dumps({"mesclar_catalogo": True, "ativo": False,
            "fontes": [{**CATALOGO["fontes"][0], "ativo": False}]}), encoding="utf-8")
        c = carregar(self.root, CATALOGO)
        self.assertFalse(c["ativo"])
        self.assertFalse(next(f for f in c["fontes"] if f["id"] == "cariani-monitor")["ativo"])

    def test_optin_nao_se_estende_a_fontes_locais_ou_testes(self):
        cfg = {"publicacao_automatica": {"ativo": True, "fontes": []}}
        f = {"id": "novo", "publicacao_catalogo": True, "revisao_automatica": True}
        self.assertFalse(habilitada(cfg, f))
        self.assertTrue(habilitada(cfg, {**f, "origem_online": True}))
        cfg["publicacao_automatica"]["ativo"] = False
        self.assertFalse(habilitada(cfg, {**f, "origem_online": True}))

    def test_pesquisas_rodam_todo_catalogo_sem_ficar_em_um_nome(self):
        self.preparar()
        self.c.online.transporte = Mock()
        self.c.online.transporte.pesquisar.return_value = []
        for i in range(4):
            self.c.banco.set("online_tema_maromba", 0)
            self.c.online.buscar_temas(self.c.config(), self.c.online.config())
        consultas = {c.args[0] for c in self.c.online.transporte.pesquisar.call_args_list}
        for q in self.c.online.config()["buscas"]["maromba"]:
            self.assertIn(q, consultas)

    def test_dedupe_global_nao_baixa_episodio_importado_por_outra_fonte(self):
        self.preparar()
        agora = dt.datetime.now(dt.timezone.utc).timestamp()
        self.c.banco.x("INSERT INTO descobertas(fonte,video,titulo,tema,pontuacao,estado,criado) VALUES(?,?,?,?,?,?,?)",
            ("fonte-antiga", "cfaCODAGmmE", "jogo", "games", 0, "importado", agora))
        f = next(f for f in self.c.online.config()["fontes"] if f["id"] == "gaules-cs-arquivo")
        cfg = self.c.config()
        cfg["canais"] = [{**cfg["canais"][0], "tema": "games"}]
        self.c.online.registrar(f, {"id": "cfaCODAGmmE", "title": "jogo"}, cfg)
        self.c.online.transporte = Mock()
        self.c.online.importar_um(cfg, self.c.online.config())
        self.c.online.transporte.baixar.assert_not_called()

    def test_validacao_rejeita_buscas_invalidas(self):
        c = self.preparar()
        for patch in ({"buscas": {"games": []}}, {"max_buscas_ciclo": 999}, {"busca_por_tema": "sim"}):
            with self.assertRaises(ValueError): validar({**c, **patch})

    def test_edicao_encaminha_maromba_para_dois_canais_e_games_para_um(self):
        self.preparar()
        base = self.cfg["canais"][0]
        self.cfg["canais"] = [base,
            {**base, "id": "tiktok-maromba", "plataforma": "tiktok", "buffer_channel_id": "tt1", "dur_min": 65, "dur_max": 90},
            {**base, "id": "youtube-games", "tema": "games", "buffer_channel_id": "yt2"},
            {**base, "id": "tiktok-games", "tema": "games", "plataforma": "tiktok", "ativo": False, "buffer_channel_id": ""}]
        self.cfg["temas"].append({"id": "games", "palavras": ["CS"]})
        self.save()
        fontes = self.c.online.config()["fontes"]
        for ident, video in [("vacacast-rodrigo-goes-203", "7MY_ZpLqIkw"), ("gaules-cs-arquivo", "cfaCODAGmmE")]:
            f = next(f for f in fontes if f["id"] == ident)
            pasta = self.c.online.entrada / ident
            pasta.mkdir(parents=True)
            p = pasta / (video + ".mp4")
            p.write_bytes(ident.encode())
            import os, time
            os.utime(p, (time.time()-300, time.time()-300))
        self.c.descobrir(self.c.config())

        def render(app, fonte, nome, quantidade, dur_min, dur_max, legendar, **kw):
            dest = Path(app.cfg["cortes_dir"]) / nome
            dest.mkdir(parents=True, exist_ok=True)
            arq = dest / "corte.mp4"
            arq.write_bytes(nome.encode())
            return {"ok": True, "erros": [], "arquivos": [{"caminho": str(arq), "inicio": 0,
                "fim": dur_min, "duracao": dur_min, "texto": "Trecho completo de teste", "titulo": "Título de teste"}]}

        with patch("cortes.produzir", side_effect=render):
            self.c.editar_um(self.c.config())
            self.c.editar_um(self.c.config())
        rows = self.c.banco.q("SELECT canal,tema,duracao FROM posts")
        self.assertEqual({"youtube-maromba", "tiktok-maromba", "youtube-games"}, {r["canal"] for r in rows})
        self.assertEqual(3, len(rows))
        self.assertEqual(65, next(r["duracao"] for r in rows if r["canal"] == "tiktok-maromba"))

    def test_limita_buscas_e_retoma_outros_monitores_na_volta_seguinte(self):
        self.preparar()
        self.c.online.transporte = Mock()
        self.c.online.transporte.pesquisar.return_value = []
        self.c.online.transporte.listar.return_value = []
        self.c.online.ciclo(self.c.config())
        self.assertEqual(4, self.c.online.transporte.listar.call_count)
        primeiros = {c.args[0]["id"] for c in self.c.online.transporte.listar.call_args_list}
        self.c.online.transporte.listar.reset_mock()
        self.c.online.ciclo(self.c.config())
        seguintes = {c.args[0]["id"] for c in self.c.online.transporte.listar.call_args_list}
        self.assertFalse(primeiros & seguintes)


if __name__ == "__main__":
    unittest.main()
