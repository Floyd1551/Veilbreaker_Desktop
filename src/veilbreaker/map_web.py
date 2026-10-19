"""WebEngine imports are optional: native map evidence must still open."""
from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineUrlRequestInterceptor,QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

class LocalRequests(QWebEngineUrlRequestInterceptor):
    def __init__(self,base,parent=None):super().__init__(parent);self.base=base;self.blocked=0
    def permitted(self,url):
        value=url.toString()
        return value.startswith(self.base) or value.startswith('blob:'+self.base) or value.startswith('data:image/') or value=='about:blank'
    def interceptRequest(self,info):
        if not self.permitted(info.requestUrl()):self.blocked+=1;info.block(True)

class LocalPage(QWebEnginePage):
    def __init__(self,profile,parent,base):super().__init__(profile,parent);self.base=base
    def acceptNavigationRequest(self,url,kind,is_main):return url.toString()==self.base+'index.html' or url.toString()=='about:blank'
    def createWindow(self,kind):return None
    def javaScriptConsoleMessage(self,level,message,line,source):
        # CSP denials are expected. Renderer failures are reported by the page
        # and initialization timeout, not every Chromium console error.
        pass

def create_view(parent,base,bridge):
    profile=QWebEngineProfile(parent);profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
    interceptor=LocalRequests(base,profile);profile.setUrlRequestInterceptor(interceptor)
    profile.downloadRequested.connect(lambda request:request.cancel())
    page=LocalPage(profile,parent,base)
    page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,False)
    page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,False)
    page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled,False)
    channel=QWebChannel(page);channel.registerObject('bridge',bridge);page.setWebChannel(channel)
    view=QWebEngineView(parent);view.setPage(page)
    page.renderProcessTerminated.connect(lambda *_:bridge.failed('map renderer stopped'))
    return view,profile,interceptor
