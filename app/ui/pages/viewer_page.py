import tkinter as tk
from app.ui.components.workbench_viewer import WorkbenchViewer


class ViewerPage(tk.Frame):
    def __init__(self, parent, app_root, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self.viewer = WorkbenchViewer(self, app_root=app_root, on_dataset_loaded=self._on_dataset_loaded)

    def _on_dataset_loaded(self, dataframe, file_label_text, is_new_file=False, metadata=None):
        self.workbench.set_loaded_dataset(dataframe, file_label_text, is_new_file=is_new_file, metadata=metadata)

    def on_show(self):
        pass

    def on_resize_commit(self):
        try:
            self.viewer.grid_table.schedule_render(force=False)
        except Exception:
            pass
        try:
            self.viewer.canvas.draw_idle()
        except Exception:
            pass
