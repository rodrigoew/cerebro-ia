"""Configuração inicial e diagnóstico, sem iniciar contas de e-mail ou o aplicativo inteiro."""
from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from criador import Criador
from publicacao import Buffer, guardar_segredo


def main():
    parser = argparse.ArgumentParser(description="Núcleo: YouTube e TikTok")
    parser.add_argument("acao", choices=["status","temas","fontes","limpeza","buscar","diagnostico","segredo","conexoes","reconciliar","testar-rascunho","catalogo","importar-catalogo","autonomia"])
    parser.add_argument("--pasta", default=str(Path(__file__).resolve().parent), help="Pasta de config.json/criador.json")
    parser.add_argument("--nome", choices=["buffer_token","cloudinary_cloud","cloudinary_key","cloudinary_secret"])
    parser.add_argument("--post", type=int)
    parser.add_argument("--remoto-id")
    parser.add_argument("--arquivo", help="JSON de catálogo; nunca contém senhas.")
    parser.add_argument("--aplicar", action="store_true", help="Confirma a gravação do catálogo validado.")
    parser.add_argument("--ativar", action="store_true", help="Configura início automático por usuário no Windows.")
    parser.add_argument("--desativar", action="store_true", help="Remove o início automático sem encerrar o aplicativo aberto.")
    args = parser.parse_args()
    if args.acao == "segredo":
        if not args.nome:
            parser.error("Informe --nome. O valor será solicitado sem aparecer na tela.")
        valor = getpass.getpass("Valor: ").strip()
        if not valor:
            parser.error("Valor vazio.")
        guardar_segredo(args.nome, valor)
        print("Guardado no cofre do sistema.")
        return
    pasta = Path(args.pasta).resolve()
    if args.acao == "autonomia":
        from autonomia_windows import registrar, desativar, consultar
        if args.ativar and args.desativar:
            parser.error("Escolha ativar ou desativar.")
        r = registrar(pasta) if args.ativar else desativar(pasta) if args.desativar else consultar(pasta)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    if args.acao in ("catalogo", "importar-catalogo"):
        from catalogo_criador import carregar, importar
        from fontes_auto import CATALOGO
        if args.acao == "catalogo":
            r = carregar(pasta, CATALOGO)
        else:
            if not args.arquivo:
                parser.error("Informe --arquivo com o catálogo completo.")
            r = importar(pasta, args.arquivo, CATALOGO, args.aplicar)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    app_config = pasta / "config.json"
    cfg = json.loads(app_config.read_text(encoding="utf-8-sig")) if app_config.exists() else {}
    app = SimpleNamespace(caminho_cfg=app_config, saida=pasta/cfg.get("pasta_saida","saida"),cfg=cfg)
    criador = Criador(app)
    if args.acao == "status":
        r = criador.status()
    elif args.acao == "fontes":
        r = criador.online.status()
    elif args.acao == "limpeza":
        r = {**criador.limpeza.status(criador.config()), "plano": criador.limpeza.plano(criador.config()),
             "aviso": "Consulta apenas; este comando não exclui arquivos."}
    elif args.acao == "buscar":
        # A mesma trava impede dois processos de baixar o mesmo episódio.
        if not criador._lock():
            parser.error("O aplicativo já está cuidando da busca. Consulte fontes ou status.")
        try:
            cfg = criador.config()
            if not cfg["ativo"]:
                parser.error("Criador desativado no criador.json.")
            criador.online.ciclo(cfg)
            criador.descobrir(criador.config())
            r = criador.online.status()
        finally:
            criador._lockfile.close()
            criador._lockfile = None
    elif args.acao == "testar-rascunho":
        if not args.post:
            parser.error("Informe --post com o ID de um único corte pronto.")
        try:
            r = criador.testar_rascunho(args.post)
        except Exception as erro:
            print(json.dumps({"ok":False,"erro":str(erro)},ensure_ascii=False,indent=2))
            raise SystemExit(1)
    elif args.acao == "temas":
        r = criador.analise()
    elif args.acao == "diagnostico":
        import cortes
        try:
            ffmpeg = cortes._ffmpeg()
        except RuntimeError as erro:
            ffmpeg = str(erro)
        r = {"ffmpeg":ffmpeg,"cloudinary_instalado":importlib.util.find_spec("cloudinary") is not None,
             "config_existe":criador.config_path.is_file(),"config":criador.config(),
             "aviso":"Não inicia uploads nem testa serviços pagos."}
    elif args.acao == "conexoes":
        pub = Buffer()
        r = pub.graphql("query { account { organizations { id name } } }",{})
        for org in r["account"]["organizations"]:
            org["canais"] = pub.graphql("""query($input: ChannelsInput!) {
              channels(input: $input) { id name service isDisconnected }
            }""",{"input":{"organizationId":org["id"]}})["channels"]
    else:
        if not args.post or not args.remoto_id:
            parser.error("Informe --post e --remoto-id depois de conferir o post no Buffer.")
        post = criador.banco.q("SELECT * FROM posts WHERE id=?",(args.post,))
        if not post or post[0]["estado"] != "verificar_envio":
            parser.error("Post não está aguardando reconciliação.")
        remoto = Buffer().consultar(args.remoto_id)
        criador.banco.x("UPDATE posts SET remoto_id=?,estado=? WHERE id=?",
            (remoto["id"],"publicado" if remoto["status"]=="sent" else "agendado",args.post))
        r = {"ok":True,"mensagem":"Envio associado; não foi criado outro post."}
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
