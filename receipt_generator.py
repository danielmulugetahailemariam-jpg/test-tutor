import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5, landscape
from reportlab.pdfgen import canvas


def generate_membership_pdf(
    student_id: str,
    name: str,
    grade: str,
    phone: str,
    tg_id: str,
    months_paid: int,
    approved_at: str,
    expires_on: str,
    is_renewal: bool = False,
) -> io.BytesIO:
    buf = io.BytesIO()
    width, height = landscape(A5)
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setTitle(f"Bishoftu Tutoring Hub Pass - {name}")

    # Outer border
    c.setStrokeColor(colors.HexColor("#1B365D"))
    c.setLineWidth(2)
    c.roundRect(14, 14, width - 28, height - 28, 10, stroke=1, fill=0)

    # Top Navy Banner
    c.setFillColor(colors.HexColor("#1B365D"))
    c.roundRect(14, height - 86, width - 28, 72, 10, stroke=0, fill=1)
    c.rect(14, height - 86, width - 28, 20, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, height - 46, "BISHOFTU TUTORING HUB")
    c.setFont("Helvetica", 10)
    subtitle = "MONTHLY PAYMENT RECEIPT & STUDY PASS" if is_renewal else "OFFICIAL WELCOME PASS & STUDY RECEIPT"
    c.drawString(30, height - 66, subtitle)

    # Active Badge on Top Right
    c.setFillColor(colors.HexColor("#16A34A"))
    c.roundRect(width - 135, height - 68, 105, 24, 6, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width - 82.5, height - 60, "STATUS: APPROVED")

    # Receipt ID & Cycle
    pass_no = f"BTH-{str(student_id).zfill(4)}-M{months_paid}"
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, height - 108, f"PASS / RECEIPT NO: {pass_no}")
    c.drawRightString(width - 30, height - 108, f"BILLING CYCLE: MONTH #{months_paid}")

    # Divider
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.line(30, height - 116, width - 30, height - 116)

    # Student Details Box
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.roundRect(28, 92, width - 56, 178, 8, stroke=1, fill=1)

    rows = [
        ("Student Name:", name),
        ("Grade Level:", grade),
        ("Phone Number:", phone),
        ("Telegram ID:", str(tg_id)),
        ("Payment / Issue Date:", approved_at),
        ("Valid Until (30 Days):", expires_on),
    ]

    y = height - 144
    for label, val in rows:
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(44, y, label)

        c.setFillColor(colors.HexColor("#0F172A") if "Valid Until" not in label else colors.HexColor("#15803D"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(195, y, str(val)[:42])
        y -= 27

    # Footer Notes
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 8.5)
    c.drawString(30, 62, "• Grants full access to the Telegram Study Library, Verified Answer Keys & Bubble-Sheet Mock Exams.")
    c.drawString(30, 48, "• Monthly renewal reminder starts on Day 23. A 7-day grace window applies after Day 30.")
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, 26, "Bishoftu Tutoring Hub • Automated Student Registration & Library System")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
