from __future__ import annotations

import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.database import DatabaseManager
from app.reports import generate_pdf_report
from app.theme import COLORS, FONTS, configure_ttk_styles


def iso_today() -> str:
    return date.today().isoformat()


def month_start() -> str:
    today = date.today()
    return date(today.year, today.month, 1).isoformat()


def parse_iso_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def parse_float(value: str, field_name: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid number.") from exc
    return number


def money(value: float) -> str:
    return f"Rs. {value:,.2f}"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def blend_color(start: str, end: str, progress: float) -> str:
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    mixed = [
        round(channel_start + (channel_end - channel_start) * progress)
        for channel_start, channel_end in zip(start_rgb, end_rgb)
    ]
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


def resource_path(*parts: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_path.joinpath(*parts)


class BasePage(ttk.Frame):
    def __init__(self, parent, controller: "ConstructionManagementApp") -> None:
        super().__init__(parent, style="App.TFrame")
        self.controller = controller
        self.database = controller.database

    def card(self, parent, title: str) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        ttk.Label(frame, text=title, style="SubHeading.TLabel").pack(anchor="w")
        return frame

    def build_tree(self, parent, columns: list[tuple[str, int]]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=[name for name, _ in columns], show="headings")
        for name, width in columns:
            tree.heading(name, text=name.replace("_", " ").title())
            tree.column(name, width=width, anchor="center")

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def choose_export_path(self, title: str, report_name: str) -> str:
        return filedialog.asksaveasfilename(
            title=title,
            defaultextension=".pdf",
            initialfile=Path(self.database.default_report_path(report_name)).name,
            initialdir=str(self.database.export_dir),
            filetypes=[("PDF Files", "*.pdf")],
        )

    def flash_status(self, message: str) -> None:
        self.controller.flash_status(message)

    def selected_item_id(self, tree: ttk.Treeview, empty_message: str) -> int | None:
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", empty_message)
            return None
        return int(selection[0])

    def refresh(self) -> None:  # pragma: no cover - UI hook
        return


class ScrollablePanel(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent, style="App.TFrame")
        self.canvas = tk.Canvas(
            self,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas, style="App.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.content.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<Configure>", self._sync_width)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _sync_scroll_region(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_width(self, event) -> None:
        self.canvas.itemconfigure(self.window, width=event.width)

    def _bind_wheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")


class DashboardPage(BasePage):
    def __init__(self, parent, controller: "ConstructionManagementApp") -> None:
        super().__init__(parent, controller)
        self.metric_labels: dict[str, ttk.Label] = {}
        self.recent_production_tree: ttk.Treeview | None = None
        self.recent_payments_tree: ttk.Treeview | None = None
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Project Overview", style="Heading.TLabel").pack(anchor="w", padx=24, pady=(20, 8))
        ttk.Label(
            self,
            text="Track production, stock movement, and worker payments from one desktop workspace.",
            style="Muted.TLabel",
        ).pack(anchor="w", padx=24)

        metrics_frame = ttk.Frame(self, style="App.TFrame")
        metrics_frame.pack(fill="x", padx=24, pady=20)
        metrics = [
            ("production_entries", "Production Entries"),
            ("total_blocks", "Blocks Produced"),
            ("total_material_quantity", "Stock Quantity"),
            ("net_paid_total", "Net Payments"),
        ]
        for index, (key, label) in enumerate(metrics):
            card = ttk.Frame(metrics_frame, style="Panel.TFrame", padding=18)
            card.grid(row=0, column=index, padx=(0, 10 if index < len(metrics) - 1 else 0), sticky="nsew")
            metrics_frame.grid_columnconfigure(index, weight=1)
            ttk.Label(card, text=label, style="CardTitle.TLabel").pack(anchor="w")
            value_label = ttk.Label(card, text="0", style="Metric.TLabel")
            value_label.pack(anchor="w", pady=(10, 0))
            self.metric_labels[key] = value_label

        content = ttk.Frame(self, style="App.TFrame")
        content.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        production_card = self.card(content, "Recent Production")
        production_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        production_tree_host = ttk.Frame(production_card, style="Panel.TFrame")
        production_tree_host.pack(fill="both", expand=True, pady=(14, 0))
        self.recent_production_tree = self.build_tree(
            production_tree_host,
            [("entry_date", 110), ("block_type", 130), ("block_color", 110), ("blocks_produced", 110)],
        )

        payment_card = self.card(content, "Recent Payments")
        payment_card.grid(row=0, column=1, sticky="nsew")
        payment_tree_host = ttk.Frame(payment_card, style="Panel.TFrame")
        payment_tree_host.pack(fill="both", expand=True, pady=(14, 0))
        self.recent_payments_tree = self.build_tree(
            payment_tree_host,
            [("payment_date", 120), ("period_end", 120), ("total_blocks", 100), ("net_paid", 110)],
        )

    def refresh(self) -> None:
        metrics = self.database.fetch_dashboard_metrics()
        for key, label in self.metric_labels.items():
            value = metrics.get(key, 0)
            if key in {"net_paid_total"}:
                label.configure(text=money(float(value)))
            else:
                label.configure(text=f"{float(value):,.0f}")

        production_rows = self.database.fetch_production_records(limit=8)
        payment_rows = self.database.fetch_payment_history(limit=8)

        assert self.recent_production_tree is not None
        assert self.recent_payments_tree is not None

        for tree in (self.recent_production_tree, self.recent_payments_tree):
            for item in tree.get_children():
                tree.delete(item)

        for row in production_rows:
            self.recent_production_tree.insert(
                "",
                "end",
                values=(row["entry_date"], row["block_type"], row.get("block_color", ""), f'{row["blocks_produced"]:.2f}'),
            )

        for row in payment_rows:
            self.recent_payments_tree.insert(
                "",
                "end",
                values=(row["payment_date"], row["period_end"], f'{row["total_blocks"]:.2f}', money(float(row["net_paid"]))),
            )


class ProductionPage(BasePage):
    def __init__(self, parent, controller: "ConstructionManagementApp") -> None:
        super().__init__(parent, controller)
        self.records_tree: ttk.Treeview | None = None
        self.date_var = tk.StringVar(value=iso_today())
        self.block_type_var = tk.StringVar(value="")
        self.block_color_var = tk.StringVar(value="")
        self.blocks_var = tk.StringVar(value="0")
        self.summary_var = tk.StringVar(value="0 records | 0 blocks")
        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self, style="App.TFrame")
        header.pack(fill="x", padx=24, pady=(20, 12))
        ttk.Label(header, text="Production Management", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Capture the daily production report with only the essentials and review the latest entries instantly.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, style="App.TFrame")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        form_card = self.card(body, "Add Daily Production")
        form_card.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        form = ttk.Frame(form_card, style="Panel.TFrame")
        form.pack(fill="both", expand=True, pady=(14, 0))

        fields = [
            ("Date (YYYY-MM-DD)", self.date_var),
            ("Block Type", self.block_type_var),
            ("Block Color", self.block_color_var),
            ("Blocks Produced", self.blocks_var),
        ]

        for row_index, (label_text, variable) in enumerate(fields):
            ttk.Label(form, text=label_text, style="Field.TLabel").grid(row=row_index, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(form, textvariable=variable, width=28).grid(row=row_index, column=1, sticky="ew", pady=(0, 12))
        form.columnconfigure(1, weight=1)

        button_row = ttk.Frame(form, style="Panel.TFrame")
        button_row.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(button_row, text="Save Production", style="App.TButton", command=self.save_record).pack(side="left")
        ttk.Button(button_row, text="Export PDF", style="Ghost.TButton", command=self.export_report).pack(side="left", padx=8)
        ttk.Button(button_row, text="Clear", style="Ghost.TButton", command=self.clear_form).pack(side="left")

        table_card = self.card(body, "Production History")
        table_card.grid(row=0, column=1, sticky="nsew")
        toolbar = ttk.Frame(table_card, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(14, 12))
        ttk.Label(toolbar, textvariable=self.summary_var, style="PanelMuted.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Delete Selected", style="Ghost.TButton", command=self.delete_selected_record).pack(side="right")
        ttk.Button(toolbar, text="Refresh", style="Ghost.TButton", command=self.refresh).pack(side="right")

        table_host = ttk.Frame(table_card, style="Panel.TFrame")
        table_host.pack(fill="both", expand=True)
        self.records_tree = self.build_tree(
            table_host,
            [
                ("entry_date", 110),
                ("block_type", 160),
                ("block_color", 120),
                ("blocks_produced", 120),
            ],
        )

    def clear_form(self) -> None:
        self.date_var.set(iso_today())
        self.block_type_var.set("")
        self.block_color_var.set("")
        self.blocks_var.set("0")

    def save_record(self) -> None:
        try:
            entry_date = parse_iso_date(self.date_var.get().strip())
            block_type = self.block_type_var.get().strip()
            blocks_produced = parse_float(self.blocks_var.get().strip(), "Blocks Produced")
            if not block_type:
                raise ValueError("Please enter the block type before saving.")
            if blocks_produced <= 0:
                raise ValueError("Blocks produced must be greater than 0.")

            self.database.add_production_record(
                {
                    "entry_date": entry_date,
                    "site_name": "",
                    "customer_name": "",
                    "worker_name": "",
                    "block_type": block_type,
                    "block_color": self.block_color_var.get().strip(),
                    "blocks_produced": blocks_produced,
                    "unit_rate": 0,
                    "total_value": 0,
                    "notes": "",
                }
            )
        except ValueError as error:
            messagebox.showerror("Invalid Production Entry", str(error))
            return

        self.clear_form()
        self.controller.refresh_all()
        self.flash_status("Production report updated.")
        messagebox.showinfo("Saved", "Production record saved successfully.")

    def export_report(self) -> None:
        rows = self.database.fetch_production_records()
        if not rows:
            messagebox.showwarning("No Data", "There are no production records to export.")
            return

        output_path = self.choose_export_path("Export Production Report", "production_report")
        if not output_path:
            return

        summary = self.database.fetch_production_summary()
        report_rows = [
            [
                row["entry_date"],
                row["block_type"],
                row.get("block_color", ""),
                f'{row["blocks_produced"]:.2f}',
            ]
            for row in rows
        ]
        try:
            generate_pdf_report(
                "Production Report",
                ["Date", "Block Type", "Block Color", "Blocks"],
                report_rows,
                output_path,
                summary_lines=[
                    f"Total records: {int(summary['record_count'])}",
                    f"Total blocks: {summary['total_blocks']:.2f}",
                ],
            )
            self.flash_status("Production PDF exported.")
            messagebox.showinfo("Export Complete", f"Production report exported to:\n{output_path}")
        except RuntimeError as error:
            messagebox.showerror("Export Error", str(error))

    def delete_selected_record(self) -> None:
        assert self.records_tree is not None
        record_id = self.selected_item_id(self.records_tree, "Select a production record to delete.")
        if record_id is None:
            return
        if not messagebox.askyesno("Delete Production", "Delete the selected production record?"):
            return

        try:
            self.database.delete_production_record(record_id)
        except ValueError as error:
            messagebox.showerror("Delete Error", str(error))
            return

        self.controller.refresh_all()
        self.flash_status("Production record deleted.")
        messagebox.showinfo("Deleted", "Production record deleted successfully.")

    def refresh(self) -> None:
        rows = self.database.fetch_production_records()
        summary = self.database.fetch_production_summary()

        assert self.records_tree is not None
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

        for row in rows:
            self.records_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["entry_date"],
                    row["block_type"],
                    row.get("block_color", ""),
                    f'{row["blocks_produced"]:.2f}',
                ),
            )

        self.summary_var.set(
            f"{int(summary['record_count'])} records | "
            f"{summary['total_blocks']:.2f} blocks"
        )


class MaterialsPage(BasePage):
    def __init__(self, parent, controller: "ConstructionManagementApp") -> None:
        super().__init__(parent, controller)
        self.inventory_tree: ttk.Treeview | None = None
        self.transactions_tree: ttk.Treeview | None = None
        self.add_name_var = tk.StringVar()
        self.add_unit_var = tk.StringVar(value="Kg")
        self.add_qty_var = tk.StringVar(value="0")
        self.add_reorder_var = tk.StringVar(value="0")
        self.add_ref_var = tk.StringVar()
        self.add_date_var = tk.StringVar(value=iso_today())
        self.use_name_var = tk.StringVar()
        self.use_qty_var = tk.StringVar(value="0")
        self.use_ref_var = tk.StringVar()
        self.use_date_var = tk.StringVar(value=iso_today())
        self.add_notes_text: tk.Text | None = None
        self.use_notes_text: tk.Text | None = None
        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self, style="App.TFrame")
        header.pack(fill="x", padx=24, pady=(20, 12))
        ttk.Label(header, text="Material Management", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Maintain inventory, register material consumption, and keep quantity updates automatic.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, style="App.TFrame")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        side_scroll = ScrollablePanel(body)
        side_scroll.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 14))
        side_scroll.configure(width=420)
        side = side_scroll.content

        add_card = self.card(side, "Add Material Stock")
        add_card.pack(fill="x", pady=(0, 14))
        add_form = ttk.Frame(add_card, style="Panel.TFrame")
        add_form.pack(fill="x", pady=(14, 0))

        add_fields = [
            ("Material Name", self.add_name_var),
            ("Unit", self.add_unit_var),
            ("Quantity", self.add_qty_var),
            ("Reorder Level", self.add_reorder_var),
            ("Reference", self.add_ref_var),
            ("Date (YYYY-MM-DD)", self.add_date_var),
        ]
        for row_index, (label_text, variable) in enumerate(add_fields):
            ttk.Label(add_form, text=label_text, style="Field.TLabel").grid(row=row_index, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(add_form, textvariable=variable, width=28).grid(row=row_index, column=1, sticky="ew", pady=(0, 12))
        add_form.columnconfigure(1, weight=1)

        ttk.Label(add_form, text="Notes", style="Field.TLabel").grid(row=len(add_fields), column=0, sticky="nw", pady=(0, 6))
        self.add_notes_text = tk.Text(
            add_form,
            height=4,
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=FONTS["body"],
            wrap="word",
        )
        self.add_notes_text.grid(row=len(add_fields), column=1, sticky="ew", pady=(0, 12))
        ttk.Button(add_form, text="Add Stock", style="App.TButton", command=self.add_stock).grid(row=len(add_fields) + 1, column=0, columnspan=2, sticky="ew")

        use_card = self.card(side, "Use Material Stock")
        use_card.pack(fill="x")
        use_form = ttk.Frame(use_card, style="Panel.TFrame")
        use_form.pack(fill="x", pady=(14, 0))

        ttk.Label(use_form, text="Material Name", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.material_picker = ttk.Combobox(use_form, textvariable=self.use_name_var, state="readonly")
        self.material_picker.grid(row=0, column=1, sticky="ew", pady=(0, 12))

        use_fields = [
            ("Quantity", self.use_qty_var),
            ("Reference", self.use_ref_var),
            ("Date (YYYY-MM-DD)", self.use_date_var),
        ]
        for row_index, (label_text, variable) in enumerate(use_fields, start=1):
            ttk.Label(use_form, text=label_text, style="Field.TLabel").grid(row=row_index, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(use_form, textvariable=variable, width=28).grid(row=row_index, column=1, sticky="ew", pady=(0, 12))
        use_form.columnconfigure(1, weight=1)

        ttk.Label(use_form, text="Notes", style="Field.TLabel").grid(row=4, column=0, sticky="nw", pady=(0, 6))
        self.use_notes_text = tk.Text(
            use_form,
            height=4,
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=FONTS["body"],
            wrap="word",
        )
        self.use_notes_text.grid(row=4, column=1, sticky="ew", pady=(0, 12))
        ttk.Button(use_form, text="Use Stock", style="App.TButton", command=self.use_stock).grid(row=5, column=0, columnspan=2, sticky="ew")

        inventory_card = self.card(body, "Current Inventory")
        inventory_card.grid(row=0, column=1, sticky="nsew", pady=(0, 14))
        inventory_toolbar = ttk.Frame(inventory_card, style="Panel.TFrame")
        inventory_toolbar.pack(fill="x", pady=(14, 12))
        ttk.Button(inventory_toolbar, text="Delete Selected", style="Ghost.TButton", command=self.delete_selected_inventory_item).pack(side="right")
        ttk.Button(inventory_toolbar, text="Export Inventory PDF", style="Ghost.TButton", command=self.export_inventory_report).pack(side="right")
        inventory_host = ttk.Frame(inventory_card, style="Panel.TFrame")
        inventory_host.pack(fill="both", expand=True)
        self.inventory_tree = self.build_tree(
            inventory_host,
            [("name", 180), ("unit", 90), ("current_quantity", 120), ("reorder_level", 120), ("last_updated", 120)],
        )

        transaction_card = self.card(body, "Material Transaction History")
        transaction_card.grid(row=1, column=1, sticky="nsew")
        transaction_toolbar = ttk.Frame(transaction_card, style="Panel.TFrame")
        transaction_toolbar.pack(fill="x", pady=(14, 12))
        ttk.Button(transaction_toolbar, text="Delete Selected", style="Ghost.TButton", command=self.delete_selected_transaction).pack(side="right")
        ttk.Button(transaction_toolbar, text="Export Transactions PDF", style="Ghost.TButton", command=self.export_transaction_report).pack(side="right")
        transaction_host = ttk.Frame(transaction_card, style="Panel.TFrame")
        transaction_host.pack(fill="both", expand=True)
        self.transactions_tree = self.build_tree(
            transaction_host,
            [("transaction_date", 110), ("material_name", 160), ("transaction_type", 90), ("quantity", 90), ("unit", 80), ("reference", 120)],
        )

    def add_stock(self) -> None:
        try:
            name = self.add_name_var.get().strip()
            unit = self.add_unit_var.get().strip()
            quantity = parse_float(self.add_qty_var.get().strip(), "Quantity")
            reorder_level = parse_float(self.add_reorder_var.get().strip(), "Reorder Level")
            reference = self.add_ref_var.get().strip()
            transaction_date = parse_iso_date(self.add_date_var.get().strip())
            notes = self.add_notes_text.get("1.0", "end").strip() if self.add_notes_text is not None else ""
            if not name or not unit:
                raise ValueError("Material name and unit are required.")
            if quantity <= 0 or reorder_level < 0:
                raise ValueError("Quantity must be greater than 0 and reorder level cannot be negative.")
            self.database.add_material_stock(name, unit, quantity, reorder_level, reference, transaction_date, notes)
        except ValueError as error:
            messagebox.showerror("Invalid Material Entry", str(error))
            return

        self.add_name_var.set("")
        self.add_unit_var.set("Kg")
        self.add_qty_var.set("0")
        self.add_reorder_var.set("0")
        self.add_ref_var.set("")
        self.add_date_var.set(iso_today())
        if self.add_notes_text is not None:
            self.add_notes_text.delete("1.0", "end")
        self.controller.refresh_all()
        self.flash_status("Material stock added.")
        messagebox.showinfo("Saved", "Material stock added successfully.")

    def use_stock(self) -> None:
        try:
            name = self.use_name_var.get().strip()
            quantity = parse_float(self.use_qty_var.get().strip(), "Quantity")
            reference = self.use_ref_var.get().strip()
            transaction_date = parse_iso_date(self.use_date_var.get().strip())
            notes = self.use_notes_text.get("1.0", "end").strip() if self.use_notes_text is not None else ""
            if not name:
                raise ValueError("Please select a material before using stock.")
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0.")
            self.database.use_material_stock(name, quantity, reference, transaction_date, notes)
        except ValueError as error:
            messagebox.showerror("Invalid Material Usage", str(error))
            return

        self.use_qty_var.set("0")
        self.use_ref_var.set("")
        self.use_date_var.set(iso_today())
        if self.use_notes_text is not None:
            self.use_notes_text.delete("1.0", "end")
        self.controller.refresh_all()
        self.flash_status("Material stock updated.")
        messagebox.showinfo("Updated", "Material stock updated successfully.")

    def export_inventory_report(self) -> None:
        rows = self.database.fetch_material_inventory()
        if not rows:
            messagebox.showwarning("No Data", "There is no inventory data to export.")
            return
        output_path = self.choose_export_path("Export Inventory Report", "inventory_report")
        if not output_path:
            return
        report_rows = [
            [row["name"], row["unit"], f'{row["current_quantity"]:.2f}', f'{row["reorder_level"]:.2f}', row["last_updated"]]
            for row in rows
        ]
        try:
            generate_pdf_report("Material Inventory Report", ["Material", "Unit", "Quantity", "Reorder", "Updated"], report_rows, output_path)
            self.flash_status("Inventory PDF exported.")
            messagebox.showinfo("Export Complete", f"Inventory report exported to:\n{output_path}")
        except RuntimeError as error:
            messagebox.showerror("Export Error", str(error))

    def delete_selected_inventory_item(self) -> None:
        assert self.inventory_tree is not None
        item_id = self.selected_item_id(self.inventory_tree, "Select an inventory item to delete.")
        if item_id is None:
            return
        if not messagebox.askyesno(
            "Delete Inventory Item",
            "Delete the selected inventory item and all of its material transaction history?",
        ):
            return

        try:
            self.database.delete_material_inventory_item(item_id)
        except ValueError as error:
            messagebox.showerror("Delete Error", str(error))
            return

        self.controller.refresh_all()
        self.flash_status("Inventory item deleted.")
        messagebox.showinfo("Deleted", "Inventory item deleted successfully.")

    def delete_selected_transaction(self) -> None:
        assert self.transactions_tree is not None
        transaction_id = self.selected_item_id(self.transactions_tree, "Select a material transaction to delete.")
        if transaction_id is None:
            return
        if not messagebox.askyesno(
            "Delete Transaction",
            "Delete the selected material transaction and update inventory automatically?",
        ):
            return

        try:
            self.database.delete_material_transaction(transaction_id)
        except ValueError as error:
            messagebox.showerror("Delete Error", str(error))
            return

        self.controller.refresh_all()
        self.flash_status("Material transaction deleted.")
        messagebox.showinfo("Deleted", "Material transaction deleted successfully.")

    def export_transaction_report(self) -> None:
        rows = self.database.fetch_material_transactions()
        if not rows:
            messagebox.showwarning("No Data", "There are no material transactions to export.")
            return
        output_path = self.choose_export_path("Export Material Transactions Report", "material_transactions")
        if not output_path:
            return
        report_rows = [
            [row["transaction_date"], row["material_name"], row["transaction_type"], f'{row["quantity"]:.2f}', row["unit"], row["reference"]]
            for row in rows
        ]
        try:
            generate_pdf_report("Material Transactions Report", ["Date", "Material", "Type", "Quantity", "Unit", "Reference"], report_rows, output_path)
            self.flash_status("Material transactions PDF exported.")
            messagebox.showinfo("Export Complete", f"Material transaction report exported to:\n{output_path}")
        except RuntimeError as error:
            messagebox.showerror("Export Error", str(error))

    def refresh(self) -> None:
        inventory_rows = self.database.fetch_material_inventory()
        transaction_rows = self.database.fetch_material_transactions()
        material_names = self.database.get_material_names()
        self.material_picker["values"] = material_names
        if self.use_name_var.get() not in material_names:
            self.use_name_var.set(material_names[0] if material_names else "")

        assert self.inventory_tree is not None
        assert self.transactions_tree is not None
        for tree in (self.inventory_tree, self.transactions_tree):
            for item in tree.get_children():
                tree.delete(item)

        for row in inventory_rows:
            self.inventory_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(row["name"], row["unit"], f'{row["current_quantity"]:.2f}', f'{row["reorder_level"]:.2f}', row["last_updated"]),
            )

        for row in transaction_rows:
            self.transactions_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["transaction_date"],
                    row["material_name"],
                    row["transaction_type"],
                    f'{row["quantity"]:.2f}',
                    row["unit"],
                    row["reference"],
                ),
            )


