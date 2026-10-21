"""Self-contained terrain profile visualization and report section."""
import base64
from .survey_report import text,table


def profile_png(profile):
    if not profile.get('line_m'):return None
    from PySide6.QtCore import Qt,QPointF,QRectF,QBuffer,QIODevice
    from PySide6.QtGui import QImage,QPainter,QColor,QPen,QFont,QPolygonF
    width,height=1100,440;left,right,top,bottom=85,1070,50,365
    image=QImage(width,height,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    values=profile['terrain_effective_m']+profile['line_m']
    low,high=min(values),max(values);padding=max(5,(high-low)*.15);low-=padding;high+=padding
    length=profile['distances_m'][-1]
    def point(x,y):return QPointF(left+x/length*(right-left),bottom-(y-low)/(high-low)*(bottom-top))
    painter=QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setFont(QFont('Arial',10));painter.setPen(QColor('#172131'))
        painter.drawText(85,23,'Terrain profile — conditional on selected endpoint and antenna heights')
        for i in range(6):
            x=length*i/5;y=low+(high-low)*i/5
            painter.setPen(QColor('#d6dfe4'));painter.drawLine(point(0,y),point(length,y))
            painter.setPen(QColor('#172131'));painter.drawText(QRectF(5,point(0,y).y()-8,72,20),Qt.AlignmentFlag.AlignRight,f'{y:.1f} m')
            painter.drawText(QRectF(point(x,low).x()-32,bottom+8,80,20),Qt.AlignmentFlag.AlignLeft,f'{x/1000:.2f} km')
        terrain=QPolygonF([point(x,y) for x,y in zip(profile['distances_m'],profile['terrain_effective_m'])])
        painter.setPen(QPen(QColor('#81663f'),2));painter.drawPolyline(terrain)
        painter.setPen(QPen(QColor('#126759'),2));painter.drawPolyline(QPolygonF([point(x,y) for x,y in zip(profile['distances_m'],profile['line_m'])]))
        if profile.get('frequency_mhz'):
            painter.setPen(QPen(QColor('#b65928'),2,Qt.PenStyle.DashLine))
            painter.drawPolyline(QPolygonF([point(x,y-profile['fresnel_fraction']*r) for x,y,r in zip(profile['distances_m'],profile['line_m'],profile['fresnel_radius_m'])]))
        painter.setPen(QColor('#172131'));painter.drawText(85,418,'Brown: terrain + Earth bulge | Teal: antenna path | Dashed: required Fresnel lower boundary')
    finally:painter.end()
    buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'PNG')
    return bytes(buffer.data())


def assessment_html(value):
    profile=value['profile'];dem=value['terrain']['dem'];context=value['endpoint_context']
    parts=['<h2>Terrain / path assessment</h2>',table(['Geometric terrain result','Fresnel result','Minimum clearance','First obstruction'],[[profile['status'],profile['fresnel_status'],profile['minimum_clearance_m'],profile['first_obstruction_m']]])]
    if value.get('profile_png'):
        parts.append('<p><img width="960" src="data:image/png;base64,'+value['profile_png']+'" alt="Terrain profile"></p>')
    parts.append(table(['Receiver AGL m','Site antenna AGL m','Frequency MHz','Earth factor','Fresnel fraction'],[[profile[k] for k in ('receiver_agl_m','site_agl_m','frequency_mhz','earth_factor','fresnel_fraction')]]))
    parts.append('<p>Prepared: '+text(value.get('prepared_utc'))+'<br>Endpoint: '+text(context['candidate'].get('verification','Estimated reference'))+'; '+text(value['terrain']['endpoints'])+'<br>DEM: '+text(dem['source'])+'; datum '+text(dem['vertical_datum'])+'; units '+text(dem['units'])+'; CRS '+text(dem['crs'])+'<br>DEM SHA-256: '+text(dem['sha256'])+'<br>Sample spacing: '+text(dem['sample_spacing_m'])+' m; nearest-cell sampling.</p>')
    parts.append('<p>Conditional on the selected reference location and operator-entered antenna heights. Bare-earth terrain omits buildings, vegetation and sub-pixel obstructions. No sampled obstruction is not a guarantee of coverage, visibility or connectivity.</p>')
    return '\n'.join(parts)
