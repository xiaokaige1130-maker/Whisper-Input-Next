"""Control UI visual themes (Linux).

Themes are pure presentation: switching only rewrites the stylesheet and
persists UI_THEME in .env. Service process does not need a restart.
"""

from __future__ import annotations

from typing import Mapping

# (display_label, theme_id)
THEME_OPTIONS: list[tuple[str, str]] = [
    ("经典绿 · 深色侧栏", "classic"),
    ("浅色简洁", "light"),
    ("深色护眼", "dark"),
    ("午夜蓝", "blue"),
]

DEFAULT_THEME = "classic"
THEME_IDS = {theme_id for _, theme_id in THEME_OPTIONS}

# Color tokens shared by the stylesheet template.
_PALETTES: dict[str, dict[str, str]] = {
    # Original look: dark green sidebar + soft content (easier on the eyes).
    "classic": {
        "font_size": "13px",
        "text": "#172019",
        "text_muted": "#6b766e",
        "text_soft": "#8a948d",
        "text_strong": "#142019",
        "bg_app": "#f3f5f2",
        "bg_card": "#ffffff",
        "bg_input": "#fbfcfb",
        "bg_input_focus": "#ffffff",
        "bg_band": "#e8ece8",
        "bg_header": "#eef1ee",
        "bg_hover": "#edf0ed",
        "bg_chip": "#ffffff",
        "bg_chip_running": "#eaf7ef",
        "border": "#dce2dd",
        "border_strong": "#cfd7d1",
        "border_chip": "#d6ddd7",
        "border_chip_running": "#b8dfc7",
        "sidebar_bg": "#101411",
        "sidebar_border": "transparent",
        "brand": "#f5f7f4",
        "brand_sub": "#8f9b92",
        "version": "#657169",
        "nav_text": "#aeb8b1",
        "nav_hover_bg": "#1a201c",
        "nav_hover_text": "#ffffff",
        "nav_selected_bg": "#21392b",
        "nav_selected_text": "#f6fff9",
        "accent": "#227d4f",
        "accent_hover": "#196840",
        "accent_soft": "#238553",
        "accent_text": "#1d5e3b",
        "accent_bg": "#edf7f0",
        "accent_border": "#cce3d4",
        "accent_select": "#2e8a59",
        "accent_row": "#e5f3ea",
        "status_text": "#48534b",
        "status_dot": "#a5aca7",
        "status_dot_running": "#238553",
        "primary_text": "#ffffff",
        "secondary_text": "#263129",
        "secondary_bg": "#ffffff",
        "secondary_border": "#ccd4ce",
        "danger_text": "#9b3733",
        "danger_bg": "#fff7f6",
        "danger_border": "#e7c7c4",
        "danger_hover": "#fde9e7",
        "diag_good_bg": "#ecf8f0",
        "diag_good_border": "#b8dfc7",
        "diag_bad_bg": "#fff0ee",
        "diag_bad_border": "#ecc5c1",
        "diag_warn_bg": "#fff7e8",
        "diag_warn_border": "#ebd2a6",
        "conflict_bg": "#f4f6f4",
        "conflict_good_text": "#1e6942",
        "conflict_good_bg": "#edf8f1",
        "conflict_good_border": "#c3e2cf",
        "conflict_bad_text": "#9b3733",
        "conflict_bad_bg": "#fff3f1",
        "conflict_bad_border": "#e7c7c4",
        "conflict_cap_text": "#7c520d",
        "conflict_cap_bg": "#fff8e8",
        "conflict_cap_border": "#e5cc94",
        "capture_text": "#7c520d",
        "capture_bg": "#fff8e8",
        "capture_border": "#d7a84d",
        "persona_text": "#23476b",
        "persona_bg": "#eef5fb",
        "persona_border": "#c7d9e8",
        "table_item_border": "#edf0ed",
        "scroll_handle": "#bec7c0",
        "log_text": "#dce8df",
        "log_bg": "#151a16",
        "log_border": "#2b332d",
        "radius_card": "10px",
        "radius_btn": "8px",
        "nav_item_height": "34px",
        "btn_min_height": "32px",
        "input_min_height": "32px",
    },
    # Bright macOS Settings-like light theme.
    "light": {
        "font_size": "13px",
        "text": "#1d1d1f",
        "text_muted": "#86868b",
        "text_soft": "#aeaeb2",
        "text_strong": "#1d1d1f",
        "bg_app": "#f5f5f7",
        "bg_card": "#ffffff",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_band": "#ffffff",
        "bg_header": "#fafafa",
        "bg_hover": "#f2f2f7",
        "bg_chip": "#ffffff",
        "bg_chip_running": "#e8f8ee",
        "border": "#e5e5ea",
        "border_strong": "#d2d2d7",
        "border_chip": "#d2d2d7",
        "border_chip_running": "#b7e0c5",
        "sidebar_bg": "#ececf0",
        "sidebar_border": "#d2d2d7",
        "brand": "#1d1d1f",
        "brand_sub": "#86868b",
        "version": "#aeaeb2",
        "nav_text": "#1d1d1f",
        "nav_hover_bg": "#e1e1e6",
        "nav_hover_text": "#1d1d1f",
        "nav_selected_bg": "#ffffff",
        "nav_selected_text": "#1d1d1f",
        "accent": "#007aff",
        "accent_hover": "#0066d6",
        "accent_soft": "#007aff",
        "accent_text": "#007aff",
        "accent_bg": "#f0f7ff",
        "accent_border": "#c9e1ff",
        "accent_select": "#007aff",
        "accent_row": "#e8f1ff",
        "status_text": "#3a3a3c",
        "status_dot": "#aeaeb2",
        "status_dot_running": "#34c759",
        "primary_text": "#ffffff",
        "secondary_text": "#1d1d1f",
        "secondary_bg": "#ffffff",
        "secondary_border": "#d2d2d7",
        "danger_text": "#ff3b30",
        "danger_bg": "#ffffff",
        "danger_border": "#ffc9c6",
        "danger_hover": "#fff2f1",
        "diag_good_bg": "#eefbf2",
        "diag_good_border": "#c6ecd2",
        "diag_bad_bg": "#fff2f1",
        "diag_bad_border": "#f0c9c6",
        "diag_warn_bg": "#fff8eb",
        "diag_warn_border": "#f0ddb0",
        "conflict_bg": "#f2f2f7",
        "conflict_good_text": "#1f7a3a",
        "conflict_good_bg": "#eefbf2",
        "conflict_good_border": "#c6ecd2",
        "conflict_bad_text": "#c9342b",
        "conflict_bad_bg": "#fff2f1",
        "conflict_bad_border": "#f0c9c6",
        "conflict_cap_text": "#9a5b00",
        "conflict_cap_bg": "#fff8eb",
        "conflict_cap_border": "#f0ddb0",
        "capture_text": "#b25000",
        "capture_bg": "#fff8eb",
        "capture_border": "#f0c36d",
        "persona_text": "#3a3a3c",
        "persona_bg": "#f2f2f7",
        "persona_border": "#e5e5ea",
        "table_item_border": "#f2f2f7",
        "scroll_handle": "#c7c7cc",
        "log_text": "#e8e8ed",
        "log_bg": "#1c1c1e",
        "log_border": "#3a3a3c",
        "radius_card": "12px",
        "radius_btn": "8px",
        "nav_item_height": "32px",
        "btn_min_height": "30px",
        "input_min_height": "30px",
    },
    # Full dark: less glare at night.
    "dark": {
        "font_size": "13px",
        "text": "#f2f2f7",
        "text_muted": "#98989f",
        "text_soft": "#6c6c70",
        "text_strong": "#ffffff",
        "bg_app": "#1c1c1e",
        "bg_card": "#2c2c2e",
        "bg_input": "#3a3a3c",
        "bg_input_focus": "#48484a",
        "bg_band": "#2c2c2e",
        "bg_header": "#3a3a3c",
        "bg_hover": "#3a3a3c",
        "bg_chip": "#2c2c2e",
        "bg_chip_running": "#1f3d2a",
        "border": "#3a3a3c",
        "border_strong": "#48484a",
        "border_chip": "#48484a",
        "border_chip_running": "#2f6b45",
        "sidebar_bg": "#111113",
        "sidebar_border": "#2c2c2e",
        "brand": "#f5f5f7",
        "brand_sub": "#8e8e93",
        "version": "#636366",
        "nav_text": "#aeaeb2",
        "nav_hover_bg": "#2c2c2e",
        "nav_hover_text": "#ffffff",
        "nav_selected_bg": "#3a3a3c",
        "nav_selected_text": "#ffffff",
        "accent": "#30d158",
        "accent_hover": "#28c04e",
        "accent_soft": "#30d158",
        "accent_text": "#30d158",
        "accent_bg": "#1a3324",
        "accent_border": "#2f6b45",
        "accent_select": "#30d158",
        "accent_row": "#1f3d2a",
        "status_text": "#d1d1d6",
        "status_dot": "#636366",
        "status_dot_running": "#30d158",
        "primary_text": "#0b1a10",
        "secondary_text": "#f2f2f7",
        "secondary_bg": "#3a3a3c",
        "secondary_border": "#48484a",
        "danger_text": "#ff6961",
        "danger_bg": "#3a2423",
        "danger_border": "#7a3a36",
        "danger_hover": "#4a2c2a",
        "diag_good_bg": "#1a3324",
        "diag_good_border": "#2f6b45",
        "diag_bad_bg": "#3a2423",
        "diag_bad_border": "#7a3a36",
        "diag_warn_bg": "#3a3118",
        "diag_warn_border": "#8a6a20",
        "conflict_bg": "#2c2c2e",
        "conflict_good_text": "#30d158",
        "conflict_good_bg": "#1a3324",
        "conflict_good_border": "#2f6b45",
        "conflict_bad_text": "#ff6961",
        "conflict_bad_bg": "#3a2423",
        "conflict_bad_border": "#7a3a36",
        "conflict_cap_text": "#ffd60a",
        "conflict_cap_bg": "#3a3118",
        "conflict_cap_border": "#8a6a20",
        "capture_text": "#ffd60a",
        "capture_bg": "#3a3118",
        "capture_border": "#8a6a20",
        "persona_text": "#64d2ff",
        "persona_bg": "#1a2a33",
        "persona_border": "#2f5a6b",
        "table_item_border": "#3a3a3c",
        "scroll_handle": "#636366",
        "log_text": "#d1d1d6",
        "log_bg": "#000000",
        "log_border": "#3a3a3c",
        "radius_card": "12px",
        "radius_btn": "8px",
        "nav_item_height": "32px",
        "btn_min_height": "30px",
        "input_min_height": "30px",
    },
    # Navy sidebar + cool content.
    "blue": {
        "font_size": "13px",
        "text": "#0f172a",
        "text_muted": "#64748b",
        "text_soft": "#94a3b8",
        "text_strong": "#0f172a",
        "bg_app": "#eef2f7",
        "bg_card": "#ffffff",
        "bg_input": "#f8fafc",
        "bg_input_focus": "#ffffff",
        "bg_band": "#e2e8f0",
        "bg_header": "#e8eef6",
        "bg_hover": "#e8eef6",
        "bg_chip": "#ffffff",
        "bg_chip_running": "#e0f2fe",
        "border": "#d0d9e6",
        "border_strong": "#b8c5d6",
        "border_chip": "#c5d0e0",
        "border_chip_running": "#7dd3fc",
        "sidebar_bg": "#0f172a",
        "sidebar_border": "transparent",
        "brand": "#f8fafc",
        "brand_sub": "#94a3b8",
        "version": "#64748b",
        "nav_text": "#94a3b8",
        "nav_hover_bg": "#1e293b",
        "nav_hover_text": "#ffffff",
        "nav_selected_bg": "#1d4ed8",
        "nav_selected_text": "#ffffff",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_soft": "#2563eb",
        "accent_text": "#1d4ed8",
        "accent_bg": "#eff6ff",
        "accent_border": "#bfdbfe",
        "accent_select": "#2563eb",
        "accent_row": "#dbeafe",
        "status_text": "#334155",
        "status_dot": "#94a3b8",
        "status_dot_running": "#0ea5e9",
        "primary_text": "#ffffff",
        "secondary_text": "#0f172a",
        "secondary_bg": "#ffffff",
        "secondary_border": "#b8c5d6",
        "danger_text": "#b91c1c",
        "danger_bg": "#fef2f2",
        "danger_border": "#fecaca",
        "danger_hover": "#fee2e2",
        "diag_good_bg": "#ecfdf5",
        "diag_good_border": "#a7f3d0",
        "diag_bad_bg": "#fef2f2",
        "diag_bad_border": "#fecaca",
        "diag_warn_bg": "#fffbeb",
        "diag_warn_border": "#fde68a",
        "conflict_bg": "#f1f5f9",
        "conflict_good_text": "#047857",
        "conflict_good_bg": "#ecfdf5",
        "conflict_good_border": "#a7f3d0",
        "conflict_bad_text": "#b91c1c",
        "conflict_bad_bg": "#fef2f2",
        "conflict_bad_border": "#fecaca",
        "conflict_cap_text": "#b45309",
        "conflict_cap_bg": "#fffbeb",
        "conflict_cap_border": "#fde68a",
        "capture_text": "#b45309",
        "capture_bg": "#fffbeb",
        "capture_border": "#f59e0b",
        "persona_text": "#1d4ed8",
        "persona_bg": "#eff6ff",
        "persona_border": "#bfdbfe",
        "table_item_border": "#e8eef6",
        "scroll_handle": "#94a3b8",
        "log_text": "#e2e8f0",
        "log_bg": "#0f172a",
        "log_border": "#334155",
        "radius_card": "10px",
        "radius_btn": "8px",
        "nav_item_height": "34px",
        "btn_min_height": "32px",
        "input_min_height": "32px",
    },
}


