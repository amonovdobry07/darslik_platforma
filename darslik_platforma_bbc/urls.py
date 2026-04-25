from django.urls import path, include
from rest_framework_nested import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView,
    MeView,
    CategoryViewSet,
    CourseViewSet,
    LessonViewSet,
    EnrollmentViewSet,
    ReviewViewSet,
    UpdateProfileView,
    ChangePasswordView,
)

router = routers.DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('courses', CourseViewSet, basename='course')
router.register('enrollments', EnrollmentViewSet, basename='enrollment')

courses_router = routers.NestedDefaultRouter(router, 'courses', lookup='course')
courses_router.register('lessons', LessonViewSet, basename='course-lessons')
courses_router.register('reviews', ReviewViewSet, basename='course-reviews')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/update/', UpdateProfileView.as_view(), name='update-profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('', include(router.urls)),
    path('', include(courses_router.urls)),
]