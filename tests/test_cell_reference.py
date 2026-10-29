import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from veilbreaker import cell_reference as ref

HEADER='radio,mcc,net,area,cell,unit,lon,lat,range,samples,changeable,created,updated,averageSignal\n'
ROW='LTE,311,480,42,12345,10,-96.8,32.8,1000,15,1,1600000000,1700000000,0\n'
META=dict(source='OpenCellID',license='CC BY-SA 4.0',date='2026-10-20')

class ReferenceTests(unittest.TestCase):
    def test_headerless_country_export_and_nr_full_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'refs';source=Path(temp)/'311.csv'
            nr='NR,311,480,16777214,55341514827,-1,-86.5,34.7,1000,5,1,1600000000,1700000000,0\n'
            source.write_text(ROW+nr,encoding='utf-8')
            result=ref.import_reference(root,source,META,lambda:False,lambda _:None)
            self.assertEqual(result['accepted'],2)
            self.assertEqual(result['unsupported'],0)
            self.assertEqual(result['coverage']['radio_counts'], {'LTE':1, 'NR':1})
            self.assertEqual(result['coverage']['mccs'], [311])
            self.assertEqual(result['coverage']['bounds'], [-96.8, 32.8, -86.5, 34.7])
            ref.activate_reference(root,result['dataset_id'])
            self.assertEqual(len(ref.lookup_reference(root,('NR',311,480,16777214,55341514827))),1)

    def test_headerless_export_rejects_unknown_first_row(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'wrong.csv'
            source.write_text('not,a,valid,export\n'+ROW,encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'header|first row'):
                ref.import_reference(Path(temp)/'refs',source,META,lambda:False,lambda _:None)

    def test_import_lookup_conflict_and_cancel(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'refs'; source=Path(temp)/'cells.csv.gz'
            source.write_bytes(gzip.compress((HEADER+ROW+ROW.replace('-96.8','-96.9')).encode()))
            imported=ref.import_reference(root,source,META,lambda:False,lambda _:None)
            ref.activate_reference(root,imported['dataset_id'])
            self.assertEqual(len(ref.lookup_reference(root,('LTE',311,480,42,12345))),2)
            self.assertEqual(ref.lookup_reference(root,('LTE',311,480,43,12345)),[])
            with self.assertRaisesRegex(ValueError,'cancel'):
                ref.import_reference(root,source,META,lambda:True,lambda _:None)
            self.assertEqual(ref.active_reference(root)['dataset_id'],imported['dataset_id'])
            self.assertEqual(ref.import_reference(root,source,META,lambda:False,lambda _:None)['dataset_id'],imported['dataset_id'])

    def test_invalid_gzip_limits_and_empty_preserve_active(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'refs'; source=Path(temp)/'cells.csv'
            source.write_text(HEADER+ROW)
            imported=ref.import_reference(root,source,META,lambda:False,lambda _:None)
            ref.activate_reference(root,imported['dataset_id'])
            source.write_text(HEADER+ROW.replace('12345','268435456'))
            with self.assertRaises(ValueError):ref.import_reference(root,source,META,lambda:False,lambda _:None)
            source.write_text(HEADER+ROW)
            with patch.object(ref,'MAX_BYTES',20):
                with self.assertRaises(ValueError):ref.import_reference(root,source,META,lambda:False,lambda _:None)
            broken=source.with_suffix('.gz'); broken.write_bytes(gzip.compress((HEADER+ROW).encode())[:-6])
            with self.assertRaises((ValueError,EOFError)):
                ref.import_reference(root,broken,META,lambda:False,lambda _:None)
            self.assertEqual(ref.active_reference(root)['dataset_id'],imported['dataset_id'])

    def test_operator_nr_and_key_validation(self):
        row=dict(radio='NR',mcc='311',mnc='048',tac=100000,cell_id='34359738369',lon=-97,lat=33,
                 source='Site owner',verification='operator-entered')
        self.assertEqual(ref.identity_key(row),('NR',311,48,100000,34359738369))
        for field,value in [('cell_id',True),('tac',-1),('mcc',0),('cell_id',68719476736)]:
            with self.assertRaises(ValueError):ref.identity_key(dict(row,**{field:value}))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'refs'; source=Path(temp)/'sites.json'
            source.write_text(json.dumps(dict(schema_version=1,records=[row])))
            result=ref.import_reference(root,source,dict(source='Operator',license='Private',date='2026-10-20'),lambda:False,lambda _:None)
            ref.activate_reference(root,result['dataset_id'])
            self.assertEqual(ref.lookup_reference(root,ref.identity_key(row))[0]['verification'],'operator-entered')

    def test_pinned_lookup_survives_active_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'refs';source=Path(tmp)/'cells.csv';source.write_text(HEADER+ROW)
            first=ref.import_reference(root,source,META,lambda:False,lambda _:None)
            ref.activate_reference(root,first['dataset_id'])
            source.write_text(HEADER+ROW.replace('-96.8','-95.0'))
            second=ref.import_reference(root,source,META,lambda:False,lambda _:None)
            ref.activate_reference(root,second['dataset_id'])
            pinned=ref.lookup_reference(root,('LTE',311,480,42,12345),first['dataset_id'])
            self.assertEqual(pinned[0]['lon'],-96.8)
