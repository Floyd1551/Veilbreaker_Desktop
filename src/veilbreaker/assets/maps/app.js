'use strict';
let map, bridge, model, selected=null, generation=0;
const base=new URL('.',location.href).href;
const notice=document.getElementById('notice');
const empty=()=>({type:'FeatureCollection',features:[]});
maplibregl.setWorkerUrl(base+'maplibre-worker.js');
const protocol=new pmtiles.Protocol();maplibregl.addProtocol('pmtiles',protocol.tile);
function fit(){if(map&&model.bounds){const b=model.bounds;map.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:65,maxZoom:17,duration:0});}}
function circle(feature){
 const radius=feature.properties.horizontal_accuracy_m;
 if(typeof radius!=='number'||radius<0||radius>100000)return empty();
 const [lon,lat]=feature.geometry.coordinates,rad=Math.PI/180,d=radius/6371008.8,p=lat*rad,l=lon*rad,coords=[];
 for(let i=0;i<=64;i++){const bearing=i/64*2*Math.PI,p2=Math.asin(Math.sin(p)*Math.cos(d)+Math.cos(p)*Math.sin(d)*Math.cos(bearing));const l2=l+Math.atan2(Math.sin(bearing)*Math.sin(d)*Math.cos(p),Math.cos(d)-Math.sin(p)*Math.sin(p2));coords.push([l2/rad,p2/rad]);}
 return {type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[coords]}}]};
}
function highlight(id){
 selected=id;if(!map||!map.getSource('accuracy'))return;
 const f=model.features.features.find(f=>f.id===id);
 map.setFilter('selected',['==',['get','id'],id]);map.getSource('accuracy').setData(f?circle(f):empty());
 if(f&&f.properties.horizontal_accuracy_m>100000)notice.textContent='Reported accuracy exceeds 100 km; uncertainty circle omitted.';
}
function install(){
 map.addSource('measurements',{type:'geojson',data:model.features});map.addSource('accuracy',{type:'geojson',data:empty()});
 map.addLayer({id:'uncertainty',type:'fill',source:'accuracy',paint:{'fill-color':'#63dec8','fill-opacity':0.18}});
 map.addLayer({id:'uncertainty-border',type:'line',source:'accuracy',paint:{'line-color':'#63dec8','line-width':1}});
 map.addLayer({id:'points',type:'circle',source:'measurements',paint:{'circle-radius':7,'circle-color':['case',['==',['get','label',['get','quality']],'Qualified fix'],'#63dec8','#f3ad54'],'circle-stroke-width':2,'circle-stroke-color':'#101722'}});
 map.addLayer({id:'selected',type:'circle',source:'measurements',filter:['==',['get','id'],''],paint:{'circle-radius':11,'circle-color':'transparent','circle-stroke-width':3,'circle-stroke-color':'#ffffff'}});
 map.on('click','points',e=>{if(e.features.length)bridge.selectFeature(String(e.features[0].properties.id));});
 map.on('mouseenter','points',()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave','points',()=>map.getCanvas().style.cursor='');
 fit();if(selected)highlight(selected);bridge.ready();window.veilbreakerMap=map;
}
async function refresh(){
 const epoch=++generation;
 try{
  const response=await fetch(base+'model.json');if(!response.ok)throw Error('Local evidence unavailable');const next=await response.json();if(epoch!==generation)return;model=next;
  if(map)map.remove();
  const style={version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#152333'}}]};
  if(model.pack){
   style.sources.basemap={type:'vector',tiles:['pmtiles://'+base+'pack.pmtiles/{z}/{x}/{y}'],minzoom:model.pack.minzoom,maxzoom:model.pack.maxzoom};
   style.glyphs=base+'fonts/{fontstack}/{range}.pbf';style.sprite=base+'sprites/v4/dark';
   style.layers=basemaps.layers('basemap',basemaps.namedFlavor('dark'),{lang:'en'});
  }
  notice.textContent=(model.pack?'Offline basemap · '+model.pack.name:'Basemap unavailable · Coordinate-only view')+(model.features.features.length?'':' · No plottable fixes in this view');
  map=new maplibregl.Map({container:'map',style,center:[-98,39],zoom:3,attributionControl:false,renderWorldCopies:false});
  map.addControl(new maplibregl.NavigationControl(),'top-right');
  map.addControl(new maplibregl.AttributionControl({customAttribution:'Receiver positions · GPS quality evidence',compact:false}));
  map.on('error',()=>{notice.textContent='Basemap or rendering error · GPS evidence remains in the point list';bridge.failed('local basemap or rendering error');});
  map.on('load',install);
 }catch(e){notice.textContent='Map unavailable · '+e.message;bridge.failed(String(e.message));}
}
new QWebChannel(qt.webChannelTransport,channel=>{bridge=channel.objects.bridge;bridge.refresh.connect(refresh);bridge.fit.connect(fit);bridge.highlight.connect(highlight);refresh();});
