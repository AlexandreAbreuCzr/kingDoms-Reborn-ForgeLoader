"""Install the real .flmod format with the player PowerShell entry point."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell required')
class ModInstallerTests(unittest.TestCase):
    def run_installer(self, game, package, okay=True):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'installer/Install-Mod.ps1'),
                                 '-GamePath', str(game), '-Package', str(package), '-NoUI'], capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0 if okay else 1, result.stdout + result.stderr)
        return result

    def fixture(self, root, extra=None, **changes):
        game=root/'game'; dll=game/'PunCity/Binaries/Win64/KingdomsPortraits.dll';dll.parent.mkdir(parents=True, exist_ok=True);dll.write_bytes(b'fixture')
        example=ROOT/'modkit/examples/forgeloader/forge.hello'
        m=json.loads((example/'mod.json').read_text());m.update(changes)
        archive=root/'example.flmod'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('mod.json',json.dumps(m));z.writestr('Scripts/main.lua',(example/'Scripts/main.lua').read_bytes())
            if extra:z.writestr(*extra)
        return game, archive

    def test_real_example_and_existing_mod_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            game, package=self.fixture(Path(folder))
            result=json.loads(self.run_installer(game,package).stdout)
            self.assertEqual(result['id'],'forge.hello')
            script=game/'Mods/forge.hello/Scripts/main.lua';original=script.read_bytes()
            self.run_installer(game,package,False)
            self.assertEqual(script.read_bytes(),original)

    def test_traversal_collision_other_runtime_and_required_mod_refused(self):
        cases=[({'extra':('../outside.txt','bad')},'traversal'),({'extra':('scripts/MAIN.lua','bad')},'collision'),
               ({'runtime':'ue4ss-lua'},'runtime'),({'multiplayer':'required'},'multiplayer'),({'extra':('NUL.txt','bad')},'device')]
        for options, name in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);game,package=self.fixture(root,**options)
                self.run_installer(game,package,False)
                self.assertFalse((game/'Mods/forge.hello').exists())
                self.assertFalse((root/'outside.txt').exists())

if __name__ == '__main__':unittest.main()
