from django.urls import path
from . import views

app_name = "pharmacy"

urlpatterns = [
    # Auth URLs
    path('',views.login_view,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('logout/',views.logout_view,name='logout'),
    path('add-medicine/',views.add_medicine,name='add_medicine'),
    path('add-salesman/', views.add_salesman, name='add_salesman'),
    path('delete-medicine/',views.delete_medicine,name='delete_medicine'),
    path('delete-medicine/<int:pk>/', views.delete_med, name='delete_med'),
    path('delete-salesman/<int:pk>/', views.delete_salesman, name='delete_salesman'),
    path('sale-medicines/', views.sale_medicines, name='sale_medicines'),
]
