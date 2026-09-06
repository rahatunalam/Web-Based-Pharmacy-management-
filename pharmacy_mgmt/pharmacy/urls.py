from django.urls import path
from . import views

app_name = "pharmacy"

urlpatterns = [
    # Auth URLs
    path('',views.login_view,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('logout/',views.logout_view,name='logout'),
    path('add-medicine/',views.add_medicine,name='add_medicine'),
    path('s-add-medicine/',views.s_add_medicine,name='s_add_medicine'),
    path('add-salesman/', views.add_salesman, name='add_salesman'),
    path('edit-medicine/',views.edit_medicine,name='edit_medicine'),
    path('edit-medicine/<int:pk>/', views.edit_medicine_save, name='edit_medicine_save'),
    path('edit-medicine/delete/<int:pk>/', views.delete_med, name='delete_med'),
    path('delete-salesman/<int:pk>/', views.delete_salesman, name='delete_salesman'),
    path('sale-medicines/', views.sale_medicines, name='sale_medicines'),
    path('get-medicine-price/', views.get_medicine_price, name='get_medicine_price'),
    path('wholesale/',views.wholesale,name='wholesale'),
    path('get-wholesale-price/',views.get_wholesale_price,name='get_wholesale_price'),
    path('update-medicine/',views.update_medicine,name='update_medicine'),
    path('medicine-list/',views.medicine_list,name='medicine_list'),
    path('medicine-suggestion/',views.medicine_suggestions,name='medicine_suggestion'),
    path('sales-report/',views.sales_report,name='sales_report'),
    path('pro-customer/', views.pro_customer, name='pro_customer'),
    path('pro-customer/delete/<int:pk>/',views.delete_pro_customer,name='delete_pro_customer'),
    path('pro-customer-sale/', views.pro_customer_sale, name='pro_customer_sale'),
    path('get-pro-customer-price/', views.get_pro_customer_price, name='get_pro_customer_price'),
    path('get-pro-customers/', views.get_pro_customers, name='get_pro_customers'),
    path('pro-customer-report/', views.pro_customer_report, name='pro_customer_report'),
    path('medicine-search/',views.medicine_search,name='medicine_search'),
    path('receipt/',views.receipt,name='receipt'),
]
