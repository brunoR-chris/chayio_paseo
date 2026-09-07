from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('registro/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reservar/<int:offer_id>/', views.book_service, name='book_service'),
    path('mascota/nueva/', views.create_pet, name='create_pet'),
    path('paseo/nuevo/', views.create_offer, name='create_offer'),
    path('mis-reservas/', views.bookings_for_walker, name='walker_bookings'),
]
