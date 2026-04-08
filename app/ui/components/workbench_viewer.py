import numpy as np

from app.ui.viewer_module import FastCSVViewerWithGraph


class WorkbenchViewer(FastCSVViewerWithGraph):
    def __init__(self, parent, app_root=None, on_dataset_loaded=None):
        self.on_dataset_loaded = on_dataset_loaded
        super().__init__(parent, app_root=app_root)


    def reset_session_state(self):
        self.numeric_cache.clear()
        self.filtered_cache.clear()
        self.channel_extrema_cache.clear()
        self.multi_channels = []
        self.channel_colors = {}
        self.current_channel = None
        self.selected_graph_row = None
        self.selected_graph_col = None
        self.current_xlim_full = None
        self.current_ylim_full = None
        self.current_view_xlim = None
        self.current_view_ylim = None
        self.hover_row = None
        self.hover_annotation = None
        self.hover_point_artist = None
        self.filter_mode.set("Raw")
        self.overlay_raw.set(False)
        self.set_span_zoom_active(False)
        try:
            self.grid_table.set_multi_checked_columns([])
        except Exception:
            pass
        try:
            self.refresh_multi_channel_ui()
        except Exception:
            pass
        try:
            self.update_metadata_info()
            self.update_status_bar()
        except Exception:
            pass

    def load_dat(self):
        old_id = id(self.df) if self.df is not None else None
        super().load_dat()
        new_id = id(self.df) if self.df is not None else None
        if self.df is not None and new_id != old_id:
            self._notify_dataset_loaded(is_new_file=True)

    def load_csv(self):
        self.load_dat()

    def _notify_dataset_loaded(self, is_new_file=False):
        if callable(self.on_dataset_loaded) and self.df is not None:
            metadata = dict(getattr(self, "loaded_metadata", {}) or {})
            metadata.update({
                "units": dict(getattr(self, "external_units", {}) or {}),
                "descriptions": dict(getattr(self, "external_descriptions", {}) or {}),
                "lengths": dict(getattr(self, "external_lengths", {}) or {}),
                "time_column": self.time_column,
            })
            metadata.setdefault("source_format", "CSV" if str(self.file_label.cget("text")).lower().endswith(".csv") else "DAT")
            self.on_dataset_loaded(self.df.copy(deep=True), self.file_label.cget("text"), is_new_file=is_new_file, metadata=metadata)

    def load_dataframe(self, dataframe, file_label_text=None, reset_plot=False, metadata=None):
        if dataframe is None or dataframe.empty:
            return

        self.df = dataframe.copy(deep=True)
        self.columns = list(self.df.columns)
        self.numeric_cache.clear()
        self.filtered_cache.clear()
        self.selected_graph_row = None
        self.selected_graph_col = None
        self.current_xlim_full = None
        self.current_ylim_full = None
        self.current_view_xlim = None
        self.current_view_ylim = None
        self.hover_row = None
        self.filter_mode.set("Raw")
        self.overlay_raw.set(False)
        self.set_span_zoom_active(False)

        metadata = metadata or {}
        self.loaded_metadata = dict(metadata)
        self.external_units = dict(metadata.get("units", {}) or {})
        self.external_descriptions = dict(metadata.get("descriptions", {}) or {})
        self.external_lengths = dict(metadata.get("lengths", {}) or {})
        self.time_column = metadata.get("time_column") or self.find_time_column()
        self.extract_metadata_rows()

        self.display_data, row_labels = self._build_display_dataframe_and_labels(metadata)

        self.grid_table.set_data(self.columns, self.display_data, row_labels=row_labels)
        self.grid_table.set_multi_checked_columns(self.multi_channels)
        self.refresh_multi_channel_ui()

        if file_label_text:
            self.file_label.config(text=file_label_text)

        if self.current_channel not in self.columns:
            self.current_channel = None

        if reset_plot or self.current_channel is None or self.time_column is None:
            self.clear_graph()
            self.update_metadata_info()
            self.update_status_bar()
            return

        try:
            self.plot_channel(selected_row=None, preserve_view=False)
        except Exception:
            self.clear_graph()
        self.update_metadata_info(self.current_channel)
        self.update_status_bar()

    def get_numeric_channel_names(self, exclude_time=True):
        if self.df is None:
            return []
        result = []
        for col in self.columns:
            if exclude_time and self.time_column is not None and col == self.time_column:
                continue
            arr = self.get_numeric_column(col)
            if np.isfinite(arr).any():
                result.append(col)
        return result

    def get_preferred_preview_channel(self):
        channels = self.get_numeric_channel_names(exclude_time=True)
        if not channels:
            return None
        if self.current_channel in channels:
            return self.current_channel
        return channels[0]
