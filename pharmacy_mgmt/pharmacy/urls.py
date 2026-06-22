from django.urls import path
from . import views

app_name = "pharmacy"

urlpatterns = [
    # Auth URLs
    path('',views.login_view,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('logout/',views.logout_view,name='logout'),
    path('add-medicine/',views.add_medicine,name='add_medicine')
]