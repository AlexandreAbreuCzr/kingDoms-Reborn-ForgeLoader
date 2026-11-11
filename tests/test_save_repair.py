import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('repair_save_players',ROOT/'tools/repair_save_players.py')
save=importlib.util.module_from_spec(spec);sys.modules[spec.name]=save;spec.loader.exec_module(save)


def s(text):
    if not text:return struct.pack('<i',0)
    value=text.encode('cp1252')+b'\0'
    return struct.pack('<i',len(value))+value


def record(name='', steam=save.EMPTY_STEAM, slot=-1):
    return struct.pack('<IbI',0,-1,bool(name))+(s(name) if name else b'')+struct.pack('<Qi',steam,slot)+bytes(36)+s('')+bytes(8)


def metadata(rows, date=200, ticks=500, seed='123456789', version=214240322, single=False):
    settings=struct.pack('<q',5)+s(seed)+struct.pack('<i4BIiiBIII',1,2,3,4,5,1,3,1,2,1,1,int(single))
    return struct.pack('<II',version,len(rows))+b''.join(rows)+s('City')+struct.pack('<qii',date,ticks,20)+settings+struct.pack('<iIiIiB',1,0xabcd1234,1,4,1,1)


class RepairTests(unittest.TestCase):
    host=record('Host',123,0);friend=record('Parceiro',456,1)

    def pair(self,folder,**donor_options):
        target,donor=folder/'target',folder/'previous'
        target.mkdir();donor.mkdir()
        (target/'MetaData.dat').write_bytes(metadata([self.host,record()]))
        (target/'GameData0.dat').write_bytes(b'data')
        (donor/'MetaData.dat').write_bytes(metadata([self.host,self.friend],**{'date':100,**donor_options}))
        return target,donor

    def test_copy_only_rewrites_metadata_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target,donor=self.pair(root);out=root/'Reparado';before=save.fingerprint(target)
            self.assertEqual(save.repair(target,donor,out),[1]);self.assertEqual(save.fingerprint(target),before)
            self.assertEqual(save.load(out).players[1].steam_id,456)
            self.assertEqual((out/'GameData0.dat').read_bytes(),b'data')
            with self.assertRaises(save.SaveError):save.repair(target,donor,out)

    def test_wrong_world_newer_save_and_wrong_version_are_refused(self):
        for settings in ({'seed':'another-map'},{'date':300},{'ticks':501},{'version':253260211},{'single':True},{'seed':''}):
            with self.subTest(settings=settings),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);target,donor=self.pair(root,**settings);out=root/'Reparado'
                with self.assertRaises(save.SaveError):save.repair(target,donor,out)
                self.assertFalse(out.exists())

    def test_donor_must_share_existing_player_and_never_duplicate_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target,donor=self.pair(root)
            (donor/'MetaData.dat').write_bytes(metadata([record('Different',999,0),self.friend],date=100))
            with self.assertRaises(save.SaveError):save.plan(target,donor)
            (target/'MetaData.dat').write_bytes(metadata([self.host,record(),record('Parceiro',456,2)]))
            (donor/'MetaData.dat').write_bytes(metadata([self.host,self.friend,record()],date=100))
            self.assertEqual(save.plan(target,donor)[1],{})


if __name__=='__main__':unittest.main()
