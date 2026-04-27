from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, Course, Lesson
from .models import Enrollment
from .models import Review
from .models import LessonProgress 
from .models import Certificate
from .models import Quiz, Question, Answer, QuizAttempt
from .models import Notification
from .models import Payment

User = get_user_model()


# ============ AUTH ============
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'role', 'bio']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Parollar mos kelmadi!")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'avatar', 'bio']


# ============ CATEGORY ============
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


# ============ LESSON (Course'dan oldin bo'lishi kerak!) ============
class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'title', 'content',
            'video_url', 'order', 'is_free',
            'duration_minutes', 'created_at'
        ]
        read_only_fields = ['created_at']


class LessonListSerializer(serializers.ModelSerializer):
    """Kurs ichida darslar ro'yxati uchun qisqartirilgan versiya"""
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'order', 'is_free', 'duration_minutes']


# ============ COURSE ============
class CourseSerializer(serializers.ModelSerializer):
    instructor = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    lessons = LessonListSerializer(many=True, read_only=True)
    lessons_count = serializers.IntegerField(source='lessons.count', read_only=True)
    average_rating = serializers.SerializerMethodField()  # ← YANGI
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)  # ← YANGI
    students_count = serializers.IntegerField(source='enrollments.count', read_only=True)  # ← YANGI

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price',
            'thumbnail', 'level', 'instructor',
            'category', 'category_id', 'created_at',
            'lessons', 'lessons_count',
            'average_rating', 'reviews_count', 'students_count'  # ← YANGI
        ]
        read_only_fields = ['instructor', 'created_at']

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            'id', 'course', 'course_id', 'enrolled_at',
            'is_completed', 'progress'
        ]
        read_only_fields = ['enrolled_at', 'is_completed', 'progress']

class ReviewSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'student', 'course', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['student', 'course', 'created_at', 'updated_at']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'bio', 'avatar']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Yangi parollar mos kelmadi!"})
        return attrs
    
class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    course_id = serializers.IntegerField(source='lesson.course.id', read_only=True)
    
    class Meta:
        model = LessonProgress
        fields = [
            'id', 
            'lesson', 
            'lesson_title',
            'course_id',
            'is_completed', 
            'completed_at', 
            'watch_time_seconds',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['student', 'completed_at']


class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    instructor_name = serializers.CharField(source='course.instructor.username', read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id',
            'certificate_id',
            'student_name',
            'course',
            'course_title',
            'course_thumbnail',
            'instructor_name',
            'issued_at'
        ]
        read_only_fields = ['certificate_id', 'student_name', 'issued_at']

class AnswerSerializer(serializers.ModelSerializer):
    """Instructor uchun — to'g'ri javob ham ko'rinadi"""
    class Meta:
        model = Answer
        fields = ['id', 'question', 'text', 'is_correct', 'order']


class AnswerStudentSerializer(serializers.ModelSerializer):
    """Talabaga ko'rinadigan — to'g'ri javob ko'rinmaydi"""
    class Meta:
        model = Answer
        fields = ['id', 'text', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'quiz', 'text', 'order', 'answers']


class QuestionStudentSerializer(serializers.ModelSerializer):
    """Talabaga — to'g'ri javoblarsiz"""
    answers = AnswerStudentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'answers']


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'id', 
            'lesson', 
            'title', 
            'description', 
            'pass_score',
            'questions',
            'questions_count'
        ]
    
    def get_questions_count(self, obj):
        return obj.questions.count()


class QuizStudentSerializer(serializers.ModelSerializer):
    """Talabaga — to'g'ri javoblarsiz"""
    questions = QuestionStudentSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'id',
            'lesson',
            'title',
            'description',
            'pass_score',
            'questions',
            'questions_count'
        ]
    
    def get_questions_count(self, obj):
        return obj.questions.count()


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    lesson_title = serializers.CharField(source='quiz.lesson.title', read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = [
            'id',
            'quiz',
            'quiz_title',
            'lesson_title',
            'score',
            'total_questions',
            'correct_answers',
            'is_passed',
            'completed_at'
        ]
        read_only_fields = ['student', 'completed_at']


class NotificationSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'course',
            'course_title',
            'course_thumbnail',
            'link',
            'is_read',
            'created_at',
            'read_at'
        ]
        read_only_fields = ['user', 'created_at', 'read_at']


class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_id',
            'student',
            'student_name',
            'course',
            'course_title',
            'course_thumbnail',
            'amount',
            'payment_method',
            'status',
            'provider_transaction_id',
            'created_at',
            'completed_at',
            'notes'
        ]
        read_only_fields = [
            'student',
            'transaction_id',
            'created_at',
            'completed_at',
            'provider_transaction_id'
        ]