def normalize_theme(theme_id: str | None) -> str:
    value = (theme_id or DEFAULT_THEME).strip().lower()
    return value if value in THEME_IDS else DEFAULT_THEME


def palette_for(theme_id: str | None) -> Mapping[str, str]:
    return _PALETTES[normalize_theme(theme_id)]


def build_stylesheet(theme_id: str | None = None) -> str:
    p = dict(palette_for(theme_id))
    # Double braces become single braces in the final CSS.
    return """
            * {{
                font-family: "Ubuntu Sans", "Noto Sans CJK SC", "Source Han Sans SC",
                    "DejaVu Sans", "Sans Serif";
                font-size: {font_size};
                color: {text};
            }}
            QMainWindow, QWidget#appRoot, QFrame#contentPanel {{
                background: {bg_app};
            }}
            QFrame#sidebar {{
                background: {sidebar_bg};
                border: none;
                border-right: 1px solid {sidebar_border};
            }}
            QLabel#brandTitle {{
                color: {brand};
                font-size: 15px;
                font-weight: 700;
            }}
            QLabel#brandSubtitle {{
                color: {brand_sub};
                font-size: 11px;
            }}
            QLabel#versionLabel {{
                color: {version};
                font-size: 10px;
                font-weight: 500;
            }}
            QListWidget#navigation {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#navigation::item {{
                color: {nav_text};
                min-height: {nav_item_height};
                padding: 0 12px;
                margin: 1px 4px;
                border-radius: 8px;
            }}
            QListWidget#navigation::item:hover {{
                background: {nav_hover_bg};
                color: {nav_hover_text};
            }}
            QListWidget#navigation::item:selected {{
                background: {nav_selected_bg};
                color: {nav_selected_text};
                font-weight: 600;
            }}
            QLabel#pageTitle {{
                font-size: 22px;
                font-weight: 700;
                color: {text_strong};
                letter-spacing: -0.3px;
            }}
            QFrame#statusChip {{
                border-radius: 999px;
                border: 1px solid {border_chip};
                background: {bg_chip};
            }}
            QFrame#statusChip[state="running"] {{
                background: {bg_chip_running};
                border-color: {border_chip_running};
            }}
            QLabel#statusDot {{
                color: {status_dot};
                font-size: 11px;
            }}
            QFrame#statusChip[state="running"] QLabel#statusDot {{
                color: {status_dot_running};
            }}
            QLabel#statusText {{
                color: {status_text};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#iconButton {{
                background: {bg_card};
                border: 1px solid {border_strong};
                border-radius: {radius_btn};
                padding: 0;
            }}
            QPushButton#iconButton:hover {{
                background: {bg_hover};
            }}
            QFrame#heroPanel, QFrame#sectionPanel,
            QFrame#metricCard, QFrame#diagnosticCard {{
                background: {bg_card};
                border: 1px solid {border};
                border-radius: {radius_card};
            }}
            QLabel#eyebrow {{
                color: {accent_soft};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#heroTitle {{
                color: {text_strong};
                font-size: 17px;
                font-weight: 700;
            }}
            QLabel#heroDetail, QLabel#pageHint, QLabel#panelDetail {{
                color: {text_muted};
                font-size: 12px;
            }}
            QLabel#metricTitle, QLabel#diagnosticTitle, QLabel#configTitle {{
                color: {text_muted};
                font-size: 11px;
                font-weight: 500;
            }}
            QLabel#metricValue {{
                color: {text_strong};
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#metricSubtitle {{
                color: {text_soft};
                font-size: 11px;
            }}
            QLabel#sectionTitle, QLabel#panelTitle {{
                color: {text_strong};
                font-size: 15px;
                font-weight: 700;
            }}
            QFrame#configBand {{
                background: {bg_band};
                border: 1px solid {border};
                border-radius: {radius_card};
            }}
            QLabel#configValue {{
                color: {text_strong};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#diagnosticValue {{
                color: {status_text};
                font-size: 12px;
                font-weight: 600;
            }}
            QFrame#diagnosticCard[status="good"] {{
                background: {diag_good_bg};
                border-color: {diag_good_border};
            }}
            QFrame#diagnosticCard[status="bad"] {{
                background: {diag_bad_bg};
                border-color: {diag_bad_border};
            }}
            QFrame#diagnosticCard[status="warning"] {{
                background: {diag_warn_bg};
                border-color: {diag_warn_border};
            }}
            QPushButton {{
                min-height: {btn_min_height};
                padding: 0 14px;
                border-radius: {radius_btn};
                font-weight: 600;
                color: {text};
            }}
            QPushButton[role="primary"] {{
                color: {primary_text};
                background: {accent};
                border: 1px solid {accent};
            }}
            QPushButton[role="primary"]:hover {{
                background: {accent_hover};
            }}
            QPushButton[role="secondary"] {{
                color: {secondary_text};
                background: {secondary_bg};
                border: 1px solid {secondary_border};
            }}
            QPushButton[role="secondary"]:hover {{
                background: {bg_hover};
            }}
            QPushButton[role="danger"] {{
                color: {danger_text};
                background: {danger_bg};
                border: 1px solid {danger_border};
            }}
            QPushButton[role="danger"]:hover {{
                background: {danger_hover};
            }}
            QPushButton[role="link"] {{
                color: {accent};
                background: transparent;
                border: none;
                padding: 0 4px;
                min-height: 22px;
            }}
            QLineEdit, QComboBox, QSpinBox {{
                min-height: {input_min_height};
                color: {text};
                background: {bg_input};
                border: 1px solid {border_strong};
                border-radius: {radius_btn};
                padding: 0 10px;
                selection-background-color: {accent_select};
                selection-color: {primary_text};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {accent};
                background: {bg_input_focus};
            }}
            QComboBox QAbstractItemView {{
                color: {text};
                background: {bg_card};
                border: 1px solid {border};
                selection-background-color: {accent_row};
                selection-color: {text_strong};
            }}
            QLineEdit#hotkeyCapture {{
                color: {accent_text};
                background: {accent_bg};
                font-weight: 700;
            }}
            QLineEdit#hotkeyCapture[capturing="true"] {{
                color: {capture_text};
                background: {capture_bg};
                border: 1px solid {capture_border};
            }}
            QLabel#hotkeyConflictStatus {{
                color: {status_text};
                background: {conflict_bg};
                border: 1px solid {border};
                border-radius: {radius_btn};
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QLabel#hotkeyConflictStatus[state="good"] {{
                color: {conflict_good_text};
                background: {conflict_good_bg};
                border-color: {conflict_good_border};
            }}
            QLabel#hotkeyConflictStatus[state="bad"] {{
                color: {conflict_bad_text};
                background: {conflict_bad_bg};
                border-color: {conflict_bad_border};
            }}
            QLabel#hotkeyConflictStatus[state="capture"] {{
                color: {conflict_cap_text};
                background: {conflict_cap_bg};
                border-color: {conflict_cap_border};
            }}
            QLabel#shortcutSummary {{
                color: {accent_text};
                background: {accent_bg};
                border: 1px solid {accent_border};
                border-radius: {radius_btn};
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            QToolButton#spinStepButton {{
                background: {bg_card};
                border: 1px solid {border_strong};
                border-radius: {radius_btn};
                padding: 3px;
            }}
            QToolButton#spinStepButton:hover {{
                background: {accent_bg};
                border-color: {accent};
            }}
            QToolButton#spinStepButton:pressed {{
                background: {accent_row};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QCheckBox {{
                spacing: 8px;
                color: {text};
            }}
            QTableWidget#dataTable {{
                color: {text};
                background: {bg_card};
                alternate-background-color: {bg_card};
                border: 1px solid {border};
                border-radius: {radius_card};
                outline: none;
                selection-background-color: {accent_row};
                selection-color: {text_strong};
                gridline-color: {table_item_border};
            }}
            QTableWidget#dataTable::item {{
                border-bottom: 1px solid {table_item_border};
                padding: 0 8px;
            }}
            QHeaderView::section {{
                min-height: 30px;
                color: {text_muted};
                background: {bg_header};
                border: none;
                border-bottom: 1px solid {border};
                padding: 0 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#logPath {{
                color: {text_muted};
                font-size: 11px;
            }}
            QLabel#glossaryArrow {{
                color: {accent_soft};
                font-size: 14px;
                font-weight: 700;
                min-width: 16px;
            }}
            QLabel#glossaryStatus {{
                color: {text_muted};
                font-size: 11px;
            }}
            QLabel#glossaryPreview {{
                color: {accent_text};
                background: {accent_bg};
                border: 1px solid {accent_border};
                border-radius: {radius_btn};
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#personaPreview {{
                color: {persona_text};
                background: {persona_bg};
                border: 1px solid {persona_border};
                border-radius: {radius_btn};
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 500;
                min-height: 28px;
            }}
            QPlainTextEdit#compactTextEdit {{
                color: {text};
                background: {bg_input};
                border: 1px solid {border_strong};
                border-radius: {radius_btn};
                padding: 8px 10px;
                selection-background-color: {accent_select};
                selection-color: {primary_text};
            }}
            QPlainTextEdit#compactTextEdit:focus {{
                border: 1px solid {accent};
                background: {bg_input_focus};
            }}
            QPlainTextEdit#logView {{
                color: {log_text};
                background: {log_bg};
                border: 1px solid {log_border};
                border-radius: {radius_card};
                padding: 10px;
                font-family: "Ubuntu Mono", "DejaVu Sans Mono", "Noto Sans Mono", monospace;
                font-size: 11px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 5px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            """.format(
        **p
    )
