"""Validate supported PMTiles headers before exposing a local archive."""
import json
from pathlib import Path
import struct
import zlib

MAX_METADATA=1024*1024

def signature(path):
    s=Path(path).stat()
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)

def inspect_pack(path):
    path=Path(path);before=signature(path)
    with path.open('rb') as stream:
        header=stream.read(127)
        if len(header)!=127 or header[:8]!=b'PMTiles\x03': raise ValueError('Choose a PMTiles version 3 archive.')
        offsets=struct.unpack_from('<8Q',header,8)
        for offset,length in zip(offsets[::2],offsets[1::2]):
            if length and (offset<127 or offset+length>before[2]):raise ValueError('Map archive is truncated or has invalid offsets.')
        if not offsets[1] or offsets[0]+offsets[1]>16384:raise ValueError('Invalid PMTiles root directory.')
        if header[97] not in (1,2) or header[98] not in (1,2) or header[99]!=1:raise ValueError('Use vector tiles with uncompressed or gzip compression.')
        if header[100]>header[101] or header[101]>26:raise ValueError('Unsupported map zoom range.')
        if not 0<offsets[3]<=MAX_METADATA:raise ValueError('Map metadata exceeds the supported size.')
        stream.seek(offsets[2]);data=stream.read(offsets[3])
        if header[97]==2:
            try:
                decoder=zlib.decompressobj(31);data=decoder.decompress(data,MAX_METADATA+1)
                if len(data)>MAX_METADATA or not decoder.eof:raise ValueError('Map metadata is oversized or truncated.')
            except zlib.error as exc:raise ValueError('Invalid map metadata compression.') from exc
        try: meta=json.loads(data)
        except (ValueError,UnicodeError) as exc:raise ValueError('Invalid map metadata.') from exc
        layers=meta.get('vector_layers') if isinstance(meta,dict) else None
        if not isinstance(layers,list) or not {'water','roads','buildings'}.issubset({x.get('id') for x in layers if isinstance(x,dict)}):
            raise ValueError('This map uses an unsupported schema. Select a Protomaps basemap archive.')
        attribution=meta.get('attribution')
        if not isinstance(attribution,str) or not attribution.strip():raise ValueError('Map attribution is missing; obtain a pack with source attribution.')
    if before!=signature(path):raise ValueError('Map changed while opening; select it again.')
    return dict(name=str(meta.get('name') or path.name)[:500],attribution=attribution[:4000],size=before[2],signature=before,
                minzoom=header[100],maxzoom=header[101],schema='Protomaps',path=str(path.resolve()))
