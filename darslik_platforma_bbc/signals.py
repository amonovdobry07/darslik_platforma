"""
Avtomatik bildirishnomalar yaratuvchi signal'lar.
Foydalanuvchi biror amal qilganda — boshqalarga bildirishnoma yuboriladi.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment, Review, Lesson, Certificate, Notification


# ============ 1. KURSGA YOZILISH ============
@receiver(post_save, sender=Enrollment)
def notify_instructor_on_enrollment(sender, instance, created, **kwargs):
    """Talaba kursga yozilganda — instructor'ga bildirishnoma"""
    if created:
        course = instance.course
        student = instance.student
        instructor = course.instructor
        
        if instructor and instructor != student:
            Notification.objects.create(
                user=instructor,
                notification_type='enrollment',
                title=f"Yangi o'quvchi! 🎉",
                message=f"{student.username} sizning '{course.title}' kursingizga yozildi.",
                course=course,
                link=f"/dashboard/instructor/courses"
            )


# ============ 2. YANGI SHARH ============
@receiver(post_save, sender=Review)
def notify_instructor_on_review(sender, instance, created, **kwargs):
    """Yangi sharh qoldirilganda — instructor'ga bildirishnoma"""
    if created:
        course = instance.course
        student = instance.student
        instructor = course.instructor
        
        if instructor and instructor != student:
            Notification.objects.create(
                user=instructor,
                notification_type='review',
                title=f"Yangi sharh ⭐",
                message=f"{student.username} '{course.title}' kursingizga {instance.rating}/5 baho qoldirdi.",
                course=course,
                link=f"/courses/{course.id}"
            )


# ============ 3. SERTIFIKAT TAYYOR ============
@receiver(post_save, sender=Certificate)
def notify_student_on_certificate(sender, instance, created, **kwargs):
    """Sertifikat yaratilganda — talabaga bildirishnoma"""
    if created:
        Notification.objects.create(
            user=instance.student,
            notification_type='certificate',
            title=f"Sertifikatingiz tayyor! 🎓",
            message=f"Tabriklaymiz! '{instance.course.title}' kursi uchun sertifikatingiz yaratildi.",
            course=instance.course,
            link=f"/dashboard/student/certificates"
        )


# ============ 4. YANGI DARS QO'SHILDI ============
@receiver(post_save, sender=Lesson)
def notify_students_on_new_lesson(sender, instance, created, **kwargs):
    """Yangi dars qo'shilganda — yozilgan barcha talabalarga"""
    if created:
        course = instance.course
        # Yozilgan barcha talabalar
        enrollments = Enrollment.objects.filter(course=course)
        
        notifications = [
            Notification(
                user=enrollment.student,
                notification_type='new_lesson',
                title=f"Yangi dars qo'shildi 📚",
                message=f"'{course.title}' kursiga yangi dars qo'shildi: '{instance.title}'",
                course=course,
                link=f"/courses/{course.id}/lessons/{instance.id}"
            )
            for enrollment in enrollments
        ]
        
        # Bulk create — tezroq
        Notification.objects.bulk_create(notifications)