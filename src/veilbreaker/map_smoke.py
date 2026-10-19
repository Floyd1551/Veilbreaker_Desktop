"""Offline source/frozen map smoke; synthetic evidence only."""
import json,os,struct,time
from pathlib import Path

def synthetic_pack():
    meta=json.dumps({'name':'Synthetic packaging fixture','attribution':'Synthetic fixture; no geographic basemap data','vector_layers':[{'id':x} for x in ('water','roads','buildings')]}).encode()
    tile=b'\x1a\x0c\x0a\x05water\x28\x80\x20\x78\x02';root=bytes([1,0,1,len(tile),1]);h=bytearray(127);h[:8]=b'PMTiles\x03'
    struct.pack_into('<8Q',h,8,127,len(root),127+len(root),len(meta),0,0,127+len(root)+len(meta),len(tile))
    h[96:102]=bytes([1,1,1,1,0,0]);struct.pack_into('<4i',h,102,-1800000000,-850000000,1800000000,850000000)
    return bytes(h)+root+meta+tile

def smoke(destination,pack_path=None):
    os.environ.setdefault('QT_QPA_PLATFORM','windows' if os.name=='nt' else 'offscreen')
    from PySide6.QtCore import Qt,QUrl
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase,QFont
    from PySide6.QtTest import QTest
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app=QApplication.instance() or QApplication([])
    if os.name=='nt':
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf');app.setFont(QFont('Segoe UI',10))
    from .gui import STYLE
    from .map_ui import MapWindow
    from .map_data import build_map_data
    app.setStyleSheet(STYLE)
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    rows=[dict(status='available',latitude_deg=32.78+i*.001,longitude_deg=-96.8+i*.001,horizontal_accuracy_m=8,fix_age_ms=300,observation_id='Observation '+str(i+1),source='phone',provider='gps') for i in range(3)]
    model=build_map_data([dict(run_id='synthetic',label='Synthetic field survey',locations=rows)])
    window=MapWindow(None,model,lambda _:None,restore_pack=False)
    fixture=destination/'synthetic.pmtiles';fixture.write_bytes(synthetic_pack());window.load_pack(pack_path or fixture,persist=False)
    window.run_filter.setCurrentIndex(1);window.show()
    def wait(check,seconds=25):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            app.processEvents();QTest.qWait(50)
            if check():return True
        return False
    def js(script):
        result=[];window.web.page().runJavaScript(script,lambda value:result.append(value));wait(lambda:bool(result),5)
        return result[0] if result else None
    report={}
    try:
        report['ready']=wait(lambda:window.ready)
        if window.web and report['ready']:
            wait(lambda:window.server.pack_reads>0)
            QTest.qWait(1800)
            report['rendered_points']=js("window.veilbreakerMap.queryRenderedFeatures({layers:['points']}).length")
            js("(()=>{const m=window.veilbreakerMap,p=m.project([-96.8,32.78]);m.fire('click',{point:p,lngLat:m.unproject(p)});return true})()")
            report['selection']=wait(lambda:window.selected is not None,5)
            report['local_pack_reads']=window.server.pack_reads
            js("window.externalBlocked=null;fetch('https://example.com/veilbreaker-map-test').then(()=>window.externalBlocked=false).catch(()=>window.externalBlocked=true);true")
            QTest.qWait(200);report['external_blocked']=js('window.externalBlocked') is True
            report['url_allowlist']=not window.interceptor.permitted(QUrl('https://example.com'))
            window.grab().save(str(destination/'map.png'))
            anti=[dict(run_id=str(lon),locations=[dict(rows[0],longitude_deg=lon,latitude_deg=0)]) for lon in (179,-179)]
            window.model=build_map_data(anti);window.run_filter.blockSignals(True);window.run_filter.setCurrentIndex(0);window.run_filter.blockSignals(False)
            window.ready=False;window.update_view();wait(lambda:window.ready);QTest.qWait(1000)
            report['antimeridian_points']=js("window.veilbreakerMap.queryRenderedFeatures({layers:['points']}).length")
        report['status']=window.renderer_status.text()
        report['passed']=bool('unavailable' not in report['status'].lower() and report.get('ready') and report.get('rendered_points',0)>=3 and report.get('selection') and report.get('local_pack_reads',0)>0 and report.get('external_blocked') and report.get('url_allowlist') and report.get('antimeridian_points',0)>=2)
    finally:
        window.close();app.processEvents()
    (destination/'map-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1
