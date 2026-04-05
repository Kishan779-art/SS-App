from __future__ import annotations

from tkinter import ttk


COLORS = {
    "bg": "#111827",
    "panel": "#18212f",
    "panel_alt": "#223043",
    "panel_soft": "#1d2735",
    "panel_hover": "#283548",
    "accent": "#d97706",
    "accent_hover": "#f59e0b",
    "accent_soft": "#4a3316",
    "text": "#f8fafc",
    "muted": "#9ca3af",
    "success": "#10b981",
    "success_soft": "#18392f",
    "danger": "#ef4444",
    "danger_soft": "#402023",
    "line": "#314153",
    "line_bright": "#475569",
}


FONTS = {
    "title": ("Segoe UI Semibold", 22),
    "subtitle": ("Segoe UI", 10),
    "heading": ("Segoe UI Semibold", 14),
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "metric": ("Segoe UI Semibold", 20),
}


def configure_ttk_styles(root) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=FONTS["body"])
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("AltPanel.TFrame", background=COLORS["panel_alt"])
    style.configure("SoftPanel.TFrame", background=COLORS["panel_soft"])

    style.configure("CardTitle.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=FONTS["small"])
    style.configure("Heading.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONTS["heading"])
    style.configure("SubHeading.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=FONTS["heading"])
    style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=FONTS["body"])
    style.configure("PanelMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=FONTS["body"])
    style.configure("Metric.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=FONTS["metric"])
    style.configure("Field.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=FONTS["small"])

    style.configure(
        "App.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text"],
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
        font=FONTS["body"],
    )
    style.map("App.TButton", background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent_hover"])])
    style.configure(
        "AppHover.TButton",
        background=COLORS["accent_hover"],
        foreground=COLORS["text"],
        borderwidth=0,
        focusthickness=0,
        padding=(16, 11),
        font=FONTS["body"],
    )
    style.configure(
        "AppPressed.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text"],
        borderwidth=0,
        focusthickness=0,
        padding=(15, 10),
        font=FONTS["body"],
    )

    style.configure("Ghost.TButton", background=COLORS["panel_alt"], foreground=COLORS["text"], borderwidth=0, padding=(12, 9))
    style.map("Ghost.TButton", background=[("active", COLORS["line"]), ("pressed", COLORS["line"])])
    style.configure("GhostHover.TButton", background=COLORS["line_bright"], foreground=COLORS["text"], borderwidth=0, padding=(13, 10))
    style.configure("GhostPressed.TButton", background=COLORS["line"], foreground=COLORS["text"], borderwidth=0, padding=(12, 9))

    style.configure(
        "Nav.TButton",
        background=COLORS["panel_soft"],
        foreground=COLORS["muted"],
        borderwidth=0,
        padding=(16, 12),
        anchor="w",
        font=("Segoe UI Semibold", 10),
    )
    style.map("Nav.TButton", background=[("active", COLORS["panel_alt"])], foreground=[("active", COLORS["text"])])
    style.configure(
        "NavHover.TButton",
        background=COLORS["panel_hover"],
        foreground=COLORS["text"],
        borderwidth=0,
        padding=(17, 13),
        anchor="w",
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "NavPressed.TButton",
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        borderwidth=0,
        padding=(16, 12),
        anchor="w",
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "ActiveNav.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text"],
        borderwidth=0,
        padding=(16, 12),
        anchor="w",
        font=("Segoe UI Semibold", 10),
    )
    style.map("ActiveNav.TButton", background=[("active", COLORS["accent_hover"])])
    style.configure(
        "ActiveNavHover.TButton",
        background=COLORS["accent_hover"],
        foreground=COLORS["text"],
        borderwidth=0,
        padding=(17, 13),
        anchor="w",
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "ActiveNavPressed.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text"],
        borderwidth=0,
        padding=(16, 12),
        anchor="w",
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS["panel_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["line"],
        lightcolor=COLORS["line"],
        darkcolor=COLORS["line"],
        insertcolor=COLORS["text"],
        padding=(8, 8),
    )
    style.configure(
        "Focus.TEntry",
        fieldbackground=COLORS["panel_hover"],
        foreground=COLORS["text"],
        bordercolor=COLORS["accent_hover"],
        lightcolor=COLORS["accent_hover"],
        darkcolor=COLORS["accent_hover"],
        insertcolor=COLORS["text"],
        padding=(8, 8),
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["panel_alt"],
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["line"],
        lightcolor=COLORS["line"],
        darkcolor=COLORS["line"],
        arrowsize=14,
        padding=(6, 6),
    )
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["panel_alt"])], selectbackground=[("readonly", COLORS["panel_alt"])])
    style.configure(
        "Focus.TCombobox",
        fieldbackground=COLORS["panel_hover"],
        background=COLORS["panel_hover"],
        foreground=COLORS["text"],
        bordercolor=COLORS["accent_hover"],
        lightcolor=COLORS["accent_hover"],
        darkcolor=COLORS["accent_hover"],
        arrowsize=14,
        padding=(6, 6),
    )
    style.map("Focus.TCombobox", fieldbackground=[("readonly", COLORS["panel_hover"])], selectbackground=[("readonly", COLORS["panel_hover"])])

    style.configure(
        "Treeview",
        background=COLORS["panel"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["panel"],
        bordercolor=COLORS["line"],
        rowheight=28,
        font=FONTS["body"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        relief="flat",
        font=("Segoe UI Semibold", 10),
    )
    style.map("Treeview", background=[("selected", COLORS["accent"])], foreground=[("selected", COLORS["text"])])
    style.map("Treeview.Heading", background=[("active", COLORS["panel_hover"])])
