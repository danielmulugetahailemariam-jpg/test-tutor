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
    referral_code: str = "",
    is_renewal: bool = False,
) -> io.BytesIO:
    buf = io.BytesIO()
    width, height = landscape(A5)
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setTitle(f"Qelal Tutoring Pass - {name}")

    c.setStrokeColor(colors.HexColor("#1B365D"))
    c.setLineWidth(2)
    c.roundRect(14, 14, width - 28, height - 28, 10, stroke=1, fill=0)

    c.setFillColor(colors.HexColor("#1B365D"))
    c.roundRect(14, height - 86, width - 28, 72, 10, stroke=0, fill=1)
    c.rect(14, height - 86, width - 28, 20, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(30, height - 46, "QELAL / BISHOFTU TUTORING HUB")
    c.setFont("Helvetica", 10)
    subtitle = "MONTHLY PAYMENT RECEIPT & STUDY PASS" if is_renewal else "OFFICIAL WELCOME PASS & STUDY RECEIPT"
    c.drawString(30, height - 66, subtitle)

    c.setFillColor(colors.HexColor("#16A34A"))
    c.roundRect(width - 135, height - 68, 105, 24, 6, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width - 82.5, height - 60, "STATUS: APPROVED")

    pass_no = f"QELAL-{str(student_id).zfill(4)}-M{months_paid}"
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, height - 108, f"PASS / RECEIPT NO: {pass_no}")
    c.drawRightString(width - 30, height - 108, f"BILLING CYCLE: MONTH #{months_paid}")

    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.line(30, height - 116, width - 30, height - 116)

    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.roundRect(28, 86, width - 56, 184, 8, stroke=1, fill=1)

    rows = [
        ("Student Name:", name),
        ("Grade / Stream:", grade),
        ("Phone Number:", phone),
        ("Referral / Squad Code:", referral_code or f"TG-{tg_id}"),
        ("Payment / Issue Date:", approved_at),
        ("Valid Until (30 Days):", expires_on),
    ]

    y = height - 142
    for label, val in rows:
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(44, y, label)

        c.setFillColor(colors.HexColor("#0F172A") if "Valid Until" not in label else colors.HexColor("#15803D"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(200, y, str(val)[:42])
        y -= 26

    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 8.5)
    c.drawString(30, 58, "• Unlocks full Study Library, Verified Answer Keys, Study Plans & Interactive Quizzes.")
    c.drawString(30, 44, "• Invite friends with your Referral Code for Study Squad seating & tuition perks!")
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, 24, "Qelal Learning • Bishoftu, Ethiopia")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
