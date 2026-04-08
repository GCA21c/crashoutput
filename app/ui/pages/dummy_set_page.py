import tkinter as tk
from tkinter import messagebox, ttk

from app.core.dummy.engine import FRONTAL_UNIFIED_PROFILES, SIDE_UNIFIED_PROFILES
from app.ui.components.multi_dummy_panel import MultiDummyPanel, DUMMY_POSITION_OPTIONS


class DummySetPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self.status_var = tk.StringVar(value="SET! 전까지는 현재 설정이 계산 모듈에 반영되지 않습니다.")
        self.dummy_count_var = tk.StringVar(value="1")
        self.active_dummy_var = tk.StringVar(value="B1")
        self._build_ui()

    def _profile_options(self):
        mode = str(self.workbench.injury_test_mode_var.get() or 'FRONTAL').strip().upper()
        if mode == 'SIDE':
            return tuple(SIDE_UNIFIED_PROFILES)
        return tuple(FRONTAL_UNIFIED_PROFILES)

    def _build_ui(self):
        outer = tk.Frame(self, bg="#ffffff")
        outer.pack(fill=tk.BOTH, expand=True, anchor="nw")

        body = tk.Frame(outer, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, anchor="nw", padx=16, pady=(16, 8))

        content = tk.Frame(body, bg="#ffffff", width=620)
        content.pack(anchor="nw")

        header = tk.Frame(content, bg="#ffffff")
        header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(header, text="DUMMY SET", font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)

        mode_row = tk.Frame(content, bg="#ffffff")
        mode_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(mode_row, text="시험모드", bg="#ffffff", width=9, anchor="w").pack(side=tk.LEFT)
        self.mode_combo = ttk.Combobox(
            mode_row,
            textvariable=self.workbench.injury_test_mode_var,
            values=("-", "FRONTAL", "SIDE"),
            state="readonly",
            width=14,
        )
        self.mode_combo.pack(side=tk.LEFT)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        info = tk.LabelFrame(content, text="설명", bg="#ffffff")
        info.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            info,
            text=(
                "멀티 더미 설정을 한 곳에서 일원화합니다.\n"
                "여기서 시험모드 / 더미 대수 / 배치 / 이름 / 프로필을 저장하면 각 상해 모듈에서는 더미 위치 탭만 사용합니다."
            ),
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=540,
        ).pack(fill=tk.X, padx=10, pady=8)

        self.panel = MultiDummyPanel(
            content,
            dummy_count_var=self.dummy_count_var,
            active_dummy_var=self.active_dummy_var,
            profile_options_getter=self._profile_options,
            on_count_changed=self._on_dummy_count_changed,
            on_positions_changed=self._on_positions_changed,
            show_count_row=True,
            show_rows=True,
            show_tabs=False,
            compact_layout=True,
            title="더미 공통 설정",
        )
        self.panel.pack(fill=tk.X, pady=(0, 8), anchor="nw")

        footer = tk.Frame(content, bg="#ffffff")
        footer.pack(fill=tk.X, pady=(0, 8))
        tk.Button(footer, text="SET!", command=self.save_settings, width=12).pack(side=tk.LEFT)
        tk.Label(footer, textvariable=self.status_var, bg="#ffffff", fg="#374151", anchor="w", justify="left").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

    def _on_mode_changed(self, _event=None):
        self.panel.refresh_profile_options()

    def _on_dummy_count_changed(self, *_args):
        # count 변경 즉시 행 재구성
        self.panel.set_active_positions(
            self.panel.get_selected_positions() or ['B1'],
            explicit_positions=self.panel.get_row_positions(),
        )

    def _on_positions_changed(self, *_args):
        pass

    def on_show(self):
        config = self.workbench.get_shared_dummy_config()
        mode = str(config.get('injury_test_mode') or self.workbench.injury_test_mode_var.get() or '-').strip().upper()
        if mode not in ('-', 'FRONTAL', 'SIDE'):
            mode = '-'
        self.workbench.injury_test_mode_var.set(mode)
        self.dummy_count_var.set(str(config.get('dummy_count') or 1))
        self.panel.set_detected_positions(self.workbench.get_detected_dummy_positions())
        self.panel.set_active_positions(config.get('active_positions') or ['B1'], explicit_positions=config.get('row_positions') or ['B1'])
        slot_meta = config.get('slot_meta') or {}
        for slot in DUMMY_POSITION_OPTIONS:
            meta = slot_meta.get(slot) or {}
            self.panel.name_var(slot).set(meta.get('dummy_name') or '')
            self.panel.profile_var(slot).set(meta.get('dummy_profile') or '')
        self.panel.refresh_profile_options()
        if config.get('setup_complete'):
            self.status_var.set("현재 저장된 공통 더미 설정을 불러왔습니다.")
        else:
            self.status_var.set("SET! 전까지는 현재 설정이 계산 모듈에 반영되지 않습니다.")

    def save_settings(self):
        mode = str(self.workbench.injury_test_mode_var.get() or '-').strip().upper()
        config = {
            'injury_test_mode': mode,
            'setup_complete': mode in ('FRONTAL', 'SIDE'),
            'dummy_count': int(self.dummy_count_var.get() or 1),
            'active_positions': self.panel.get_selected_positions() or ['B1'],
            'row_positions': self.panel.get_row_positions() or ['B1'],
            'slot_meta': {
                slot: {
                    'dummy_name': self.panel.name_var(slot).get().strip(),
                    'dummy_profile': self.panel.profile_var(slot).get().strip(),
                }
                for slot in DUMMY_POSITION_OPTIONS
            },
        }
        self.workbench.set_shared_dummy_config(config)
        self.status_var.set("공통 더미 설정이 저장되었습니다. 이제 각 상해 모듈은 더미 위치 탭만 사용합니다.")
        try:
            messagebox.showinfo("DUMMY SET", "공통 더미 설정이 저장되었습니다.")
        except Exception:
            pass
