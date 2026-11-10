"""Small interactive entry point for the ForgeLoader development tools."""
from pathlib import Path
from krmodkit import new_mod, discover, load_order, ModError

ROOT = Path(__file__).resolve().parents[1]


def main():
    print('ForgeLoader Dev Kit — projetos e validacao offline')
    print('O carregador de scripts dentro do jogo ainda esta em desenvolvimento.\n')
    while True:
        print('1. Criar projeto Lua\n2. Conferir exemplos\n3. Conferir MeusMods\n0. Sair')
        choice = input('Escolha: ').strip()
        if choice == '0': return
        try:
            if choice == '1':
                ident = input('ID (exemplo: meuautor.meumod): ').strip()
                name = input('Nome: ').strip()
                shared = input('Altera regras da partida? [s/N]: ').strip().lower() == 's'
                folder = ROOT / 'MeusMods' / ident
                new_mod(folder, ident, name, shared)
                print(f'Projeto criado em: {folder}\n')
            elif choice in ('2', '3'):
                folder = ROOT / ('modkit/examples/lua' if choice == '2' else 'MeusMods')
                mods = discover(folder)
                print('Manifestos validos. Ordem: ' + ', '.join(load_order(mods)))
            else: print('Escolha uma opcao da lista.')
        except (ModError, OSError) as error:
            print(f'Nao foi possivel: {error}\n')


if __name__ == '__main__':
    try: main()
    except (KeyboardInterrupt, EOFError): pass
