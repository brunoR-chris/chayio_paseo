from django.contrib import admin

from .models import Booking, Pet, ServiceOffer, UserProfile, WalkerRating


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'address', 'avatar')
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
    list_display = ('owner', 'walker_name', 'pet', 'service', 'date', 'status', 'owner_confirmed', 'walker_confirmed')
    list_filter = ('status', 'date')
    search_fields = ('owner__username', 'service__walker__username', 'service__title', 'pet__name')

    @admin.display(ordering='service__walker__username', description='Paseador')
    def walker_name(self, booking):
        return booking.service.walker


@admin.register(WalkerRating)
class WalkerRatingAdmin(admin.ModelAdmin):
    list_display = ('walker_name', 'owner_name', 'score', 'booking', 'created_at')
    list_filter = ('score',)

    @admin.display(ordering='booking__service__walker__username', description='Paseador')
    def walker_name(self, rating):
        return rating.booking.service.walker

    @admin.display(ordering='booking__owner__username', description='Dueño')
    def owner_name(self, rating):
        return rating.booking.owner
