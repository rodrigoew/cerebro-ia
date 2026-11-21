import unittest
from unittest.mock import patch
import test_criador as fixtures
from publicacao import Buffer,EnvioIncerto


class RascunhoTests(unittest.TestCase):
    setUp=fixtures.EsteiraTests.setUp
    save=fixtures.EsteiraTests.save
    source=fixtures.EsteiraTests.source
    post=fixtures.EsteiraTests.post

    def preparar(self):
        self.cfg['publicar']=False;self.save()
        self.pub.agendar.return_value={'id':'rascunho1','status':'draft'}
        return self.post()

    def test_envia_somente_rascunho_e_preserva_publicar_false(self):
        post=self.preparar()
        r=self.c.testar_rascunho(post['id'])
        self.assertTrue(r['ok'])
        self.assertFalse(self.c.config()['publicar'])
        self.assertTrue(self.pub.agendar.call_args.kwargs['rascunho'])
        self.assertEqual('rascunho_teste',self.c.banco.q('SELECT estado FROM posts')[0]['estado'])

    def test_repetir_comando_nao_duplica_rascunho(self):
        post=self.preparar()
        self.c.testar_rascunho(post['id']);self.c.testar_rascunho(post['id'])
        self.pub.agendar.assert_called_once();self.host.enviar.assert_called_once()

    def test_rejeita_teste_com_publicacao_ativa(self):
        post=self.post()
        with self.assertRaises(ValueError):self.c.testar_rascunho(post['id'])
        self.host.enviar.assert_not_called()

    def test_envio_incerto_nao_repete(self):
        post=self.preparar();self.pub.agendar.side_effect=EnvioIncerto('timeout')
        with self.assertRaises(EnvioIncerto):self.c.testar_rascunho(post['id'])
        with self.assertRaises(ValueError):self.c.testar_rascunho(post['id'])
        self.pub.agendar.assert_called_once()
        self.assertEqual('verificar_envio',self.c.banco.q('SELECT estado FROM posts')[0]['estado'])

    def test_falha_hospedagem_nao_cria_post(self):
        post=self.preparar();self.host.enviar.side_effect=RuntimeError('indisponivel')
        with self.assertRaises(RuntimeError):self.c.testar_rascunho(post['id'])
        self.pub.agendar.assert_not_called()
        self.assertEqual('pronto',self.c.banco.q('SELECT estado FROM posts')[0]['estado'])

    def test_schema_draft_usa_campos_documentados(self):
        pub=Buffer('teste')
        with patch.object(pub,'graphql',return_value={'createPost':{'post':{'id':'r1','status':'draft'}}}) as mock:
            pub.agendar('canal','youtube','titulo','desc','https://example.org/a.mp4',None,{},rascunho=True)
        data=mock.call_args.args[1]['input']
        self.assertIs(data['needsApproval'],False)
        self.assertIs(data['saveToDraft'],True)
        self.assertNotIn('dueAt',data)

    def test_nao_confirma_publicacao_como_rascunho(self):
        pub=Buffer('teste')
        with patch.object(pub,'graphql',return_value={'createPost':{'post':{'id':'r1','status':'scheduled'}}}):
            with self.assertRaises(EnvioIncerto):
                pub.agendar('canal','youtube','titulo','desc','https://example.org/a.mp4',None,{},rascunho=True)
