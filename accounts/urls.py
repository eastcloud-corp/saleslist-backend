from django.urls import path
from . import views

urlpatterns = [
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('me', views.me_view, name='me'),
    path('refresh', views.refresh_view, name='token_refresh'),
    path('users/', views.users_list_view, name='users_list'),
    path('users/create/', views.create_user_view, name='create_user'),
    path('users/<int:user_id>/', views.update_user_view, name='update_user'),
]