class PaymentsPage(BasePage):
    def __init__(self, parent, controller: "ConstructionManagementApp") -> None:
        super().__init__(parent, controller)
        self.rate_per_block = 2.0
        self.period_start_var = tk.StringVar(value=month_start())
        self.period_end_var = tk.StringVar(value=iso_today())
        self.payment_amount_var = tk.StringVar(value="0")
        self.payment_date_var = tk.StringVar(value=iso_today())
        self.total_blocks_var = tk.StringVar(value="0.00")
        self.gross_var = tk.StringVar(value=money(0))
        self.pending_var = tk.StringVar(value=money(0))
        self.advance_var = tk.StringVar(value=money(0))
        self.notes_text: tk.Text | None = None
        self.history_tree: ttk.Treeview | None = None
        self.view_mode = tk.StringVar(value="calculator")
        self._build()
        self._bind_updates()

    def _build(self) -> None:
        header = ttk.Frame(self, style="App.TFrame")
        header.pack(fill="x", padx=24, pady=(20, 12))
        ttk.Label(header, text="Payments Management", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Calculate salary automatically from production using the formula: blocks x rate per block.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        toggle_row = ttk.Frame(self, style="App.TFrame")
        toggle_row.pack(fill="x", padx=24, pady=(0, 12))
        self.calc_button = ttk.Button(toggle_row, text="Calculator", style="ActiveNav.TButton", command=lambda: self.switch_view("calculator"))
        self.calc_button.pack(side="left")
        self.history_button = ttk.Button(toggle_row, text="Payment History", style="Nav.TButton", command=lambda: self.switch_view("history"))
        self.history_button.pack(side="left", padx=(10, 0))

        self.content = ttk.Frame(self, style="App.TFrame")
        self.content.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        self.calculator_view = ttk.Frame(self.content, style="App.TFrame")
        self.history_view = ttk.Frame(self.content, style="App.TFrame")
        self._build_calculator_view()
        self._build_history_view()
        self.switch_view("calculator")

    def _build_calculator_view(self) -> None:
        self.calculator_view.columnconfigure(0, weight=1)
        self.calculator_view.columnconfigure(1, weight=1)
        self.calculator_view.rowconfigure(0, weight=1)

        form_card = self.card(self.calculator_view, "Salary Calculator")
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        form = ttk.Frame(form_card, style="Panel.TFrame")
        form.pack(fill="both", expand=True, pady=(14, 0))

        fields = [
            ("Period Start", self.period_start_var),
            ("Period End", self.period_end_var),
            ("Payment Amount", self.payment_amount_var),
            ("Payment Date", self.payment_date_var),
        ]
        for row_index, (label_text, variable) in enumerate(fields):
            label = f"{label_text} (YYYY-MM-DD)" if "Period" in label_text or label_text == "Payment Date" else label_text
            ttk.Label(form, text=label, style="Field.TLabel").grid(row=row_index, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(form, textvariable=variable, width=28).grid(row=row_index, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(form, text="Notes", style="Field.TLabel").grid(row=len(fields), column=0, sticky="nw", pady=(0, 6))
        self.notes_text = tk.Text(
            form,
            height=5,
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=FONTS["body"],
            wrap="word",
        )
        self.notes_text.grid(row=len(fields), column=1, sticky="ew", pady=(0, 12))
        form.columnconfigure(1, weight=1)

        button_row = ttk.Frame(form, style="Panel.TFrame")
        button_row.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="ew")
        ttk.Button(button_row, text="Record Payment", style="App.TButton", command=self.record_payment).pack(side="left")
        ttk.Button(button_row, text="Recalculate", style="Ghost.TButton", command=self.recalculate).pack(side="left", padx=8)

        summary_card = self.card(self.calculator_view, "Calculated Salary Details")
        summary_card.grid(row=0, column=1, sticky="nsew")
        summary_card.columnconfigure(0, weight=1)
        metrics_grid = ttk.Frame(summary_card, style="Panel.TFrame")
        metrics_grid.pack(fill="both", expand=True, pady=(14, 12))
        metrics_grid.columnconfigure(0, weight=1)
        metrics_grid.columnconfigure(1, weight=1)

        metric_specs = [
            ("Total Blocks", self.total_blocks_var),
            ("Gross Salary", self.gross_var),
            ("Pending Payment", self.pending_var),
            ("Advance Payment", self.advance_var),
        ]
        for index, (label_text, variable) in enumerate(metric_specs):
            card = ttk.Frame(metrics_grid, style="SoftPanel.TFrame", padding=18)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 10, 0), pady=(0, 10))
            ttk.Label(card, text=label_text, style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=variable, style="Metric.TLabel").pack(anchor="w", pady=(10, 0))

        info_box = ttk.Frame(summary_card, style="SoftPanel.TFrame", padding=18)
        info_box.pack(fill="x")
        ttk.Label(
            info_box,
            text="Gross salary is calculated automatically using the saved production total for the selected date range at Rs. 2 per block. Each payment updates the advance and pending amounts automatically.",
            style="PanelMuted.TLabel",
            wraplength=520,
            justify="left",
        ).pack(anchor="w")

    def _build_history_view(self) -> None:
        history_card = self.card(self.history_view, "Payment History")
        history_card.pack(fill="both", expand=True)
        toolbar = ttk.Frame(history_card, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(14, 12))
        ttk.Button(toolbar, text="Delete Selected", style="Ghost.TButton", command=self.delete_selected_payment).pack(side="right")
        ttk.Button(toolbar, text="Export Payments PDF", style="Ghost.TButton", command=self.export_report).pack(side="right")

        history_host = ttk.Frame(history_card, style="Panel.TFrame")
        history_host.pack(fill="both", expand=True)
        self.history_tree = self.build_tree(
            history_host,
            [
                ("payment_date", 110),
                ("period_start", 110),
                ("period_end", 110),
                ("total_blocks", 90),
                ("gross_salary", 100),
                ("payment_amount", 110),
            ],
        )

    def _bind_updates(self) -> None:
        for variable in (self.period_start_var, self.period_end_var, self.payment_amount_var):
            variable.trace_add("write", lambda *_: self.recalculate())

    def switch_view(self, mode: str) -> None:
        self.view_mode.set(mode)
        self.calculator_view.pack_forget()
        self.history_view.pack_forget()
        if mode == "calculator":
            self.calc_button.configure(style="ActiveNav.TButton")
            self.history_button.configure(style="Nav.TButton")
            self.calculator_view.pack(fill="both", expand=True)
        else:
            self.calc_button.configure(style="Nav.TButton")
            self.history_button.configure(style="ActiveNav.TButton")
            self.history_view.pack(fill="both", expand=True)

    def recalculate(self) -> None:
        try:
            period_start = parse_iso_date(self.period_start_var.get().strip())
            period_end = parse_iso_date(self.period_end_var.get().strip())
            if period_end < period_start:
                return
        except ValueError:
            return

        summary = self.database.calculate_payment_summary(period_start, period_end, self.rate_per_block)
        gross_salary = float(summary["gross_salary"])
        advance_paid = max(float(summary["advance_payment"]), 0)
        pending_payment = max(float(summary["pending_payment"]), 0)
        self.total_blocks_var.set(f"{summary['total_blocks']:.2f}")
        self.gross_var.set(money(gross_salary))
        self.pending_var.set(money(pending_payment))
        self.advance_var.set(money(advance_paid))

    def record_payment(self) -> None:
        try:
            period_start = parse_iso_date(self.period_start_var.get().strip())
            period_end = parse_iso_date(self.period_end_var.get().strip())
            if period_end < period_start:
                raise ValueError("Period end must be on or after period start.")
            payment_date = parse_iso_date(self.payment_date_var.get().strip())
            payment_amount = parse_float(self.payment_amount_var.get().strip(), "Payment Amount")
            if payment_amount <= 0:
                raise ValueError("Payment amount must be greater than 0.")

            calculation = self.database.calculate_payment_summary(period_start, period_end, self.rate_per_block)
            total_blocks = float(calculation["total_blocks"])
            gross_salary = float(calculation["gross_salary"])
            pending_payment = max(float(calculation["pending_payment"]), 0)
            if pending_payment <= 0:
                raise ValueError("There is no pending payment left for the selected period.")
            if payment_amount > pending_payment and pending_payment > 0:
                raise ValueError("Payment amount cannot be greater than the pending payment.")
            if total_blocks <= 0:
                raise ValueError("No production data is available for the selected period.")

            self.database.record_payment(
                {
                    "worker_name": "Production Salary",
                    "period_start": period_start,
                    "period_end": period_end,
                    "total_blocks": total_blocks,
                    "rate_per_block": self.rate_per_block,
                    "gross_salary": gross_salary,
                    "advance_paid": payment_amount,
                    "deductions": 0,
                    "net_paid": round(payment_amount, 2),
                    "payment_date": payment_date,
                    "notes": self.notes_text.get("1.0", "end").strip() if self.notes_text is not None else "",
                }
            )
        except ValueError as error:
            messagebox.showerror("Invalid Payment Entry", str(error))
            return

        self.payment_amount_var.set("0")
        self.payment_date_var.set(iso_today())
        if self.notes_text is not None:
            self.notes_text.delete("1.0", "end")
        self.controller.refresh_all()
        self.flash_status("Payment recorded.")
        messagebox.showinfo("Saved", "Payment recorded successfully.")

    def export_report(self) -> None:
        rows = self.database.fetch_payment_history()
        if not rows:
            messagebox.showwarning("No Data", "There are no payment records to export.")
            return
        output_path = self.choose_export_path("Export Payments Report", "payments_report")
        if not output_path:
            return
        report_rows = [
            [
                row["payment_date"],
                row["period_start"],
                row["period_end"],
                f'{row["total_blocks"]:.2f}',
                f'{row["gross_salary"]:.2f}',
                f'{row["net_paid"]:.2f}',
            ]
            for row in rows
        ]
        total_paid = sum(float(row["net_paid"]) for row in rows)
        try:
            generate_pdf_report(
                "Payments Report",
                ["Date", "Start", "End", "Blocks", "Gross", "Payment Amount"],
                report_rows,
                output_path,
                summary_lines=[f"Total payment records: {len(rows)}", f"Net paid total: {money(total_paid)}"],
            )
            self.flash_status("Payments PDF exported.")
            messagebox.showinfo("Export Complete", f"Payments report exported to:\n{output_path}")
        except RuntimeError as error:
            messagebox.showerror("Export Error", str(error))

    def delete_selected_payment(self) -> None:
        assert self.history_tree is not None
        payment_id = self.selected_item_id(self.history_tree, "Select a payment record to delete.")
        if payment_id is None:
            return
        if not messagebox.askyesno("Delete Payment", "Delete the selected payment record?"):
            return

        try:
            self.database.delete_payment_record(payment_id)
        except ValueError as error:
            messagebox.showerror("Delete Error", str(error))
            return

        self.controller.refresh_all()
        self.flash_status("Payment record deleted.")
        messagebox.showinfo("Deleted", "Payment record deleted successfully.")

    def refresh(self) -> None:
        rows = self.database.fetch_payment_history()
        assert self.history_tree is not None
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for row in rows:
            self.history_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["payment_date"],
                    row["period_start"],
                    row["period_end"],
                    f'{row["total_blocks"]:.2f}',
                    money(float(row["gross_salary"])),
                    money(float(row["net_paid"])),
                ),
            )
        self.recalculate()


