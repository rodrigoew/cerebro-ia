import datetime as dt
import json
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

from fontes_auto import CATALOGO, FontesOnline, YouTube, permissao, url_canal
import test_criador as fixtures


class FontesTests(unittest.TestCase):
    setUp = fixtures.EsteiraTests.setUp
    save = fixtures.EsteiraTests.save
    source = fixtures.EsteiraTests.source
    post = fixtures.EsteiraTests.post

    def preparar(self, autorizado=True):
        c = json.loads(json.dumps(CATALOGO))
        c["fontes"] = [c["fontes"][0]]
        f = c["fontes"][0]
        if autorizado:
            f.update(channel_id="UC" + "a" * 22, direitos="autorizado", comprovante="Contrato teste",
                     plataformas=["youtube"], formato_revisado=True, publicar_automaticamente=True)
        self.registry = c
        self.gravar()
        t = Mock()
        t.pesquisar.return_value = []
        t.listar.return_value = [{"id": "a"*11, "title": "treino episódio"}]
        def baixar(fonte, video, pasta, cfg):
            p = pasta / "video.mp4"
            p.write_bytes(b"video-real-simulado")
            return p, {"channel_id": "UC"+"a"*22, "title": "treino episódio"}
        t.baixar.side_effect = baixar
        self.c.online.transporte = t
        return t

    def gravar(self):
        (self.root / "fontes_online.json").write_text(json.dumps(self.registry), encoding="utf-8")

    def ciclo(self):
        self.c.online.ciclo(self.c.config())

    def test_monitoramento_sem_autorizacao_nao_baixa(self):
        t = self.preparar(False)
        self.ciclo()
        self.assertEqual(1, len(self.c.online.status()["episodios"]))
        t.baixar.assert_not_called()
        self.assertFalse(self.c.online.status()["fontes"][0]["autorizada"])

    def test_busca_descobre_varios_criadores_sem_lista_fixa(self):
        t = self.preparar(False)
        t.listar.return_value = []
        t.pesquisar.return_value = [{"id": letra*11, "channel_id": "UC"+letra*22,
                                    "channel": "Criador " + letra, "title": "treino podcast"}
                                   for letra in "abc"]
        self.ciclo()
        status = self.c.online.status()
        self.assertEqual(3, len(status["canais_encontrados"]))
        self.assertEqual(3, len(status["episodios"]))
        self.assertEqual(3, len(self.c.banco.q("SELECT * FROM sinais")))
        t.baixar.assert_not_called()
        consultas = [c.args[0] for c in t.pesquisar.call_args_list]
        self.assertIn("podcast musculação fisiculturismo", consultas)
        self.assertFalse(any("Cariani" in q for q in consultas))

    def test_busca_deduplica_e_respeita_intervalo(self):
        t = self.preparar(False)
        t.listar.return_value = []
        t.pesquisar.return_value = [{"id": "a"*11, "channel_id": "UC"+"a"*22, "title": "treino"}]
        self.ciclo(); self.ciclo()
        self.assertEqual(3, t.pesquisar.call_count)
        self.assertEqual(1, len(self.c.online.status()["episodios"]))

    def test_busca_encaminha_fonte_ja_autorizada_para_editor(self):
        t = self.preparar()
        t.listar.return_value = []
        t.pesquisar.return_value = [{"id": "b"*11, "channel_id": "UC"+"a"*22, "title": "treino"}]
        self.ciclo(); self.c.descobrir(self.c.config())
        self.assertEqual(1, t.baixar.call_count)
        self.assertEqual("online-cariani-monitor", self.c.banco.q("SELECT * FROM fontes")[0]["fonte_id"])

    def test_busca_falha_sem_bloquear_monitor_de_canal(self):
        t = self.preparar(False)
        t.pesquisar.side_effect = RuntimeError("falha de rede")
        self.ciclo()
        t.listar.assert_called_once()
        self.assertEqual(1, len(self.c.online.status()["episodios"]))
        self.assertEqual("RuntimeError", self.c.online.status()["buscas"][0]["erro"])

    def test_busca_roda_palavras_e_pode_ser_pausada(self):
        t = self.preparar(False)
        self.cfg["temas"][0]["palavras"] = ["musculação", "competição"]
        self.save(); self.ciclo()
        self.c.banco.set("online_tema_maromba", 0)
        self.ciclo()
        self.assertIn("competição podcast entrevista melhores momentos", [c.args[0] for c in t.pesquisar.call_args_list])
        self.registry["busca_por_tema"] = False
        self.gravar(); t.pesquisar.reset_mock()
        self.c.banco.set("online_tema_maromba", 0)
        self.ciclo(); t.pesquisar.assert_not_called()

    def test_busca_respeita_temas_de_canais_ativos(self):
        t = self.preparar(False)
        self.cfg["canais"][0]["tema"] = "games"
        self.cfg["temas"].append({"id": "games", "palavras": ["gameplay"]})
        self.save(); self.ciclo()
        consultas = [c.args[0] for c in t.pesquisar.call_args_list]
        self.assertIn("live melhores momentos gameplay", consultas)
        self.assertNotIn("podcast musculação fisiculturismo", consultas)
        t.listar.assert_not_called()

    def test_adaptador_pesquisa_apenas_metadados_e_limita_resultados(self):
        resultado = {"entries": [{"id": str(i)} for i in range(25)]}
        ydl = Mock()
        ydl.__enter__ = Mock(return_value=ydl)
        ydl.__exit__ = Mock(return_value=False)
        ydl.extract_info.return_value = resultado
        with patch("yt_dlp.YoutubeDL", return_value=ydl) as construtor:
            itens = YouTube().pesquisar("podcast musculação")
        self.assertEqual(10, len(itens))
        ydl.extract_info.assert_called_once_with("ytsearch10:podcast musculação", download=False)
        self.assertEqual("in_playlist", construtor.call_args.args[0]["extract_flat"])

    def test_importa_e_editor_local_encontra_com_credito(self):
        self.preparar()
        self.ciclo()
        self.c.descobrir(self.c.config())
        rows = self.c.banco.q("SELECT * FROM fontes")
        self.assertEqual(1, len(rows))
        self.assertEqual("online-cariani-monitor", rows[0]["fonte_id"])
        self.assertIn("https://www.youtube.com/watch?v="+"a"*11, rows[0]["descricao"])
        self.assertEqual("importado", self.c.online.status()["episodios"][0]["estado"])

    def test_deduplica_buscas_e_downloads(self):
        t = self.preparar()
        self.ciclo()
        self.c.banco.set("online_busca_cariani-monitor", 0)
        self.ciclo()
        self.assertEqual(1, t.baixar.call_count)
        self.assertEqual(1, len(self.c.online.status()["episodios"]))

    def test_intervalo_e_falha_de_rede_nao_tentam_toda_volta(self):
        t = self.preparar()
        t.listar.side_effect = RuntimeError("segredo não deve aparecer")
        self.ciclo(); self.ciclo()
        self.assertEqual(1, t.listar.call_count)
        self.assertNotIn("segredo", self.c.online.status()["fontes"][0]["erro"])

    def test_expiracao_bloqueia_ingestao_e_publicacao(self):
        t = self.preparar()
        self.registry["fontes"][0]["valido_ate"] = "2000-01-01T00:00:00+00:00"
        self.gravar(); self.ciclo()
        t.baixar.assert_not_called()
        self.assertFalse(self.c.autorizado(self.c.config()["fontes"][-1]))

    def test_live_nao_terminada_nao_vira_download(self):
        t = self.preparar()
        t.listar.return_value[0]["live_status"] = "is_live"
        self.ciclo()
        t.baixar.assert_not_called()
        self.assertEqual([], self.c.online.status()["episodios"])

    def test_sem_destino_ativo_nao_busca(self):
        t = self.preparar()
        self.cfg["canais"][0]["ativo"] = False
        self.save(); self.ciclo()
        t.listar.assert_not_called(); t.baixar.assert_not_called()

    def test_plataforma_fora_do_escopo_nao_baixa(self):
        t = self.preparar()
        self.registry["fontes"][0]["plataformas"] = ["tiktok"]
        self.gravar(); self.ciclo()
        t.baixar.assert_not_called()

    def test_fila_cheia_nao_baixa(self):
        t = self.preparar()
        self.post()
        self.cfg["max_fontes_pendentes"] = 1
        self.save(); self.ciclo()
        t.baixar.assert_not_called()

    def test_cota_diaria_limita_inclusive_falhas(self):
        t = self.preparar()
        self.registry["max_downloads_dia"] = 1
        self.gravar()
        t.baixar.side_effect = RuntimeError("rede")
        self.ciclo()
        self.c.banco.x("UPDATE descobertas SET proxima=0")
        self.ciclo()
        self.assertEqual(1, t.baixar.call_count)
        self.assertEqual([], list(self.c.online.entrada.glob("download-*")))

    def test_channel_id_divergente_nao_entra_na_esteira(self):
        t = self.preparar()
        def outro(f, v, pasta, cfg):
            p = pasta/"video.mp4"; p.write_bytes(b"conteudo")
            return p, {"channel_id": "UC"+"b"*22}
        t.baixar.side_effect = outro
        self.ciclo(); self.c.descobrir(self.c.config())
        self.assertEqual([], self.c.banco.q("SELECT * FROM fontes"))
        self.assertEqual("erro", self.c.online.status()["episodios"][0]["estado"])

    def test_revogacao_durante_download_nao_ingere(self):
        t = self.preparar()
        anterior = t.baixar.side_effect
        def revogar(*args):
            retorno = anterior(*args)
            self.registry["fontes"][0]["direitos"] = "pendente"
            self.gravar()
            return retorno
        t.baixar.side_effect = revogar
        self.ciclo()
        self.assertEqual([], list(self.c.online.entrada.rglob("*.mp4")))

    def test_armazenamento_cheio_nao_baixa(self):
        t = self.preparar()
        self.registry["max_armazenamento_mb"] = 0
        self.gravar(); self.ciclo()
        t.baixar.assert_not_called()

    def test_config_pessoal_preservada(self):
        self.preparar()
        antes = (self.root/"criador.json").read_bytes()
        self.ciclo()
        self.assertEqual(antes, (self.root/"criador.json").read_bytes())

    def test_prefixo_reservado_rejeita_sobreposicao(self):
        self.preparar()
        self.cfg["fontes"][0]["id"] = "online-cariani-monitor"
        self.save()
        with self.assertRaises(ValueError): self.c.config()

    def test_status_detecta_outro_trabalhador_pela_trava(self):
        self.assertTrue(self.c._lock())
        self.addCleanup(self.c._lockfile.close)
        outra = type(self.c)(self.app)
        self.assertTrue(outra.status()["trabalhador"])
        self.c._lockfile.close(); self.c._lockfile = None
        self.assertFalse(outra.status()["trabalhador"])

    def test_urls_e_ids_hostis_rejeitados(self):
        for url in ("https://www.youtube.com.evil/@foo/videos", "http://www.youtube.com/@foo/videos",
                    "https://www.youtube.com/@foo/videos?x=1", "file:///c:/foo"):
            with self.assertRaises(ValueError): url_canal(url)
        t = self.preparar()
        t.listar.return_value[0]["id"] = "../../arquivo"
        self.ciclo(); t.baixar.assert_not_called()

    def test_filtro_confere_canal_e_live_antes_de_midia(self):
        self.preparar()
        f = self.registry["fontes"][0]
        captured = {}
        class YDL:
            def __init__(self, opts): captured.update(opts)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, *args, **kwargs): return None
        with patch("yt_dlp.YoutubeDL", YDL):
            with self.assertRaises(ValueError):
                YouTube().baixar(f, "a"*11, self.out, self.c.config())
        filtro = captured["match_filter"]
        bom = {"channel_id": f["channel_id"], "duration": 300}
        self.assertIsNone(filtro(bom))
        self.assertIsNotNone(filtro({**bom, "channel_id": "UC"+"b"*22}))
        self.assertIsNotNone(filtro({**bom, "live_status": "is_live"}))
        self.assertIsNotNone(filtro({**bom, "duration": float("nan")}))
        self.assertIsNotNone(filtro({**bom, "duration": 8000}))


if __name__ == "__main__": unittest.main()
