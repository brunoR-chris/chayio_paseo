from django.contrib import admin

from .models import Booking, Pet, ServiceOffer, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'address')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'species', 'breed')
    search_fields = ('name', 'owner__username', 'species')


@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'walker', 'price', 'city', 'available')
    list_filter = ('available', 'city')
    search_fields = ('title', 'walker__username', 'city')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('owner', 'walker', 'service', 'date', 'status')
    list_filter = ('status', 'date')
    search_fields = ('owner__username', 'walker__username', 'service__title')