class SettingsPage(BasePage):
    def __init__(self, parent, controller: "ConstructionManagementApp") -> None:
        super().__init__(parent, controller)
        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self, style="App.TFrame")
        header.pack(fill="x", padx=24, pady=(20, 12))
        ttk.Label(header, text="Settings", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Use reset carefully. It clears the saved application data and keeps the app ready for a fresh start.",
            style="Muted.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self, style="App.TFrame")
        content.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        reset_card = self.card(content, "Application Reset")
        reset_card.pack(anchor="nw", fill="x")
        ttk.Label(
            reset_card,
            text="This removes all saved production, materials, and payment data from the local database. Exported PDF files are not removed.",
            style="PanelMuted.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(14, 16))
        ttk.Button(reset_card, text="Reset Application Data", style="App.TButton", command=self.reset_application_data).pack(anchor="w")

    def reset_application_data(self) -> None:
        if not messagebox.askyesno(
            "Reset Application",
            "This will permanently delete all saved application data. Do you want to continue?",
        ):
            return
        if not messagebox.askyesno(
            "Confirm Reset",
            "Please confirm again to reset production, materials, and payment records.",
        ):
            return

        self.database.reset_application_data()
        self.controller.refresh_all()
        self.controller.show_page("dashboard")
        self.flash_status("Application data reset.")
        messagebox.showinfo("Reset Complete", "All application data has been reset.")


class ConstructionManagementApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SS Construction Management System")
        self.geometry("1440x860")
        self.minsize(1240, 760)
        self.configure(bg=COLORS["bg"])
        self._icon_image: tk.PhotoImage | None = None
        self._set_app_icon()

        self.database = DatabaseManager()
        configure_ttk_styles(self)

        self.nav_buttons: dict[str, ttk.Button] = {}
        self.pages: dict[str, BasePage] = {}
        self._page_animation_after_id: str | None = None
        self._status_animation_after_id: str | None = None
        self._active_page_name: str | None = None
        self.status_var = tk.StringVar(value="Ready for daily updates.")
        self._status_chip_bg = COLORS["panel_soft"]
        self._status_after_id: str | None = None
        self.page_status = {
            "dashboard": "Overview of recent production, stock quantity, and recent payments.",
            "production": "Capture the daily block production report in a few seconds.",
            "materials": "Add or use stock, then scroll naturally through the material controls.",
            "payments": "Calculate payments from total production within the selected date range.",
            "settings": "Reset the local application data when you need a clean slate.",
        }
        self._build_shell()
        self._build_pages()
        self._apply_micro_interactions(self)
        self.show_page("dashboard")

    def _set_app_icon(self) -> None:
        png_path = resource_path("app", "assets", "app_icon.png")
        ico_path = resource_path("app", "assets", "app_icon.ico")

        if png_path.exists():
            self._icon_image = tk.PhotoImage(file=str(png_path))
            self.iconphoto(True, self._icon_image)

        if ico_path.exists():
            try:
                self.iconbitmap(default=str(ico_path))
            except tk.TclError:
                pass

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg=COLORS["panel"], width=250, bd=0, highlightthickness=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        branding = tk.Frame(sidebar, bg=COLORS["panel"], padx=20, pady=20)
        branding.pack(fill="x")
        tk.Label(branding, text="SS Construction", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
        tk.Label(branding, text="Management System", bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["subtitle"]).pack(anchor="w", pady=(4, 0))

        nav = tk.Frame(sidebar, bg=COLORS["panel"], padx=16, pady=16)
        nav.pack(fill="x")
        menu_items = [
            ("dashboard", "Dashboard"),
            ("production", "Production"),
            ("materials", "Materials"),
            ("payments", "Payments"),
        ]
        for key, label in menu_items:
            button = ttk.Button(nav, text=label, style="Nav.TButton", command=lambda name=key: self.show_page(name))
            button.pack(fill="x", pady=6)
            self.nav_buttons[key] = button

        sidebar_footer = tk.Frame(sidebar, bg=COLORS["panel"], padx=20, pady=18)
        sidebar_footer.pack(side="bottom", fill="x")
        settings_button = ttk.Button(sidebar_footer, text="Settings", style="Nav.TButton", command=lambda: self.show_page("settings"))
        settings_button.pack(fill="x", pady=(0, 14))
        self.nav_buttons["settings"] = settings_button
        tk.Label(
            sidebar_footer,
            text="Desktop software for production,\ninventory, and worker payments.",
            justify="left",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
        ).pack(anchor="w")

        main_area = tk.Frame(self, bg=COLORS["bg"], bd=0, highlightthickness=0)
        main_area.grid(row=0, column=1, sticky="nsew")
        main_area.grid_rowconfigure(1, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        topbar = tk.Frame(main_area, bg=COLORS["bg"], padx=24, pady=18)
        topbar.grid(row=0, column=0, sticky="ew")
        tk.Label(
            topbar,
            text="Construction operations, designed for daily office use",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
        ).pack(anchor="w")
        self.status_chip = tk.Frame(topbar, bg=self._status_chip_bg, padx=12, pady=7, bd=0, highlightthickness=0)
        self.status_chip.pack(anchor="w", pady=(8, 0))
        self.status_label = tk.Label(
            self.status_chip,
            textvariable=self.status_var,
            bg=self._status_chip_bg,
            fg=COLORS["accent_hover"],
            font=("Segoe UI Semibold", 10),
        )
        self.status_label.pack(anchor="w")

        self.page_host = ttk.Frame(main_area, style="App.TFrame")
        self.page_host.grid(row=1, column=0, sticky="nsew")

    def _build_pages(self) -> None:
        self.pages = {
            "dashboard": DashboardPage(self.page_host, self),
            "production": ProductionPage(self.page_host, self),
            "materials": MaterialsPage(self.page_host, self),
            "payments": PaymentsPage(self.page_host, self),
            "settings": SettingsPage(self.page_host, self),
        }
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            page.lower()
            page.refresh()

    def show_page(self, name: str) -> None:
        for key, button in self.nav_buttons.items():
            button.configure(style="ActiveNav.TButton" if key == name else "Nav.TButton")
        page = self.pages[name]
        page.lift()
        self._animate_page_transition(page)
        page.refresh()
        self._active_page_name = name
        self.set_status(self.page_status.get(name, "Ready."))

    def refresh_all(self) -> None:
        for page in self.pages.values():
            page.refresh()

    def set_status(self, message: str) -> None:
        if self._status_after_id is not None:
            self.after_cancel(self._status_after_id)
            self._status_after_id = None
        self.status_var.set(message)
        self._animate_status_chip("accent")

    def flash_status(self, message: str, timeout_ms: int = 2600) -> None:
        self.set_status(message)
        self._status_after_id = self.after(timeout_ms, lambda: self.set_status("Ready for the next update."))

    def _apply_micro_interactions(self, widget) -> None:
        if isinstance(widget, ttk.Button):
            self._bind_button_micro_interactions(widget)
        elif isinstance(widget, ttk.Combobox):
            self._bind_combobox_micro_interactions(widget)
        elif isinstance(widget, ttk.Entry):
            self._bind_entry_micro_interactions(widget)
        elif isinstance(widget, ttk.Treeview):
            self._bind_tree_micro_interactions(widget)
        elif isinstance(widget, tk.Text):
            self._bind_text_micro_interactions(widget)

        for child in widget.winfo_children():
            self._apply_micro_interactions(child)

    def _bind_button_micro_interactions(self, widget: ttk.Button) -> None:
        widget.configure(cursor="hand2")
        base_style = widget.cget("style") or "TButton"
        hover_style = {
            "App.TButton": "AppHover.TButton",
            "Ghost.TButton": "GhostHover.TButton",
            "Nav.TButton": "NavHover.TButton",
            "ActiveNav.TButton": "ActiveNavHover.TButton",
        }.get(base_style)
        pressed_style = {
            "App.TButton": "AppPressed.TButton",
            "Ghost.TButton": "GhostPressed.TButton",
            "Nav.TButton": "NavPressed.TButton",
            "ActiveNav.TButton": "ActiveNavPressed.TButton",
        }.get(base_style)

        def current_base_style() -> str:
            current_style = widget.cget("style") or base_style
            if current_style in {hover_style, pressed_style}:
                if widget in self.nav_buttons.values():
                    return "ActiveNav.TButton" if current_style.startswith("ActiveNav") or self._is_active_nav_button(widget) else "Nav.TButton"
                return base_style
            return current_style

        widget.bind(
            "<Enter>",
            lambda _event: widget.configure(style=hover_style or current_base_style()),
            add="+",
        )
        widget.bind(
            "<Leave>",
            lambda _event: widget.configure(style=current_base_style()),
            add="+",
        )
        widget.bind(
            "<ButtonPress-1>",
            lambda _event: widget.configure(style=pressed_style or current_base_style()),
            add="+",
        )
        widget.bind(
            "<ButtonRelease-1>",
            lambda _event: widget.configure(style=(hover_style if self._pointer_inside(widget) else current_base_style()) or current_base_style()),
            add="+",
        )

    def _bind_entry_micro_interactions(self, widget: ttk.Entry) -> None:
        widget.bind("<FocusIn>", lambda _event: widget.configure(style="Focus.TEntry"), add="+")
        widget.bind("<FocusOut>", lambda _event: widget.configure(style="TEntry"), add="+")

    def _bind_combobox_micro_interactions(self, widget: ttk.Combobox) -> None:
        widget.configure(cursor="hand2")
        widget.bind("<FocusIn>", lambda _event: widget.configure(style="Focus.TCombobox"), add="+")
        widget.bind("<FocusOut>", lambda _event: widget.configure(style="TCombobox"), add="+")

    def _bind_text_micro_interactions(self, widget: tk.Text) -> None:
        default_bg = widget.cget("bg")
        widget.bind("<FocusIn>", lambda _event, w=widget: w.configure(bg=COLORS["panel_hover"]), add="+")
        widget.bind("<FocusOut>", lambda _event, w=widget, bg=default_bg: w.configure(bg=bg), add="+")

    def _bind_tree_micro_interactions(self, widget: ttk.Treeview) -> None:
        widget.bind("<Enter>", lambda _event: widget.configure(cursor="hand2"), add="+")
        widget.bind("<Leave>", lambda _event: widget.configure(cursor=""), add="+")
        widget.bind("<<TreeviewSelect>>", lambda _event: self._animate_status_chip("neutral"), add="+")

    def _pointer_inside(self, widget) -> bool:
        try:
            pointer_x = widget.winfo_pointerx()
            pointer_y = widget.winfo_pointery()
            return widget.winfo_containing(pointer_x, pointer_y) == widget
        except tk.TclError:
            return False

    def _is_active_nav_button(self, widget: ttk.Button) -> bool:
        return self._active_page_name is not None and self.nav_buttons.get(self._active_page_name) is widget

    def _animate_page_transition(self, page: ttk.Frame) -> None:
        if self._page_animation_after_id is not None:
            self.after_cancel(self._page_animation_after_id)
            self._page_animation_after_id = None

        offsets = [26, 18, 12, 7, 3, 0]

        def step(index: int = 0) -> None:
            page.place_configure(x=offsets[index])
            if index < len(offsets) - 1:
                self._page_animation_after_id = self.after(20, lambda: step(index + 1))
            else:
                self._page_animation_after_id = None

        step()

    def _animate_status_chip(self, tone: str) -> None:
        tone_map = {
            "accent": (COLORS["accent_soft"], COLORS["accent_hover"]),
            "neutral": (COLORS["panel_hover"], COLORS["text"]),
            "success": (COLORS["success_soft"], COLORS["success"]),
            "danger": (COLORS["danger_soft"], COLORS["danger"]),
        }
        target_bg, target_fg = tone_map.get(tone, tone_map["accent"])
        start_bg = self._status_chip_bg

        if self._status_animation_after_id is not None:
            self.after_cancel(self._status_animation_after_id)
            self._status_animation_after_id = None

        steps = 7

        def step(index: int = 0) -> None:
            progress = index / steps
            current_bg = blend_color(start_bg, target_bg, progress)
            self.status_chip.configure(bg=current_bg)
            self.status_label.configure(bg=current_bg, fg=target_fg)
            self._status_chip_bg = current_bg
            if index < steps:
                self._status_animation_after_id = self.after(26, lambda: step(index + 1))
            else:
                self._status_animation_after_id = None

        step()
