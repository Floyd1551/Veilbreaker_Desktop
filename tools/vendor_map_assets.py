"""Reproduce bundled map dependencies; run only during development."""
import concurrent.futures,hashlib,io,json,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'src/veilbreaker/assets/maps'
ASSET_REV='028c18f713baecad011301ff7a69acc39bcc2ae7'
PACKAGES=[('maplibre-gl','5.12.0',{'dist/maplibre-gl-csp.js':'maplibre.js','dist/maplibre-gl-csp-worker.js':'maplibre-worker.js','dist/maplibre-gl.css':'maplibre.css','LICENSE.txt':'MAPLIBRE-LICENSE.txt'}),('pmtiles','4.5.0',{'dist/pmtiles.js':'pmtiles.js','@license':'PMTILES-LICENSE.txt'}),('@protomaps/basemaps','5.7.2',{'dist/basemaps.js':'basemaps.js','@license':'BASEMAPS-LICENSE.txt'})]
def get(url):
    with urllib.request.urlopen(url,timeout=60) as r:return r.read()
def main():
    ROOT.mkdir(parents=True,exist_ok=True);entries=[]
    def write(name,data,source):
        p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        return dict(file=name,source=source,sha256=hashlib.sha256(data).hexdigest())
    for package,version,files in PACKAGES:
        meta=json.loads(get('https://registry.npmjs.org/'+package+'/'+version));url=meta['dist']['tarball'];raw=get(url)
        import base64
        expected=meta['dist']['integrity'];assert expected=='sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode()
        archive=tarfile.open(fileobj=io.BytesIO(raw))
        for source,name in files.items():
            if source=='@license':
                repo='PMTiles' if package=='pmtiles' else 'basemaps'
                source_url='https://raw.githubusercontent.com/protomaps/'+repo+'/'+meta['gitHead']+('/LICENSE' if package=='pmtiles' else '/LICENSE.md')
                data=get(source_url)
            else:
                source_url=url+'#package/'+source;data=archive.extractfile('package/'+source).read()
            entries.append(write(name,data,source_url))
    tree=json.loads(get('https://api.github.com/repos/protomaps/basemaps-assets/git/trees/'+ASSET_REV+'?recursive=1'))
    selected=[x['path'] for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith(('fonts/Noto Sans Regular/','fonts/Noto Sans Medium/','fonts/Noto Sans Italic/','sprites/v4/dark')) or x['path']=='fonts/OFL.txt')]
    hashes={x['path']:x['sha'] for x in tree['tree']}
    def asset(path):
        url='https://raw.githubusercontent.com/protomaps/basemaps-assets/'+ASSET_REV+'/'+urllib.parse.quote(path)
        p=ROOT/path
        data=p.read_bytes() if p.exists() else get(url)
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==hashes[path], 'Upstream asset hash mismatch: '+path
        return write(path,data,url)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:entries.extend(pool.map(asset,selected))
    from PySide6.QtCore import QFile,QIODevice
    from PySide6.QtWebChannel import QWebChannel
    f=QFile(':/qtwebchannel/qwebchannel.js');assert f.open(QIODevice.OpenModeFlag.ReadOnly)
    entries.append(write('qwebchannel.js',bytes(f.readAll()),'PySide6 6.11.2 QtWebChannel bundled resource'))
    (ROOT/'manifest.json').write_text(json.dumps(dict(packages=[dict(name=p,version=v) for p,v,_ in PACKAGES],assets_revision=ASSET_REV,files=entries),indent=2)+'\n',encoding='utf-8')
    print('Vendored',len(entries),'assets')
if __name__=='__main__':main()
