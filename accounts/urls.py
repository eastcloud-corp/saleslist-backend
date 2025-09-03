from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('login', views.login_view, name='login_no_slash'),
    path('logout/', views.logout_view, name='logout'),
    path('logout', views.logout_view, name='logout_no_slash'),
    path('me/', views.me_view, name='me'),
    path('me', views.me_view, name='me_no_slash'),
    path('refresh/', views.refresh_view, name='token_refresh'),
    path('refresh', views.refresh_view, name='token_refresh_no_slash'),
    path('users/', views.users_list_view, name='users_list'),
    path('users/create/', views.create_user_view, name='create_user'),
    path('users/<int:user_id>/', views.update_user_view, name='update_user'),
]