"""Progress computation & certificate issuance (master prompt §8, §5).

Level progress is COMPUTED here, never stored.
"""
import io
import uuid

from django.db.models import Sum

from apps.content.models import Lesson, Level

from .models import Certificate, Progress


def compute_level_progress(user, level: Level) -> dict:
    """Aggregate a user's progress across all lessons in a level."""
    lesson_ids = list(
        Lesson.objects.filter(unit__level=level).values_list("id", flat=True)
    )
    total = len(lesson_ids)

    qs = Progress.objects.filter(user=user, lesson_id__in=lesson_ids)
    completed = qs.filter(status=Progress.Status.COMPLETED).count()
    agg = qs.aggregate(points=Sum("score"), time=Sum("time_spent"))
    percent = round((completed / total) * 100) if total else 0

    return {
        "level_id": str(level.id),
        "level_code": level.code,
        "level_name": level.name,
        "total_lessons": total,
        "completed_lessons": completed,
        "percent": percent,
        "points": agg["points"] or 0,
        "time_spent": agg["time"] or 0,
        "is_completed": total > 0 and completed == total,
    }


def overview(user) -> list:
    return [
        compute_level_progress(user, level)
        for level in Level.objects.all().order_by("order")
    ]


def maybe_issue_certificate(user, level: Level):
    """Issue a certificate when every lesson in the level is completed."""
    stats = compute_level_progress(user, level)
    if not stats["is_completed"]:
        return None
    certificate, _ = Certificate.objects.get_or_create(
        user=user,
        level=level,
        defaults={"certificate_number": _generate_number(level)},
    )
    return certificate


def _generate_number(level: Level) -> str:
    return f"CERT-{level.code}-{uuid.uuid4().hex[:8].upper()}"


def generate_certificate_pdf(certificate: Certificate) -> bytes:
    """Render a simple certificate PDF with reportlab."""
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    width, height = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

    pdf.setFont("Helvetica-Bold", 32)
    pdf.drawCentredString(width / 2, height - 4 * cm, "Certificate of Completion")

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width / 2, height - 6 * cm, "This certifies that")

    pdf.setFont("Helvetica-Bold", 24)
    name = certificate.user.full_name or certificate.user.email
    pdf.drawCentredString(width / 2, height - 7.5 * cm, name)

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(
        width / 2, height - 9 * cm,
        f"has successfully completed level {certificate.level.name}",
    )

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        width / 2, 3 * cm,
        f"Certificate No: {certificate.certificate_number}",
    )
    pdf.drawCentredString(
        width / 2, 2.3 * cm,
        f"Issued: {certificate.issued_at:%Y-%m-%d}",
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
