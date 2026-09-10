from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.audit_reporting import AuditReportData


def generate_audit_report_pdf(report: AuditReportData) -> bytes:
    """
    Gera o PDF consolidado de uma auditoria: dados da empresa/auditoria,
    resumo por status e, por controle, a lista de evidências anexadas com
    quem enviou e quando. Função pura — recebe os dados já carregados
    (AuditReportData, ver services/audit_reporting.py), sem acesso a banco
    de dados, o que a torna testável sem precisar de um SQLAlchemy Session
    real (ver proposta L.3, seção 10).

    Decisão de biblioteca: reportlab, não weasyprint. weasyprint depende
    de binários nativos (Cairo/Pango/GDK) que precisariam ser instalados
    na imagem Docker de produção (backend/Dockerfile), inflando a imagem
    e contrariando o objetivo de imagem enxuta já estabelecido no BLOCO H
    (multi-stage, base python:3.12-slim). reportlab é 100% Python puro,
    sem dependência de sistema — trade-off aceito: o layout é montado via
    API (Paragraph/Table/Spacer), não HTML/CSS.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Relatório de Auditoria — {report.name}", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"Cliente: {report.client_name}", styles["Normal"]))
    story.append(Paragraph(f"Status: {report.status}", styles["Normal"]))
    story.append(
        Paragraph(
            f"Criada em: {report.created_at.strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 1 * cm))

    status_counts: dict[str, int] = {}
    for control in report.controls:
        status_counts[control.status] = status_counts.get(control.status, 0) + 1
    resumo = ", ".join(
        f"{status}: {count}" for status, count in sorted(status_counts.items())
    )
    story.append(
        Paragraph(f"Resumo por status: {resumo or 'nenhum controle'}", styles["Normal"])
    )
    story.append(Spacer(1, 1 * cm))

    for control in report.controls:
        story.append(
            Paragraph(
                f"{control.control_code} — {control.control_title}", styles["Heading3"]
            )
        )
        story.append(Paragraph(f"Status: {control.status}", styles["Normal"]))

        if control.evidences:
            data = [["Arquivo", "Enviado por", "Data"]]
            for evidence in control.evidences:
                data.append(
                    [
                        evidence.file_name,
                        evidence.uploaded_by_name,
                        evidence.created_at.strftime("%d/%m/%Y %H:%M"),
                    ]
                )
            table = Table(data, colWidths=[8 * cm, 5 * cm, 4 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#262626")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c5c6cd")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(Paragraph("Nenhuma evidência anexada.", styles["Normal"]))

        story.append(Spacer(1, 0.6 * cm))

    doc.build(story)
    return buffer.getvalue()
