from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/login/', views.login_api, name='login'),
    path('api/kits/slots/', views.get_slots_api, name='get_slots'),
    path('api/bookings/', views.create_booking_api, name='create_booking'),
    path('api/bookings/mine/', views.my_bookings_api, name='my_bookings'),
    path('api/admin/bookings/', views.admin_bookings_api, name='admin_bookings'),
    path('api/admin/bookings/<str:id>/approve/', views.admin_approve_api, name='admin_approve'),
    path('api/admin/bookings/<str:id>/reject/', views.admin_reject_api, name='admin_reject'),
    path('api/admin/bookings/<str:id>/handover/', views.admin_handover_api, name='admin_handover'),
    path('api/admin/bookings/<str:id>/receive/', views.admin_receive_api, name='admin_receive'),
    path('api/admin/kits/<str:id>/condition/', views.admin_condition_api, name='admin_condition'),
]
