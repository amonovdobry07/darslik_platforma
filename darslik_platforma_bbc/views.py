from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Course
from .serializers import CategorySerializer, CourseSerializer
from .permissions import IsInstructorOrReadOnly

from .models import Lesson
from .serializers import LessonSerializer

from rest_framework.exceptions import ValidationError
from .models import Enrollment
from .serializers import EnrollmentSerializer

from .models import Review
from .serializers import ReviewSerializer

from .serializers import UserUpdateSerializer, ChangePasswordSerializer



User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsInstructorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'level']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = [IsInstructorOrReadOnly]

    def get_queryset(self):
        return Lesson.objects.filter(course_id=self.kwargs['course_pk'])

    def perform_create(self, serializer):
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        if course.instructor != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Siz faqat o'z kursingizga dars qo'sha olasiz!")
        serializer.save(course=course)


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']  # PUT/PATCH kerak emas

    def get_queryset(self):
        # Foydalanuvchi faqat o'zining enrollmentlarini ko'radi
        return Enrollment.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        course = serializer.validated_data['course']

        # Instructor o'z kursiga yozila olmaydi
        if course.instructor == self.request.user:
            raise ValidationError("Siz o'z kursingizga yozila olmaysiz!")

        # Allaqachon yozilganligini tekshirish
        if Enrollment.objects.filter(student=self.request.user, course=course).exists():
            raise ValidationError("Siz bu kursga allaqachon yozilgansiz!")

        serializer.save(student=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Review.objects.filter(course_id=self.kwargs['course_pk'])

    def perform_create(self, serializer):
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        user = self.request.user

        # Faqat kursga yozilgan studentlar review qoldira oladi
        if not Enrollment.objects.filter(student=user, course=course).exists():
            raise ValidationError("Siz bu kursga yozilmagansiz, review qoldira olmaysiz!")

        # Bitta student 1 marta review qoldirishi mumkin
        if Review.objects.filter(student=user, course=course).exists():
            raise ValidationError("Siz bu kursga allaqachon review qoldirgansiz!")

        serializer.save(student=user, course=course)

    def perform_update(self, serializer):
        # Faqat o'z reviewini tahrirlashi mumkin
        if serializer.instance.student != self.request.user:
            raise ValidationError("Siz faqat o'z reviewingizni tahrirlay olasiz!")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.student != self.request.user:
            raise ValidationError("Siz faqat o'z reviewingizni o'chira olasiz!")
        instance.delete()

class UpdateProfileView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": "Eski parol noto'g'ri!"},
                status=400
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"detail": "Parol muvaffaqiyatli o'zgartirildi!"})