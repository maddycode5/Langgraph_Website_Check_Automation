"""Script to generate the reference criteria PDF (criteria_reference.pdf)
Used as the benchmark rubric for website evaluations in the pipeline.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_criteria_pdf(output_path: Path) -> Path:
    """Creates a publication-grade criteria reference PDF for website auditing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Header
    story.append(Paragraph("WEBSITE AUDIT EVALUATION BENCHMARK", title_style))
    story.append(Paragraph("Standardized 5-Pillar Evaluation Criteria & Scoring Rubric (v2.4)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=15))

    overview_text = (
        "This reference framework establishes rigorous standards for assessing commercial and SaaS websites. "
        "Each dimension is scored on an objective 1 to 10 scale, where 1 represents severe commercial risk and 10 represents industry-leading execution. "
        "Every finding must be backed by verifiable verbatim quotes or observable metrics directly extracted from the target website."
    )
    story.append(Paragraph(overview_text, body_style))
    story.append(Spacer(1, 12))

    # The 5 Audit Pillars
    pillars = [
        (
            "1. Technical SEO & Metadata",
            [
                ("Title Tag Optimization", "Specific, keyword-relevant, between 40-60 characters, with company branding."),
                ("Meta Description & OpenGraph", "Compelling summary under 160 characters. Proper og:title and og:image tags."),
                ("Semantic Heading Hierarchy", "Single, high-impact H1 describing core offering; logical H2/H3 sub-structure."),
                ("Crawlability & Canonicalization", "Proper canonical tags, robots directives, and search bot friendly internal linking.")
            ]
        ),
        (
            "2. Speed, Performance & Mobile Responsiveness",
            [
                ("Initial Page Load Speed", "Server response time (TTFB) < 600ms; multi-page requests succeed without timeout."),
                ("Viewport & Mobile Meta", "Accurate viewport declaration: width=device-width, initial-scale=1.0."),
                ("Resource Bloat & Scripting", "Excessive third-party trackers, uncompressed media assets, and blocking scripts.")
            ]
        ),
        (
            "3. Content Clarity & Value Proposition",
            [
                ("Hero Section Clarity (5-Second Test)", "Visitors must understand within 5 seconds: What is offered, for whom, and why it matters."),
                ("Benefit vs. Feature Ratio", "Focus on customer outcomes and quantified impact rather than self-referential jargon."),
                ("Readability & Typography", "Scannable typography, descriptive subheadings, bullet points, and concise paragraphs.")
            ]
        ),
        (
            "4. Conversion Architecture & UX",
            [
                ("Call-to-Action (CTA) Prominence", "High-contrast, benefit-oriented CTA visible above the fold and at key decision points."),
                ("Form Friction & Lead Capture", "Minimal input fields for top-of-funnel conversion; low cognitive friction."),
                ("Navigation Simplicity", "Clean primary header menu with no more than 5-7 intuitive top-level navigation items.")
            ]
        ),
        (
            "5. Trust Signals, Security & Compliance",
            [
                ("SSL & HTTPS Security", "Secure transport protocol across all assets with valid certificates."),
                ("Social Proof & Testimonials", "Named customer testimonials, verifiable logos, case studies, or metric proof."),
                ("Clear Contact & Legal Info", "Accessible physical address, support email/phone, privacy policy, and terms of service.")
            ]
        )
    ]

    for title, items in pillars:
        story.append(Paragraph(title, h2_style))
        table_data = [[Paragraph("Evaluation Factor", bold_body), Paragraph("Standard & Benchmark Expectation", bold_body)]]
        for factor, desc in items:
            table_data.append([Paragraph(factor, bold_body), Paragraph(desc, body_style)])

        t = Table(table_data, colWidths=[160, 344])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    # Scoring Scale Table
    story.append(Paragraph("Scoring Scale & Classification", h2_style))
    scale_data = [
        [Paragraph("Score Band", bold_body), Paragraph("Classification", bold_body), Paragraph("Action Required", bold_body)],
        [Paragraph("1 - 4", bold_body), Paragraph("Critical Deficiency", body_style), Paragraph("Immediate technical or messaging overhaul necessary.", body_style)],
        [Paragraph("5 - 6", bold_body), Paragraph("Below Benchmark", body_style), Paragraph("Noticeable conversion leaks and missed revenue opportunities.", body_style)],
        [Paragraph("7 - 8", bold_body), Paragraph("Competitive Standard", body_style), Paragraph("Solid execution; tactical enhancements will yield gains.", body_style)],
        [Paragraph("9 - 10", bold_body), Paragraph("Exemplary", body_style), Paragraph("Benchmark-setting execution; minimal friction.", body_style)]
    ]
    st_table = Table(scale_data, colWidths=[100, 160, 244])
    st_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(st_table)

    doc.build(story)
    return output_path


if __name__ == "__main__":
    from config import CRITERIA_PDF_PATH
    pdf_out = generate_criteria_pdf(CRITERIA_PDF_PATH)
    print(f"Criteria reference PDF successfully generated at: {pdf_out}")
