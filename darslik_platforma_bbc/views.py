from .models import LessonProgress  # yuqorida import
from .serializers import LessonProgressSerializer 

from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
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

from django.http import HttpResponse
from .models import Certificate
from .serializers import CertificateSerializer
from .certificate_generator import generate_certificate_pdf

from .models import Quiz, Question, Answer, QuizAttempt
from .serializers import (
    QuizSerializer,
    QuizStudentSerializer,
    QuizAttemptSerializer,
    QuestionSerializer,  # <-- SHU YERDA QO'SHILDI
    AnswerSerializer
)


from .models import Notification
from .serializers import NotificationSerializer
from rest_framework import status

from rest_framework.views import APIView
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta



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
    
class LessonProgressViewSet(viewsets.ModelViewSet):
    serializer_class = LessonProgressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LessonProgress.objects.filter(student=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='complete-lesson')
    def complete_lesson(self, request):
        """Darsni tugatilgan deb belgilash"""
        lesson_id = request.data.get('lesson_id')
        
        if not lesson_id:
            return Response(
                {'error': 'lesson_id majburiy'}, 
                status=400
            )
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'error': 'Dars topilmadi'}, status=404)
        
        # Foydalanuvchi shu kursga yozilganmi?
        try:
            enrollment = Enrollment.objects.get(
                student=request.user,
                course=lesson.course
            )
        except Enrollment.DoesNotExist:
            return Response(
                {'error': 'Siz bu kursga yozilmagansiz'}, 
                status=403
            )
        
        # Progress yaratish yoki yangilash
        progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson,
            defaults={'enrollment': enrollment}
        )
        
        if not progress.is_completed:
            progress.is_completed = True
            progress.enrollment = enrollment
            progress.save()
        
        # Yangi progress'ni qaytarish
        enrollment.refresh_from_db()
        
        return Response({
            'message': 'Dars muvaffaqiyatli tugatildi! 🎉',
            'progress': enrollment.progress,
            'is_course_completed': enrollment.is_completed,
            'lesson_progress': LessonProgressSerializer(progress).data
        })
    
    @action(detail=False, methods=['get'], url_path='by-course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        """Bir kurs bo'yicha barcha progress"""
        progresses = LessonProgress.objects.filter(
            student=request.user,
            lesson__course_id=course_id
        )
        serializer = self.get_serializer(progresses, many=True)
        return Response(serializer.data)
    

# ============ CERTIFICATE VIEWSET ============
class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """Sertifikatlarni boshqarish (faqat o'qish)"""
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Certificate.objects.filter(student=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='generate/(?P<course_id>[^/.]+)')
    def generate_for_course(self, request, course_id=None):
        """Sertifikat yaratish (kurs tugagandan keyin)"""
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Kurs topilmadi'}, status=404)
        
        # Yozilganmi va tugatganmi tekshirish
        try:
            enrollment = Enrollment.objects.get(
                student=request.user,
                course=course
            )
        except Enrollment.DoesNotExist:
            return Response(
                {'error': 'Siz bu kursga yozilmagansiz'},
                status=403
            )
        
        if not enrollment.is_completed:
            return Response(
                {'error': 'Avval kursni 100% tugating!'},
                status=400
            )
        
        # Mavjud sertifikatni qaytarish yoki yangi yaratish
        full_name = request.user.get_full_name() or request.user.username
        
        certificate, created = Certificate.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={
                'enrollment': enrollment,
                'student_name': full_name
            }
        )
        
        serializer = self.get_serializer(certificate)
        return Response({
            'message': 'Sertifikat tayyor! 🎓' if created else 'Sertifikat allaqachon mavjud',
            'created': created,
            'certificate': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """Sertifikat PDF'ni yuklab olish"""
        try:
            certificate = self.get_queryset().get(id=pk)
        except Certificate.DoesNotExist:
            return Response({'error': 'Sertifikat topilmadi'}, status=404)
        
        # PDF yaratish
        pdf_buffer = generate_certificate_pdf(certificate)
        
        # Faylni qaytarish
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        filename = f"certificate_{certificate.course.title}_{certificate.student.username}.pdf"
        # Filename'dan xatoli belgilarni olib tashlash
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    

class QuizViewSet(viewsets.ModelViewSet):
    """Quiz boshqaruvi"""
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Quiz.objects.all()
    
    def get_serializer_class(self):
        # Student'ga to'g'ri javob ko'rinmaydigan serializer
        if self.action == 'retrieve' or self.action == 'list':
            user = self.request.user
            if user.role == 'student':
                return QuizStudentSerializer
        return QuizSerializer
    
    @action(detail=False, methods=['get'], url_path='by-lesson/(?P<lesson_id>[^/.]+)')
    def by_lesson(self, request, lesson_id=None):
        """Dars uchun testni olish"""
        try:
            quiz = Quiz.objects.get(lesson_id=lesson_id)
        except Quiz.DoesNotExist:
            return Response({'error': 'Bu darsda test yo\'q'}, status=404)
        
        # Student'ga to'g'ri javoblar ko'rinmasin
        if request.user.role == 'student':
            serializer = QuizStudentSerializer(quiz)
        else:
            serializer = QuizSerializer(quiz)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        """Test javoblarini yuborish va baholash"""
        try:
            quiz = self.get_queryset().get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({'error': 'Test topilmadi'}, status=404)
        
        # Javoblarni olish: { "question_id": "answer_id", ... }
        answers = request.data.get('answers', {})
        
        if not answers:
            return Response({'error': 'Javoblar yuborilmagan'}, status=400)
        
        # Baholash
        questions = quiz.questions.all()
        total = questions.count()
        correct = 0
        
        for question in questions:
            user_answer_id = answers.get(str(question.id))
            if user_answer_id:
                try:
                    answer = Answer.objects.get(id=user_answer_id, question=question)
                    if answer.is_correct:
                        correct += 1
                except Answer.DoesNotExist:
                    pass
        
        score = int((correct / total) * 100) if total > 0 else 0
        is_passed = score >= quiz.pass_score
        
        # Urinishni saqlash
        attempt = QuizAttempt.objects.create(
            student=request.user,
            quiz=quiz,
            score=score,
            total_questions=total,
            correct_answers=correct,
            is_passed=is_passed
        )
        
        return Response({
            'message': 'Test yakunlandi! 🎉' if is_passed else 'Qaytadan urinib ko\'ring',
            'score': score,
            'correct_answers': correct,
            'total_questions': total,
            'is_passed': is_passed,
            'pass_score': quiz.pass_score,
            'attempt_id': attempt.id
        })


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Foydalanuvchi urinishlari"""
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(student=self.request.user)
    
# ============ QUESTION VIEWSET ============
class QuestionViewSet(viewsets.ModelViewSet):
    """Savol boshqaruvi (instructor uchun)"""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Faqat o'z kursining savollari
        if self.request.user.is_authenticated:
            return Question.objects.filter(
                quiz__lesson__course__instructor=self.request.user
            )
        return Question.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Yangi savol yaratish"""
        quiz_id = request.data.get('quiz')
        
        if not quiz_id:
            return Response(
                {'error': 'quiz maydoni majburiy'},
                status=400
            )
        
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({'error': 'Quiz topilmadi'}, status=404)
        
        # Egasini tekshirish
        if quiz.lesson.course.instructor != request.user:
            return Response(
                {'error': 'Siz bu testni boshqara olmaysiz'},
                status=403
            )
        
        # Savolni yaratish
        question = Question.objects.create(
            quiz=quiz,
            text=request.data.get('text', ''),
            order=request.data.get('order', 0)
        )
        
        serializer = self.get_serializer(question)
        return Response(serializer.data, status=201)

# ============ ANSWER VIEWSET ============
class AnswerViewSet(viewsets.ModelViewSet):
    """Javob boshqaruvi (instructor uchun)"""
    serializer_class = AnswerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Answer.objects.filter(
                question__quiz__lesson__course__instructor=self.request.user
            )
        return Answer.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Yangi javob yaratish"""
        question_id = request.data.get('question')
        
        if not question_id:
            return Response(
                {'error': 'question maydoni majburiy'},
                status=400
            )
        
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({'error': 'Savol topilmadi'}, status=404)
        
        # Egasini tekshirish
        if question.quiz.lesson.course.instructor != request.user:
            return Response(
                {'error': 'Siz bu savolni boshqara olmaysiz'},
                status=403
            )
        
        # Javobni yaratish
        answer = Answer.objects.create(
            question=question,
            text=request.data.get('text', ''),
            is_correct=request.data.get('is_correct', False),
            order=request.data.get('order', 0)
        )
        
        serializer = self.get_serializer(answer)
        return Response(serializer.data, status=201)
    
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Foydalanuvchi bildirishnomalari"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """O'qilmagan bildirishnomalar soni"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'count': count})
    
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Bitta bildirishnomani o'qilgan deb belgilash"""
        try:
            notification = self.get_queryset().get(pk=pk)
            notification.mark_as_read()
            return Response({'message': 'Belgilandi'})
        except Notification.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
    
    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Hammasini o'qilgan deb belgilash"""
        from django.utils import timezone
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({
            'message': f"{count} ta bildirishnoma belgilandi",
            'count': count
        })
    
    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        """Barcha bildirishnomalarni o'chirish"""
        count = Notification.objects.filter(user=request.user).count()
        Notification.objects.filter(user=request.user).delete()
        return Response({
            'message': f"{count} ta bildirishnoma o'chirildi"
        })
    
class InstructorStatsView(APIView):
    """Instructor uchun batafsil statistika"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Faqat instructor uchun
        if user.role != 'instructor':
            return Response(
                {'error': "Faqat o'qituvchilar uchun"},
                status=403
            )
        
        # Mening kurslarim
        my_courses = Course.objects.filter(instructor=user)
        
        # ============ ASOSIY STATISTIKA ============
        total_courses = my_courses.count()
        
        total_students = Enrollment.objects.filter(
            course__instructor=user
        ).values('student').distinct().count()
        
        total_revenue = Enrollment.objects.filter(
            course__instructor=user
        ).aggregate(
            total=Sum('course__price')
        )['total'] or 0
        
        avg_rating = Review.objects.filter(
            course__instructor=user
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        
        total_reviews = Review.objects.filter(
            course__instructor=user
        ).count()
        
        total_lessons = Lesson.objects.filter(
            course__instructor=user
        ).count()
        
        completed_courses = Enrollment.objects.filter(
            course__instructor=user,
            is_completed=True
        ).count()
        
        # ============ DAROMAD GRAFIKI (oxirgi 30 kun) ============
        revenue_data = []
        today = timezone.now().date()
        
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            day_revenue = Enrollment.objects.filter(
                course__instructor=user,
                enrolled_at__date=date
            ).aggregate(
                total=Sum('course__price')
            )['total'] or 0
            
            revenue_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'date_formatted': date.strftime('%d %b'),
                'revenue': float(day_revenue),
                'students': Enrollment.objects.filter(
                    course__instructor=user,
                    enrolled_at__date=date
                ).count()
            })
        
        # ============ ENG MASHHUR KURSLAR (TOP 5) ============
        top_courses = my_courses.annotate(
            students_count=Count('enrollments', distinct=True),
            avg_rating=Avg('reviews__rating')
        ).order_by('-students_count')[:5]
        
        top_courses_data = []
        for course in top_courses:
            top_courses_data.append({
                'id': course.id,
                'title': course.title,
                'students': course.students_count or 0,
                'rating': round(course.avg_rating or 0, 1),
                'price': float(course.price),
                'revenue': float((course.price or 0) * (course.students_count or 0))
            })
        
        # ============ KURSLAR BO'YICHA STATISTIKA ============
        courses_breakdown = []
        for course in my_courses:
            students = Enrollment.objects.filter(course=course).count()
            completed = Enrollment.objects.filter(
                course=course, is_completed=True
            ).count()
            avg = Review.objects.filter(course=course).aggregate(
                avg=Avg('rating')
            )['avg'] or 0
            
            courses_breakdown.append({
                'id': course.id,
                'title': course.title,
                'students': students,
                'completed': completed,
                'completion_rate': int((completed / students * 100)) if students > 0 else 0,
                'rating': round(avg, 1),
                'reviews': Review.objects.filter(course=course).count(),
                'revenue': float(course.price * students)
            })
        
        # ============ QUIZ STATISTIKA ============
        quiz_stats = {
            'total_attempts': QuizAttempt.objects.filter(
                quiz__lesson__course__instructor=user
            ).count(),
            'passed': QuizAttempt.objects.filter(
                quiz__lesson__course__instructor=user,
                is_passed=True
            ).count(),
            'failed': QuizAttempt.objects.filter(
                quiz__lesson__course__instructor=user,
                is_passed=False
            ).count(),
        }
        
        # ============ OXIRGI YOZILISHLAR ============
        recent_enrollments = Enrollment.objects.filter(
            course__instructor=user
        ).select_related('student', 'course').order_by('-enrolled_at')[:10]
        
        recent_enrollments_data = [
            {
                'student_name': e.student.username,
                'course_title': e.course.title,
                'enrolled_at': e.enrolled_at.isoformat(),
                'progress': e.progress
            }
            for e in recent_enrollments
        ]
        
        return Response({
            # Asosiy raqamlar
            'overview': {
                'total_courses': total_courses,
                'total_students': total_students,
                'total_revenue': float(total_revenue),
                'avg_rating': round(avg_rating, 1),
                'total_reviews': total_reviews,
                'total_lessons': total_lessons,
                'completed_courses': completed_courses,
                'completion_rate': int(
                    (completed_courses / total_students * 100)
                ) if total_students > 0 else 0
            },
            
            # Grafik ma'lumotlari
            'revenue_chart': revenue_data,
            'top_courses': top_courses_data,
            'courses_breakdown': courses_breakdown,
            'quiz_stats': quiz_stats,
            'recent_enrollments': recent_enrollments_data
        })