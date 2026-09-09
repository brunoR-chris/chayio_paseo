from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Dueño'),
        ('walker', 'Paseador'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    avatar = models.FileField(upload_to='avatars/', blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class Pet(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50)
    breed = models.CharField(max_length=100, blank=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class ServiceOffer(models.Model):
    walker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_offers')
    title = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=60)
    city = models.CharField(max_length=100)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
        ('completed', 'Completado'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings_as_owner')
    walker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings_as_walker')
    service = models.ForeignKey('ServiceOffer', on_delete=models.CASCADE, related_name='bookings')
    date = models.DateField()
    time = models.TimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    owner_confirmed = models.BooleanField(default=False)
    walker_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Reserva de {self.owner} para {self.service}"


class WalkerRating(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='rating')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='walker_ratings')
    walker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_ratings')
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.score}/5 para {self.walker}"
