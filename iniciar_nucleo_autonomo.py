"""Entrada da tarefa por usuário do Windows; não publica nem opera contas diretamente."""
import argparse
from pathlib import Path
from autonomia_windows import rodar

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pasta", default=str(Path(__file__).resolve().parent))
    rodar(parser.parse_args().pasta)
