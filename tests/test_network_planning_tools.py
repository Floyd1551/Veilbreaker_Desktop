import json
import math
import unittest

from veilbreaker.engineering_tools import calculate
from veilbreaker.engineering_diagrams import diagram_data
from veilbreaker.tool_registry import build_registry, search_registry


class NetworkPlanningToolsTests(unittest.TestCase):
    def test_serialization_delay_includes_only_entered_wire_overhead(self):
        result=calculate('serialization_delay',{'frame_bytes':1518,'wire_overhead':20,'link_rate':100})
        self.assertAlmostEqual(result['outputs']['Frame serialization delay (µs)'],121.44)
        self.assertAlmostEqual(result['outputs']['Wire occupancy per frame (µs)'],123.04)
        self.assertAlmostEqual(result['outputs']['Ideal maximum frame rate (frames/s)'],100e6/(1538*8))
        self.assertIn('not measured',result['limitations'].lower())

    def test_tcp_window_ceiling_uses_actual_effective_inflight_window(self):
        result=calculate('tcp_window_rate',{'window':16000,'rtt':5,'path_rate':100})
        self.assertAlmostEqual(result['outputs']['Window-limited rate (Mbit/s)'],25.6)
        self.assertAlmostEqual(result['outputs']['Combined upper bound (Mbit/s)'],25.6)
        result=calculate('tcp_window_rate',{'window':64000,'rtt':5,'path_rate':50})
        self.assertEqual(result['outputs']['Combined upper bound (Mbit/s)'],50)
        self.assertIn('not a throughput prediction',result['limitations'].lower())

    def test_latency_budget_sums_independent_one_way_assumptions(self):
        result=calculate('latency_budget',{'propagation':10,'serialization':1,'switching':2,'queueing':3,'processing':4})
        self.assertEqual(result['outputs']['One-way budget (ms)'],20)
        self.assertIn('one-way',result['limitations'].lower())

    def test_battery_runtime_uses_loss_and_reserve_once(self):
        result=calculate('battery_runtime',{'energy':1000,'load':100,'efficiency':80,'reserve':25})
        self.assertEqual(result['outputs']['Available output energy (Wh)'],600)
        self.assertEqual(result['outputs']['Estimated runtime (hours)'],6)
        self.assertIn('not measured',result['limitations'].lower())

    def test_search_diagrams_and_invalid_inputs(self):
        inputs={
          'serialization_delay':{'frame_bytes':1518,'wire_overhead':20,'link_rate':100},
          'tcp_window_rate':{'window':16000,'rtt':5,'path_rate':100},
          'latency_budget':{'propagation':10,'serialization':1,'switching':2,'queueing':3,'processing':4},
          'battery_runtime':{'energy':1000,'load':100,'efficiency':80,'reserve':25},
        }
        for key,values in inputs.items():
            with self.subTest(key=key):
                result=calculate(key,values)
                self.assertEqual(result['kind'],'calculated estimate')
                self.assertEqual(len(diagram_data(result)['stages']),3)
                json.dumps(result,allow_nan=False)
        records=build_registry()
        for query,key in [('serialization delay','serialization_delay'),('tcp window throughput','tcp_window_rate'),
                          ('latency budget','latency_budget'),('battery runtime','battery_runtime')]:
            self.assertIn(key,[item.target_id for item in search_registry(records,query)])
        for key,values in [('serialization_delay',dict(frame_bytes=1518,wire_overhead=20,link_rate=0)),
                           ('serialization_delay',dict(frame_bytes=1.5,wire_overhead=20,link_rate=100)),
                           ('tcp_window_rate',dict(window=16000,rtt=0,path_rate=100)),
                           ('latency_budget',dict(propagation=-1,serialization=1,switching=2,queueing=3,processing=4)),
                           ('battery_runtime',dict(energy=1000,load=0,efficiency=80,reserve=25)),
                           ('battery_runtime',dict(energy=1000,load=100,efficiency=math.nan,reserve=25))]:
            with self.subTest(key=key),self.assertRaises(ValueError):calculate(key,values)
