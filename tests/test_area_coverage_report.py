import unittest
from veilbreaker.area_coverage_report import report_html


class AreaCoverageReportTests(unittest.TestCase):
    def test_report_keeps_status_provenance_sample_and_escapes_input(self):
        model={'bounds':[-87.2,34.3,-86.2,35.2], 'checked_utc':'2026-10-29T09:00:00Z',
               'map':{'status':'bounds contain area','note':'Map bounds only','packs':[{'name':'<map>','source_date':'2026','attribution':'OpenStreetMap'}]},
               'terrain':{'status':'bounds cover area','note':'No-data may remain','gaps':[],
                  'packs':[{'name':'DEM','source':'USGS','source_date':'2026','sha256':'abc'}],
                  'sample':{'status':'sampled','grid_size':11,'total':121,'valid':120,'missing':1,'outside':0,'nodata':1,
                            'datums':['NAVD88'],'units':['m'],'compatible':True,'note':'Sparse grid only','examples':[[-86.5,34.7]]}},
               'cell':{'status':'records found','count':1,'note':'Estimated cells','source':'OpenCellID','date':'Unknown',
                       'attribution':'CC BY-SA','groups':[{'radio':'LTE','mcc':311,'mnc':480,'count':1}]},
               'structures':{'status':'no structure extent overlaps','note':'No verified tower association','packs':[]}}
        html=report_html(model)
        for expected in ('&lt;map&gt;','USGS','Sparse grid only','120','121','311','480','No verified tower'):
            self.assertIn(expected,html)
        self.assertIn('2026-10-29T09:00:00Z',html)
        self.assertIn('Checked (UTC)',html)
        self.assertNotIn('<map>',html)
        self.assertNotIn('complete coverage',html.lower())

    def test_report_handles_absent_samples_and_cells(self):
        model={'bounds':[0,0,1,1], 'map':{'status':'none','note':'Map note','packs':[]},
               'terrain':{'status':'none','note':'Terrain note','packs':[]},
               'cell':{'status':'no active cell reference','count':None,'note':'Cell note','groups':[]},
               'structures':{'status':'none','note':'Structure note','packs':[]}}
        self.assertIn('No terrain sampling requested',report_html(model))


if __name__=='__main__': unittest.main()
