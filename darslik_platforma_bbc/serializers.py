from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, Course, Lesson
from .models import Enrollment
from .models import Review

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