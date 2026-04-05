from __future__ import annotations

import sqlite3
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path


class DatabaseManager:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        self.export_dir = base_dir / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path(db_path).resolve().parent if db_path else base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path).resolve() if db_path else self.data_dir / "ss_construction_runtime_clean.db"
        self.initialize()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        # Keep the journal in memory so the database remains reliable inside synced folders.
        connection.execute("PRAGMA journal_mode=MEMORY")
        connection.execute("PRAGMA synchronous=NORMAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    phone TEXT DEFAULT '',
                    role TEXT DEFAULT 'Worker',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    site_name TEXT DEFAULT '',
                    contact_info TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS production_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date TEXT NOT NULL,
                    site_name TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    worker_name TEXT NOT NULL,
                    block_type TEXT NOT NULL,
                    blocks_produced REAL NOT NULL,
                    unit_rate REAL NOT NULL,
                    total_value REAL NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS material_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    unit TEXT NOT NULL,
                    current_quantity REAL NOT NULL DEFAULT 0,
                    reorder_level REAL NOT NULL DEFAULT 0,
                    last_updated TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS material_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_name TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT NOT NULL,
                    reference TEXT DEFAULT '',
                    transaction_date TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS payment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_name TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    total_blocks REAL NOT NULL,
                    rate_per_block REAL NOT NULL,
                    gross_salary REAL NOT NULL,
                    advance_paid REAL NOT NULL DEFAULT 0,
                    deductions REAL NOT NULL DEFAULT 0,
                    net_paid REAL NOT NULL,
                    payment_date TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_column(conn, "production_records", "block_color", "TEXT NOT NULL DEFAULT ''")

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def add_production_record(self, payload: dict[str, object]) -> None:
        with self.connection() as conn:
            worker_name = str(payload.get("worker_name", "")).strip()
            customer_name = str(payload.get("customer_name", "")).strip()
            site_name = str(payload.get("site_name", "")).strip()
            if worker_name:
                conn.execute("INSERT OR IGNORE INTO workers (name) VALUES (?)", (worker_name,))
            if customer_name:
                conn.execute(
                    "INSERT OR IGNORE INTO customers (name, site_name) VALUES (?, ?)",
                    (customer_name, site_name),
                )
            conn.execute(
                """
                INSERT INTO production_records
                (entry_date, site_name, customer_name, worker_name, block_type, block_color, blocks_produced, unit_rate, total_value, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["entry_date"],
                    site_name,
                    customer_name,
                    worker_name,
                    payload["block_type"],
                    payload.get("block_color", ""),
                    payload["blocks_produced"],
                    payload.get("unit_rate", 0),
                    payload.get("total_value", 0),
                    payload.get("notes", ""),
                ),
            )

    def fetch_production_records(self, limit: int | None = None) -> list[dict[str, object]]:
        query = "SELECT * FROM production_records ORDER BY entry_date DESC, id DESC"
        params: tuple[object, ...] = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def fetch_production_summary(self) -> dict[str, float]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS record_count,
                    COALESCE(SUM(blocks_produced), 0) AS total_blocks,
                    COALESCE(SUM(total_value), 0) AS total_value
                FROM production_records
                """
            ).fetchone()
        return dict(row)

    def delete_production_record(self, record_id: int) -> None:
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM production_records WHERE id = ?", (record_id,))
            if cursor.rowcount == 0:
                raise ValueError("Production record not found.")
            self._remove_unused_people(conn)

    def add_material_stock(
        self,
        name: str,
        unit: str,
        quantity: float,
        reorder_level: float,
        reference: str,
        transaction_date: str,
        notes: str,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO material_inventory (name, unit, current_quantity, reorder_level, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    unit=excluded.unit,
                    current_quantity=material_inventory.current_quantity + excluded.current_quantity,
                    reorder_level=CASE
                        WHEN excluded.reorder_level > 0 THEN excluded.reorder_level
                        ELSE material_inventory.reorder_level
                    END,
                    last_updated=excluded.last_updated
                """,
                (name, unit, quantity, reorder_level, transaction_date),
            )
            conn.execute(
                """
                INSERT INTO material_transactions
                (material_name, transaction_type, quantity, unit, reference, transaction_date, notes)
                VALUES (?, 'IN', ?, ?, ?, ?, ?)
                """,
                (name, quantity, unit, reference, transaction_date, notes),
            )

    def use_material_stock(self, name: str, quantity: float, reference: str, transaction_date: str, notes: str) -> None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT unit, current_quantity FROM material_inventory WHERE name = ?",
                (name,),
            ).fetchone()
            if row is None:
                raise ValueError("Material not found in inventory.")
            if quantity > row["current_quantity"]:
                raise ValueError("Insufficient stock available for this material.")

            conn.execute(
                """
                UPDATE material_inventory
                SET current_quantity = current_quantity - ?, last_updated = ?
                WHERE name = ?
                """,
                (quantity, transaction_date, name),
            )
            conn.execute(
                """
                INSERT INTO material_transactions
                (material_name, transaction_type, quantity, unit, reference, transaction_date, notes)
                VALUES (?, 'OUT', ?, ?, ?, ?, ?)
                """,
                (name, quantity, row["unit"], reference, transaction_date, notes),
            )

    def fetch_material_inventory(self) -> list[dict[str, object]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM material_inventory ORDER BY name COLLATE NOCASE ASC").fetchall()
        return [dict(row) for row in rows]

    def fetch_material_transactions(self, limit: int | None = None) -> list[dict[str, object]]:
        query = "SELECT * FROM material_transactions ORDER BY transaction_date DESC, id DESC"
        params: tuple[object, ...] = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def delete_material_inventory_item(self, item_id: int) -> None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT name FROM material_inventory WHERE id = ?",
                (item_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Inventory item not found.")

            material_name = row["name"]
            conn.execute("DELETE FROM material_transactions WHERE material_name = ?", (material_name,))
            conn.execute("DELETE FROM material_inventory WHERE id = ?", (item_id,))

    def delete_material_transaction(self, transaction_id: int) -> None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, material_name, transaction_type, quantity, transaction_date
                FROM material_transactions
                WHERE id = ?
                """,
                (transaction_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Material transaction not found.")

            inventory = conn.execute(
                "SELECT id, current_quantity, reorder_level FROM material_inventory WHERE name = ?",
                (row["material_name"],),
            ).fetchone()
            if inventory is None:
                raise ValueError("The related inventory item is missing, so this transaction cannot be deleted safely.")

            quantity = float(row["quantity"])
            current_quantity = float(inventory["current_quantity"])

            if row["transaction_type"] == "IN":
                if current_quantity < quantity:
                    raise ValueError(
                        "This stock-in entry cannot be deleted because some of that quantity has already been used."
                    )
                updated_quantity = current_quantity - quantity
            elif row["transaction_type"] == "OUT":
                updated_quantity = current_quantity + quantity
            else:
                raise ValueError("Unsupported transaction type.")

            conn.execute(
                """
                UPDATE material_inventory
                SET current_quantity = ?, last_updated = ?
                WHERE id = ?
                """,
                (updated_quantity, row["transaction_date"], inventory["id"]),
            )
            conn.execute("DELETE FROM material_transactions WHERE id = ?", (transaction_id,))

    def get_material_names(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT name FROM material_inventory ORDER BY name COLLATE NOCASE ASC").fetchall()
        return [row["name"] for row in rows]

    def get_worker_names(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT name FROM workers ORDER BY name COLLATE NOCASE ASC").fetchall()
        return [row["name"] for row in rows]

    def calculate_payment_summary(
        self,
        period_start: str,
        period_end: str,
        rate_per_block: float,
        worker_name: str | None = None,
    ) -> dict[str, float]:
        query = """
            SELECT COALESCE(SUM(blocks_produced), 0) AS total_blocks
            FROM production_records
            WHERE entry_date BETWEEN ? AND ?
        """
        params: list[object] = [period_start, period_end]
        if worker_name:
            query += " AND worker_name = ?"
            params.append(worker_name)

        with self.connection() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        total_blocks = float(row["total_blocks"])
        paid_total = self.fetch_paid_total(period_start, period_end)
        return {
            "total_blocks": total_blocks,
            "gross_salary": round(total_blocks * rate_per_block, 2),
            "advance_payment": round(paid_total, 2),
            "pending_payment": round((total_blocks * rate_per_block) - paid_total, 2),
        }

    def calculate_worker_payment(self, worker_name: str, period_start: str, period_end: str, rate_per_block: float) -> dict[str, float]:
        return self.calculate_payment_summary(period_start, period_end, rate_per_block, worker_name=worker_name)

    def record_payment(self, payload: dict[str, object]) -> None:
        with self.connection() as conn:
            worker_name = str(payload.get("worker_name", "")).strip() or "Production Salary"
            conn.execute("INSERT OR IGNORE INTO workers (name) VALUES (?)", (worker_name,))
            conn.execute(
                """
                INSERT INTO payment_history
                (worker_name, period_start, period_end, total_blocks, rate_per_block, gross_salary, advance_paid, deductions, net_paid, payment_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    worker_name,
                    payload["period_start"],
                    payload["period_end"],
                    payload["total_blocks"],
                    payload["rate_per_block"],
                    payload["gross_salary"],
                    payload["advance_paid"],
                    payload["deductions"],
                    payload["net_paid"],
                    payload["payment_date"],
                    payload.get("notes", ""),
                ),
            )

    def fetch_payment_history(self, limit: int | None = None) -> list[dict[str, object]]:
        query = "SELECT * FROM payment_history ORDER BY payment_date DESC, id DESC"
        params: tuple[object, ...] = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def delete_payment_record(self, payment_id: int) -> None:
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM payment_history WHERE id = ?", (payment_id,))
            if cursor.rowcount == 0:
                raise ValueError("Payment record not found.")
            self._remove_unused_people(conn)

    def fetch_paid_total(self, period_start: str, period_end: str) -> float:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(net_paid), 0) AS paid_total
                FROM payment_history
                WHERE period_start = ? AND period_end = ?
                """,
                (period_start, period_end),
            ).fetchone()
        return float(row["paid_total"])

    def fetch_dashboard_metrics(self) -> dict[str, float]:
        with self.connection() as conn:
            production = conn.execute(
                """
                SELECT
                    COUNT(*) AS production_entries,
                    COALESCE(SUM(blocks_produced), 0) AS total_blocks,
                    COALESCE(SUM(total_value), 0) AS production_value
                FROM production_records
                """
            ).fetchone()
            inventory = conn.execute(
                """
                SELECT
                    COUNT(*) AS material_types,
                    COALESCE(SUM(current_quantity), 0) AS total_material_quantity,
                    COALESCE(SUM(CASE WHEN reorder_level > 0 AND current_quantity <= reorder_level THEN 1 ELSE 0 END), 0) AS low_stock_items
                FROM material_inventory
                """
            ).fetchone()
            payments = conn.execute(
                """
                SELECT
                    COUNT(*) AS payments_count,
                    COALESCE(SUM(net_paid), 0) AS net_paid_total
                FROM payment_history
                """
            ).fetchone()

        return {
            "production_entries": production["production_entries"],
            "total_blocks": production["total_blocks"],
            "production_value": production["production_value"],
            "material_types": inventory["material_types"],
            "total_material_quantity": inventory["total_material_quantity"],
            "low_stock_items": inventory["low_stock_items"],
            "payments_count": payments["payments_count"],
            "net_paid_total": payments["net_paid_total"],
        }

    def reset_application_data(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM payment_history")
            conn.execute("DELETE FROM material_transactions")
            conn.execute("DELETE FROM material_inventory")
            conn.execute("DELETE FROM production_records")
            conn.execute("DELETE FROM customers")
            conn.execute("DELETE FROM workers")
            conn.execute("DELETE FROM sqlite_sequence")

    def _remove_unused_people(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            DELETE FROM workers
            WHERE TRIM(name) <> ''
              AND name NOT IN (SELECT DISTINCT worker_name FROM production_records WHERE TRIM(worker_name) <> '')
              AND name NOT IN (SELECT DISTINCT worker_name FROM payment_history WHERE TRIM(worker_name) <> '')
            """
        )
        conn.execute(
            """
            DELETE FROM customers
            WHERE TRIM(name) <> ''
              AND name NOT IN (SELECT DISTINCT customer_name FROM production_records WHERE TRIM(customer_name) <> '')
            """
        )

    def default_report_path(self, report_name: str) -> str:
        stamp = date.today().isoformat()
        return str(self.export_dir / f"{report_name}_{stamp}.pdf")
