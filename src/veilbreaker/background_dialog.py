"""Reusable bounded job dialog lifecycle with QObject-owned slots."""
import threading
from PySide6.QtCore import QThread,Signal,Slot,QTimer
from PySide6.QtWidgets import QDialog

class JobWorker(QThread):
    ready=Signal(object)
    failed=Signal(str)
    progress=Signal(object)
    def __init__(self,operation,parent):
        super().__init__(parent);self.operation=operation;self.cancelled=threading.Event()
    def run(self):
        try:
            value=self.operation(self.cancelled.is_set,self.progress.emit)
            if not self.cancelled.is_set():self.ready.emit(value)
        except Exception as exc:self.failed.emit(str(exc))

class JobDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.worker=None;self.closing=False
    def start_job(self,operation):
        if self.worker is not None:return
        self.worker=JobWorker(operation,self)
        self.worker.ready.connect(self.job_ready);self.worker.failed.connect(self.job_failed)
        self.worker.progress.connect(self.job_progress);self.worker.finished.connect(self.job_finished)
        self.set_busy(True);self.worker.start()
    @Slot(object)
    def job_ready(self,value):pass
    @Slot(str)
    def job_failed(self,message):self.status.setText(message)
    @Slot(object)
    def job_progress(self,value):self.status.setText(str(value))
    @Slot()
    def job_finished(self):
        worker=self.worker;self.worker=None;worker.deleteLater();self.set_busy(False)
        if self.closing:super().reject()
    def set_busy(self,busy):
        for widget in self.controls:widget.setEnabled(not busy)
    @Slot()
    def reject(self):
        if self.worker is not None:
            self.closing=True;self.worker.cancelled.set();self.status.setText('Cancelling; waiting for the operation to finish…');return
        super().reject()
    def closeEvent(self,event):
        if self.worker is not None:event.ignore();self.reject()
        else:super().closeEvent(event)


def defer_background_close(owner,event):
    workers=[worker for worker in owner.findChildren(JobWorker) if worker.isRunning()]
    if not workers:return False
    for worker in workers:worker.cancelled.set()
    event.ignore()
    QTimer.singleShot(50,owner.close)
    return True
