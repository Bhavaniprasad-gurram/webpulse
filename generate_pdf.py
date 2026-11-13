import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 755, "WebPulse — Project Architecture & Presentation Guide")
            self.drawRightString(612 - 54, 755, "Confidential & Portfolio Presentation")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(54, 748, 612 - 54, 748)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 34, footer_text)
        self.drawString(54, 34, "WebPulse Monitoring Platform | Built with Python, Streamlit & MySQL")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(54, 46, 612 - 54, 46)

        self.restoreState()


def build_presentation_pdf(output_filename="WebPulse_Project_Presentation.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    navy = colors.HexColor("#0f172a")
    blue = colors.HexColor("#2563eb")
    slate_dark = colors.HexColor("#334155")
    slate_muted = colors.HexColor("#64748b")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#e2e8f0")
    green_accent = colors.HexColor("#10b981")

    # Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=navy,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=blue,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=navy,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SubSectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=blue,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=slate_dark,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletPoint",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=slate_dark,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4,
    )

    code_callout_style = ParagraphStyle(
        "CodeCallout",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )

    elements = []

    # ==========================================
    # Header & Cover Title
    # ==========================================
    elements.append(Paragraph("WebPulse", title_style))
    elements.append(Paragraph("Website Availability & Downtime Observability Platform", subtitle_style))
    elements.append(
        Paragraph(
            "<b>Project Type:</b> Full-Stack Python & Database Engineering | "
            "<b>Audience:</b> Technical Presentation & Developer Portfolio | "
            "<b>Status:</b> Production Ready",
            body_style,
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1.5, color=blue, spaceBefore=4, spaceAfter=14))

    # ==========================================
    # Section 1: Executive Summary & Purpose
    # ==========================================
    elements.append(Paragraph("1. Executive Summary & Problem Statement", h1_style))
    elements.append(
        Paragraph(
            "Every modern digital service relies on external web apps, APIs, and cloud microservices. "
            "When these endpoints suffer downtime or degrade in performance, businesses face lost revenue, "
            "tarnished brand reputation, and missed SLAs. Traditional ping utilities are insufficient because "
            "they fail to test real HTTP handshakes, ignore SSL expiration, and often misinterpret temporary network "
            "jitters as major outages.",
            body_style,
        )
    )
    elements.append(
        Paragraph(
            "<b>WebPulse</b> is an automated, real-time website observability platform. It monitors "
            "registered endpoints at customizable intervals, measures exact millisecond response latencies, "
            "categorizes error root causes, manages the complete incident lifecycle, and presents actionable "
            "intelligence through a professional SaaS dashboard.",
            body_style,
        )
    )

    # Key Objectives Box
    summary_box_data = [
        [
            Paragraph("<b>Core Objectives Achieved:</b>", body_style),
        ],
        [
            Paragraph("• <b>Real HTTP Telemetry:</b> Sends actual HTTP requests with SSL checks and follow-redirects (not mocked demo data).", bullet_style),
        ],
        [
            Paragraph("• <b>Intelligent Outage Logic:</b> Enforces consecutive failure thresholds to eliminate false alarms.", bullet_style),
        ],
        [
            Paragraph("• <b>Decoupled Architecture:</b> Independent APScheduler worker runs 24/7 separate from the interactive UI.", bullet_style),
        ],
        [
            Paragraph("• <b>Enterprise Security:</b> Built-in SSRF defense stops users from probing internal networks or cloud metadata.", bullet_style),
        ],
    ]
    t_summary = Table(summary_box_data, colWidths=[500])
    t_summary.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, 0), 1, blue),
        ])
    )
    elements.append(t_summary)
    elements.append(Spacer(1, 10))

    # ==========================================
    # Section 2: Complete Workflow in Simple Words
    # ==========================================
    elements.append(Paragraph("2. How WebPulse Works (End-to-End Workflow)", h1_style))
    elements.append(
        Paragraph(
            "The platform operates smoothly through five interconnected stages:",
            body_style,
        )
    )

    workflow_data = [
        [
            Paragraph("<b>Stage</b>", body_style),
            Paragraph("<b>Action Performed</b>", body_style),
            Paragraph("<b>Key Outcome</b>", body_style),
        ],
        [
            Paragraph("<b>1. Registration</b>", body_style),
            Paragraph("User registers target URL with custom polling interval (e.g. 60s) and timeout (e.g. 10s).", body_style),
            Paragraph("URL is checked against SSRF filters (blocking localhost & private IPs). Target enters database.", body_style),
        ],
        [
            Paragraph("<b>2. Background Polling</b>", body_style),
            Paragraph("The independent APScheduler worker queries active targets and triggers checks at their interval.", body_style),
            Paragraph("Non-blocking polling prevents overlapping checks using single-instance concurrency locks.", body_style),
        ],
        [
            Paragraph("<b>3. HTTP Verification</b>", body_style),
            Paragraph("Worker sends GET request, tracks round-trip time in ms, captures HTTP status code, and inspects SSL.", body_style),
            Paragraph("Result categorized: 200/300=UP, 4xx/5xx=DOWN, or network error (Timeout, DNS, SSL failure).", body_style),
        ],
        [
            Paragraph("<b>4. Incident Lifecycle</b>", body_style),
            Paragraph("If checks fail repeatedly (>= failure threshold), an incident opens. When operational, it auto-resolves.", body_style),
            Paragraph("Tracks start time, recovery time, exact downtime duration, and dispatches SMTP alerts.", body_style),
        ],
        [
            Paragraph("<b>5. Observability UI</b>", body_style),
            Paragraph("Streamlit dashboard displays fleet health cards, Plotly latency trends, and raw audit logs.", body_style),
            Paragraph("Stakeholders gain immediate visual clarity into uptime percentages and SLA adherence.", body_style),
        ],
    ]
    t_workflow = Table(workflow_data, colWidths=[90, 240, 170])
    t_workflow.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(t_workflow)
    elements.append(Spacer(1, 12))

    # ==========================================
    # Section 3: Technologies Used & Justifications
    # ==========================================
    elements.append(Paragraph("3. Technologies Used & Architectural Justifications", h1_style))
    elements.append(
        Paragraph(
            "Every library and tool in the stack was selected to demonstrate production-level design without unnecessary complexity:",
            body_style,
        )
    )

    tech_table_data = [
        [
            Paragraph("<b>Technology</b>", body_style),
            Paragraph("<b>Category</b>", body_style),
            Paragraph("<b>Why It Was Chosen</b>", body_style),
        ],
        [
            Paragraph("<b>Streamlit</b>", body_style),
            Paragraph("Frontend Dashboard", body_style),
            Paragraph("Enables rapid delivery of high-fidelity, reactive dashboards with native state management and custom CSS styling.", body_style),
        ],
        [
            Paragraph("<b>Python Requests</b>", body_style),
            Paragraph("HTTP Client Engine", body_style),
            Paragraph("Standard HTTP library with full support for redirect chains, TLS verification, and granular exception handling.", body_style),
        ],
        [
            Paragraph("<b>SQLAlchemy 2.0</b>", body_style),
            Paragraph("Database ORM", body_style),
            Paragraph("Modern, typed ORM with connection pooling, transaction boundaries, and cross-database portability.", body_style),
        ],
        [
            Paragraph("<b>MySQL 8.x / PyMySQL</b>", body_style),
            Paragraph("Relational Database", body_style),
            Paragraph("High-performance relational engine with foreign key constraints, composite indexes, and utf8mb4 encoding.", body_style),
        ],
        [
            Paragraph("<b>APScheduler</b>", body_style),
            Paragraph("Background Scheduling", body_style),
            Paragraph("Robust scheduling engine managing periodic cron and interval jobs independently from UI render cycles.", body_style),
        ],
        [
            Paragraph("<b>Plotly Express</b>", body_style),
            Paragraph("Data Visualization", body_style),
            Paragraph("Interactive charting for latency time series, health distribution donuts, and multi-website comparisons.", body_style),
        ],
        [
            Paragraph("<b>Pytest</b>", body_style),
            Paragraph("Testing Framework", body_style),
            Paragraph("Automated test suite with mocked network calls and isolated in-memory test databases (15/15 tests passing).", body_style),
        ],
    ]
    t_tech = Table(tech_table_data, colWidths=[100, 110, 290])
    t_tech.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(t_tech)
    elements.append(Spacer(1, 12))

    # ==========================================
    # Section 4: Deep-Dive Features & Engineering Excellence
    # ==========================================
    elements.append(Paragraph("4. Key Technical Features & Engineering Rigor", h1_style))

    elements.append(Paragraph("A. Granular Error Taxonomy", h2_style))
    elements.append(
        Paragraph(
            "Rather than treating every failure simply as 'Down', WebPulse inspects exceptions and response codes: "
            "<b>2xx/3xx</b> are operational; <b>4xx</b> are client configuration errors; <b>5xx</b> are server crashes. "
            "Network anomalies are specifically classified as <b>CONNECTION_TIMEOUT</b>, <b>READ_TIMEOUT</b>, "
            "<b>DNS_ERROR</b>, or <b>SSL_ERROR</b>, pinpointing the exact failure layer.",
            body_style,
        )
    )

    elements.append(Paragraph("B. Consecutive Failure Threshold & SLA Incident Management", h2_style))
    elements.append(
        Paragraph(
            "To prevent false incident spikes from momentary internet drops, an incident is opened only when "
            "<b>2 consecutive checks</b> fail. Once an incident is active, subsequent failed checks do not create "
            "duplicate incidents. When the site recovers, the incident automatically transitions to <b>RESOLVED</b>, "
            "computing exact downtime in seconds.",
            body_style,
        )
    )

    elements.append(Paragraph("C. SSRF (Server-Side Request Forgery) Defense", h2_style))
    elements.append(
        Paragraph(
            "Because users submit arbitrary URLs, attackers could probe the local host or internal subnets. WebPulse "
            "actively resolves domain names and blocks loopback (127.0.0.1, localhost), RFC 1918 private IPs (10.x, "
            "172.16.x, 192.168.x), and cloud metadata endpoints (169.254.169.254) prior to registration.",
            body_style,
        )
    )

    elements.append(Paragraph("D. Mathematically Accurate Uptime Formulation", h2_style))
    elements.append(
        Paragraph(
            "Uptime is computed over rolling windows (24 Hours, 7 Days, 30 Days):<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>Uptime % = (Successful Checks / Total Valid Completed Checks) &times; 100</b><br/>"
            "If no checks have been recorded yet, the platform displays <i>'No data'</i> instead of a misleading 100%.",
            body_style,
        )
    )
    elements.append(Spacer(1, 8))

    # ==========================================
    # Section 5: Database Schema
    # ==========================================
    elements.append(Paragraph("5. Relational Database Design (MySQL 8.x Schema)", h1_style))
    elements.append(
        Paragraph(
            "The platform utilizes five normalized relational tables with cascading foreign keys and composite indexes:",
            body_style,
        )
    )

    schema_data = [
        [
            Paragraph("<b>Table Name</b>", body_style),
            Paragraph("<b>Primary Key</b>", body_style),
            Paragraph("<b>Foreign Keys</b>", body_style),
            Paragraph("<b>Purpose & Stored Data</b>", body_style),
        ],
        [
            Paragraph("<code>users</code>", code_callout_style),
            Paragraph("<code>id (INT)</code>", code_callout_style),
            Paragraph("None", body_style),
            Paragraph("User accounts, credentials, and target ownership.", body_style),
        ],
        [
            Paragraph("<code>websites</code>", code_callout_style),
            Paragraph("<code>id (INT)</code>", code_callout_style),
            Paragraph("<code>user_id &rarr; users.id</code>", code_callout_style),
            Paragraph("Target URLs, names, intervals (s), timeouts (s), and active toggle.", body_style),
        ],
        [
            Paragraph("<code>monitoring_results</code>", code_callout_style),
            Paragraph("<code>id (INT)</code>", code_callout_style),
            Paragraph("<code>website_id &rarr; websites.id</code>", code_callout_style),
            Paragraph("Historical check records: checked_at, HTTP code, latency (ms), error type.", body_style),
        ],
        [
            Paragraph("<code>incidents</code>", code_callout_style),
            Paragraph("<code>id (INT)</code>", code_callout_style),
            Paragraph("<code>website_id &rarr; websites.id</code>", code_callout_style),
            Paragraph("Outage tracking: started_at, resolved_at, duration_seconds, cause.", body_style),
        ],
        [
            Paragraph("<code>alert_history</code>", code_callout_style),
            Paragraph("<code>id (INT)</code>", code_callout_style),
            Paragraph("<code>incident_id, website_id</code>", code_callout_style),
            Paragraph("Audit trail of sent, failed, or skipped email alerts.", body_style),
        ],
    ]
    t_schema = Table(schema_data, colWidths=[105, 75, 120, 200])
    t_schema.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(t_schema)
    elements.append(Spacer(1, 10))

    # ==========================================
    # Section 6: Presentation Demo Guide
    # ==========================================
    elements.append(Paragraph("6. Presentation & Demonstration Walkthrough", h1_style))
    elements.append(
        Paragraph(
            "To showcase WebPulse live during a demonstration or portfolio interview, follow this 3-step sequence:",
            body_style,
        )
    )

    demo_steps = [
        [
            Paragraph("<b>Step</b>", body_style),
            Paragraph("<b>Demonstration Action</b>", body_style),
            Paragraph("<b>Presenter Talking Points</b>", body_style),
        ],
        [
            Paragraph("<b>1. Overview Dashboard</b>", body_style),
            Paragraph("Open <code>http://localhost:8501</code>. Highlight the top 5 KPI cards, latency chart, and status donut.", body_style),
            Paragraph("<i>'Notice how WebPulse aggregates fleet-wide telemetry in real time. We can immediately see average latency and 24h uptime.'</i>", body_style),
        ],
        [
            Paragraph("<b>2. Instant Check & Registration</b>", body_style),
            Paragraph("Click <b>'⚡ Check Now'</b> on any target or add a new URL in the <b>Monitored Websites</b> tab.", body_style),
            Paragraph("<i>'The system immediately executes an HTTP check, measures round-trip time in milliseconds, and validates against SSRF vulnerabilities.'</i>", body_style),
        ],
        [
            Paragraph("<b>3. Incidents & Analytics</b>", body_style),
            Paragraph("Navigate to <b>Incidents</b> and <b>Analytics</b> pages to demonstrate root-cause logs and historical filters.", body_style),
            Paragraph("<i>'Here we see automated incident opening, root-cause categorization, and full historical audit logs for SLA tracking.'</i>", body_style),
        ],
    ]
    t_demo = Table(demo_steps, colWidths=[60, 220, 220])
    t_demo.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(t_demo)
    elements.append(Spacer(1, 14))

    # Summary Conclusion Callout
    conclusion_text = [
        [
            Paragraph(
                "<b>Conclusion & Key Takeaways:</b><br/>"
                "WebPulse demonstrates practical competencies in full-stack Python software engineering, "
                "database normalization, background worker design, network security (SSRF), telemetry data "
                "visualization, and automated software testing. It delivers a complete, production-inspired solution "
                "ready for enterprise portfolio presentations.",
                body_style,
            )
        ]
    ]
    t_conclusion = Table(conclusion_text, colWidths=[500])
    t_conclusion.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(t_conclusion)

    # Build the document using NumberedCanvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"[OK] Successfully built {output_filename}")


if __name__ == "__main__":
    build_presentation_pdf("WebPulse_Project_Presentation.pdf")
