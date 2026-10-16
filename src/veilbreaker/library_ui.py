"""Small, explicit restore workflow for recoverable library removals."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from .library import list_trash, restore_entry

class TrashDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        from .gui import table, button, label
        self.config=config
        self.setWindowTitle('Trash — saved evidence retained')
        self.resize(850,450)
        layout=QVBoxLayout(self)
        layout.addWidget(label('Removed items retain their evidence. Select an item to restore it.'))
        self.rows=table(['Type','Item','Removed UTC']); layout.addWidget(self.rows)
        layout.addWidget(button('Restore selected',self.restore))
        layout.addWidget(button('Close',self.accept))
        self.refresh()
    def refresh(self):
        from .gui import fill
        self.entries=list_trash(self.config)
        fill(self.rows,[[r['kind'],r['item_id'],r['removed_utc']] for r in self.entries])
    def restore(self):
        index=self.rows.currentRow()
        if not self.rows.selectedItems() or not 0<=index<len(self.entries): return
        try:
            restore_entry(self.config,self.entries[index]['entry_id'])
            self.refresh()
        except (OSError,ValueError) as exc: QMessageBox.warning(self,'Cannot restore',str(exc))
