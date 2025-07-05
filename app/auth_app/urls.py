from django.urls import path
from . import views

app_name = 'auth' 

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    # path('two-fa-verification/', views.two_fa_verification_view, name='two_fa_verification'),
    path('two-fa-verification/<int:user_id>/', views.two_fa_verification_view, name='two_fa_verification_with_id'),
]