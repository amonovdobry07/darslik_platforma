from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        INSTRUCTOR = 'instructor', 'Instructor'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT
    
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail = models.ImageField(upload_to='courses/', null=True, blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='courses',
        limit_choices_to={'role': 'instructor'}
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Matn yoki tushuntirish")
    video_url = models.URLField(blank=True, null=True, help_text="YouTube yoki Vimeo link")
    order = models.PositiveIntegerField(default=0, help_text="Darslar tartibi")
    is_free = models.BooleanField(default=False, help_text="Bepul preview uchun")
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Dars davomiyligi (minut)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    

class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'student'}
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.PositiveIntegerField(default=0, help_text="0-100%")

    class Meta:
        unique_together = ['student', 'course']  # Bitta kursga 2 marta yozila olmaydi
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.username} → {self.course.title}"
    def update_progress(self):
        """Progress'ni avtomatik hisoblash"""
        total_lessons = self.course.lessons.count()
        if total_lessons == 0:
            self.progress = 0
            self.save()
            return
        
        completed_lessons = LessonProgress.objects.filter(
            student=self.student,
            lesson__course=self.course,
            is_completed=True
        ).count()
        
        # Foiz hisoblash
        new_progress = int((completed_lessons / total_lessons) * 100)
        self.progress = new_progress
        
        # Agar 100% bo'lsa — kurs tugadi
        if new_progress >= 100 and not self.is_completed:
            from django.utils import timezone
            self.is_completed = True
            self.completed_at = timezone.now()
        
        self.save()
    
    def get_completed_lessons_count(self):
        """Tugatilgan darslar soni"""
        return LessonProgress.objects.filter(
            student=self.student,
            lesson__course=self.course,
            is_completed=True
        ).count()
    
    def get_total_lessons_count(self):
        """Jami darslar soni"""
        return self.course.lessons.count()
    
class Review(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text="1 dan 5 gacha baho"
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'course']  # Bitta kursga 1 ta review
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} → {self.course.title} ({self.rating}⭐)"
    

# ============ YANGI MODEL — LessonProgress ============
class LessonProgress(models.Model):
    """Talabaning har bir dars bo'yicha taraqqiyoti"""
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='lesson_progresses'
    )
    lesson = models.ForeignKey(
        Lesson, 
        on_delete=models.CASCADE,
        related_name='student_progresses'
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='lesson_progresses',
        null=True,
        blank=True
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    watch_time_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'lesson']
        ordering = ['-updated_at']
        verbose_name = "Dars taraqqiyoti"
        verbose_name_plural = "Dars taraqqiyotlari"

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title}"

    def save(self, *args, **kwargs):
        # Agar tugatilgan deb belgilangan bo'lsa va vaqti yo'q bo'lsa
        if self.is_completed and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
        
        # Enrollment'dagi progress'ni yangilash
        if self.enrollment:
            self.enrollment.update_progress()


class Certificate(models.Model):
    """Talabaga beriladigan sertifikat"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='certificate',
        null=True,
        blank=True
    )
    
    # Unique sertifikat ID (qog'ozda ko'rinadi)
    certificate_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    
    # Talabaning ismi (sertifikatda ko'rinadi)
    student_name = models.CharField(max_length=200)
    
    # Sana
    issued_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-issued_at']
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title}"
    
    def get_verification_url(self):
        """Sertifikatni tekshirish URL"""
        return f"/certificates/verify/{self.certificate_id}/"
    

# ============ QUIZ MODELS ============

class Quiz(models.Model):
    """Dars uchun test"""
    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name='quiz'
    )
    title = models.CharField(max_length=200, default="Dars testi")
    description = models.TextField(blank=True)
    pass_score = models.IntegerField(
        default=70,
        help_text="O'tish uchun minimal foiz (0-100)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
    
    def __str__(self):
        return f"{self.lesson.title} - Test"


class Question(models.Model):
    """Test savoli"""
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    text = models.TextField()
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
    
    def __str__(self):
        return f"{self.quiz.lesson.title} - Savol {self.order}"


class Answer(models.Model):
    """Savol uchun javob varianti"""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"
    
    def __str__(self):
        return f"{self.text[:50]}"


class QuizAttempt(models.Model):
    """Talabaning test urinishi"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    score = models.IntegerField(default=0, help_text="To'g'ri javoblar foizi")
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    is_passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-completed_at']
        verbose_name = "Test urinishi"
        verbose_name_plural = "Test urinishlari"
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.lesson.title} ({self.score}%)"
    

class Notification(models.Model):
    """Foydalanuvchi bildirishnomalari"""
    
    NOTIFICATION_TYPES = [
        ('enrollment', 'Yangi yozilish'),
        ('review', 'Yangi sharh'),
        ('certificate', 'Sertifikat tayyor'),
        ('new_lesson', 'Yangi dars'),
        ('new_course', 'Yangi kurs'),
        ('quiz_passed', 'Test muvaffaqiyatli'),
        ('quiz_failed', 'Test muvaffaqiyatsiz'),
        ('course_completed', 'Kurs tugatildi'),
        ('system', 'Tizim xabari'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Foydalanuvchi"
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='system',
        verbose_name="Tur"
    )
    
    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar")
    
    # Qaysi obyektga tegishli (ixtiyoriy)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Bildirishnoma havolasi (bossa qaerga olib boradi)
    link = models.CharField(max_length=500, blank=True, default='')
    
    # O'qilganmi
    is_read = models.BooleanField(default=False, verbose_name="O'qilgan")
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Bildirishnomani o'qilgan deb belgilash"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class Payment(models.Model):
    """To'lov tranzaksiyalari"""
    
    PAYMENT_METHODS = [
        ('click', 'Click'),
        ('payme', 'Payme'),
        ('card', 'Plastik karta'),
        ('demo', 'Demo (test)'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Kutilmoqda'),
        ('processing', 'Jarayonda'),
        ('completed', 'Muvaffaqiyatli'),
        ('failed', 'Muvaffaqiyatsiz'),
        ('refunded', 'Qaytarildi'),
    ]
    
    # Unique transaction ID
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    # Foydalanuvchi va kurs
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Talaba"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Kurs"
    )
    
    # Pul ma'lumotlari
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Summa"
    )
    
    # To'lov turi va holati
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='demo',
        verbose_name="To'lov usuli"
    )
    
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending',
        verbose_name="Holati"
    )
    
    # Click/Payme provider'idan keladigan ma'lumotlar (kelajakda)
    provider_transaction_id = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name="Provider ID"
    )
    provider_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Provider javobi"
    )
    
    # Vaqt belgilari
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Qo'shimcha ma'lumot
    notes = models.TextField(blank=True, default='')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.amount} so'm)"
    
    def mark_as_completed(self):
        """To'lovni muvaffaqiyatli deb belgilash"""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Avtomatik enrollment yaratish
        Enrollment.objects.get_or_create(
            student=self.student,
            course=self.course
        )