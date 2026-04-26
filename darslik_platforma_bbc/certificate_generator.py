"""
Sertifikat PDF yaratuvchi
"""
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from datetime import datetime


def generate_certificate_pdf(certificate):
    """
    Sertifikat uchun chiroyli PDF yaratadi
    
    Args:
        certificate: Certificate model instance
    
    Returns:
        BytesIO: PDF fayli
    """
    buffer = BytesIO()
    
    # Landscape A4 (gorizontal)
    page_width, page_height = landscape(A4)
    
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    
    # ============ FON RANG ============
    # Asosiy fon
    c.setFillColorRGB(0.039, 0.039, 0.039)  # #0a0a0a
    c.rect(0, 0, page_width, page_height, fill=True, stroke=False)
    
    # ============ DEKORATIV CHIZIQLAR ============
    # Yuqori va pastki to'q yashil chiziq
    c.setStrokeColorRGB(0.063, 0.725, 0.506)  # #10b981 (emerald)
    c.setLineWidth(3)
    
    # Yuqori chiziq
    c.line(2*cm, page_height - 1.5*cm, page_width - 2*cm, page_height - 1.5*cm)
    # Pastki chiziq
    c.line(2*cm, 1.5*cm, page_width - 2*cm, 1.5*cm)
    
    # Burchaklar (zayrkachalar)
    corner_size = 1*cm
    
    # Yuqori chap
    c.line(2*cm, page_height - 1.5*cm, 2*cm, page_height - 1.5*cm - corner_size)
    c.line(2*cm, page_height - 1.5*cm, 2*cm + corner_size, page_height - 1.5*cm)
    
    # Yuqori o'ng
    c.line(page_width - 2*cm, page_height - 1.5*cm, page_width - 2*cm, page_height - 1.5*cm - corner_size)
    c.line(page_width - 2*cm, page_height - 1.5*cm, page_width - 2*cm - corner_size, page_height - 1.5*cm)
    
    # Pastki chap
    c.line(2*cm, 1.5*cm, 2*cm, 1.5*cm + corner_size)
    c.line(2*cm, 1.5*cm, 2*cm + corner_size, 1.5*cm)
    
    # Pastki o'ng
    c.line(page_width - 2*cm, 1.5*cm, page_width - 2*cm, 1.5*cm + corner_size)
    c.line(page_width - 2*cm, 1.5*cm, page_width - 2*cm - corner_size, 1.5*cm)
    
    # ============ SARLAVHA ============
    # "DARSLIK PLATFORMA"
    c.setFillColorRGB(0.518, 0.800, 0.086)  # #84cc16 (lime)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2, page_height - 2.5*cm, "DARSLIK PLATFORMA")
    
    # Liniya ostida
    c.setStrokeColorRGB(0.518, 0.800, 0.086)
    c.setLineWidth(1)
    line_y = page_height - 2.8*cm
    c.line(page_width/2 - 4*cm, line_y, page_width/2 + 4*cm, line_y)
    
    # ============ "SERTIFIKAT" KATTA YOZUV ============
    c.setFillColorRGB(0.063, 0.725, 0.506)  # emerald
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(page_width / 2, page_height - 4.5*cm, "SERTIFIKAT")
    
    # Sub-title
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.setFont("Helvetica", 12)
    c.drawCentredString(page_width / 2, page_height - 5.2*cm, "Muvaffaqiyatli yakunlash haqida")
    
    # ============ "Berildi" ============
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(page_width / 2, page_height - 6.5*cm, "Ushbu sertifikat")
    
    # ============ TALABA ISMI ============
    c.setFillColorRGB(1, 1, 1)  # oq
    c.setFont("Helvetica-Bold", 32)
    student_name = certificate.student_name.upper()
    c.drawCentredString(page_width / 2, page_height - 8*cm, student_name)
    
    # Ism ostida chiziq
    c.setStrokeColorRGB(0.063, 0.725, 0.506)
    c.setLineWidth(2)
    name_width = len(student_name) * 0.5 * cm
    c.line(
        page_width/2 - max(name_width, 6*cm),
        page_height - 8.3*cm,
        page_width/2 + max(name_width, 6*cm),
        page_height - 8.3*cm
    )
    
    # ============ KURS NOMI MATNI ============
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(
        page_width / 2,
        page_height - 9.3*cm,
        "quyidagi kursni muvaffaqiyatli yakunlaganligi uchun beriladi:"
    )
    
    # ============ KURS NOMI ============
    c.setFillColorRGB(0.518, 0.800, 0.086)  # lime
    c.setFont("Helvetica-Bold", 22)
    course_title = f'"{certificate.course.title}"'
    c.drawCentredString(page_width / 2, page_height - 10.5*cm, course_title)
    
    # ============ PASTKI MA'LUMOTLAR ============
    
    # SANA (chap)
    sana_x = 5*cm
    bottom_y = 3.5*cm
    
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 10)
    c.drawString(sana_x, bottom_y + 0.5*cm, "BERILGAN SANA")
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    date_str = certificate.issued_at.strftime("%d.%m.%Y")
    c.drawString(sana_x, bottom_y - 0.2*cm, date_str)
    
    # SERTIFIKAT ID (o'rtada)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 10)
    c.drawCentredString(page_width / 2, bottom_y + 0.5*cm, "SERTIFIKAT ID")
    
    c.setFillColorRGB(0.518, 0.800, 0.086)
    c.setFont("Courier-Bold", 11)
    cert_id_short = str(certificate.certificate_id).upper()[:13] + "..."
    c.drawCentredString(page_width / 2, bottom_y - 0.2*cm, cert_id_short)
    
    # O'QITUVCHI (o'ng)
    instructor_x = page_width - 5*cm
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 10)
    c.drawRightString(instructor_x, bottom_y + 0.5*cm, "O'QITUVCHI")
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    instructor_name = certificate.course.instructor.username if certificate.course.instructor else "Darslik Platforma"
    c.drawRightString(instructor_x, bottom_y - 0.2*cm, instructor_name)
    
    # ============ ENG PASTKI MATN ============
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        page_width / 2,
        2.2*cm,
        f"Sertifikatning haqiqiyligini tekshirish uchun ID dan foydalaning"
    )
    
    # PDF ni saqlash
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer