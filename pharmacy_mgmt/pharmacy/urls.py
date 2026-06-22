from django.urls import path
from . import views

urlpatterns = [
    # Auth URLs
    path('',views.login_view,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('logout/',views.logout_view,name='logout'),
]