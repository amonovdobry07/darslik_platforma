from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .models import Lesson
from .models import Enrollment
from .models import Review
from .models import LessonProgress
from .models import Certificate

from .models import Category, Course

from .models import Quiz, Question, Answer, QuizAttempt

from .models import Notification

from .models import Payment

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['username', 'email']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'avatar', 'bio')}),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'category', 'price', 'level']
    list_filter = ['level', 'category']
    search_fields = ['title']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_free', 'duration_minutes']
    list_filter = ['is_free', 'course']
    search_fields = ['title']
    ordering = ['course', 'order']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrolled_at', 'progress', 'is_completed']
    list_filter = ['is_completed', 'enrolled_at']
    search_fields = ['student__username', 'course__title']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['student__username', 'course__title', 'comment']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'is_completed', 'completed_at']
    list_filter = ['is_completed', 'completed_at']
    search_fields = ['student__username', 'lesson__title']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'student_name', 'issued_at']
    list_filter = ['issued_at', 'course']
    search_fields = ['student__username', 'course__title', 'student_name']
    readonly_fields = ['certificate_id', 'issued_at']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'pass_score']
    inlines = [QuestionInline]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'quiz', 'order']
    inlines = [AnswerInline]

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'is_passed', 'completed_at']
    list_filter = ['is_passed', 'completed_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['student__username', 'course__title', 'transaction_id']
    readonly_fields = ['transaction_id', 'created_at', 'completed_at']