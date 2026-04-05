from __future__ import annotations

from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except ImportError:  # pragma: no cover - handled in runtime
    colors = None
    A4 = None
    getSampleStyleSheet = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None


def generate_pdf_report(title: str, columns: list[str], rows: list[list[object]], output_path: str, summary_lines: list[str] | None = None) -> str:
    if SimpleDocTemplate is None:
        raise RuntimeError("reportlab is not installed. Install requirements.txt before generating PDF reports.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=24, rightMargin=24, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    for line in summary_lines or []:
        story.append(Paragraph(line, styles["BodyText"]))
    if summary_lines:
        story.append(Spacer(1, 10))

    table_data = [columns]
    for row in rows:
        table_data.append([str(item) for item in row])

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9ca3af")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f3f4f6")]),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return str(path)
