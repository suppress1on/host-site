from django.urls import path
from . import views

app_name = 'main_app'

urlpatterns = [
    # Корневой URL должен вести на index_view, который сам решает, куда перенаправить
    path('', views.index_view, name='index'),
    # Дашборд должен иметь свой собственный уникальный URL, на который перенаправляет index_view
    path('dashboard/', views.dashboard_view, name='home'),
]