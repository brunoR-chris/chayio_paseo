from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator


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

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(role__in=['owner', 'walker']), name='profile_role_valid'),
        ]

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

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(price__gt=0), name='offer_price_positive'),
            models.CheckConstraint(condition=Q(duration_minutes__gt=0), name='offer_duration_positive'),
        ]

    def __str__(self):
        return self.title


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('canceled', 'Cancelada'),
        ('completed', 'Completado'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings_as_owner')
    service = models.ForeignKey('ServiceOffer', on_delete=models.CASCADE, related_name='bookings')
    pet = models.ForeignKey('Pet', on_delete=models.PROTECT, related_name='bookings')
    date = models.DateField()
    time = models.TimeField()
    pickup_address = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    owner_confirmed = models.BooleanField(default=False)
    walker_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=['pending', 'confirmed', 'canceled', 'completed']),
                name='booking_status_valid',
            ),
        ]

    def clean(self):
        owner_id = getattr(self, 'owner_id', None)
        pet_id = getattr(self, 'pet_id', None)
        pet = getattr(self, 'pet', None)

        if owner_id and pet_id and pet is not None and owner_id != getattr(pet, 'owner_id', None):
            raise ValidationError({'pet': 'La mascota debe pertenecer al dueño de la reserva.'})

        service_id = getattr(self, 'service_id', None)
        service = getattr(self, 'service', None)
        if service_id and self.date and self.time and service is not None:
            conflicting_booking = Booking.objects.filter(
                service__walker_id=getattr(service, 'walker_id', None),
                date=self.date,
                time=self.time,
            ).exclude(pk=self.pk)
            if conflicting_booking.exists():
                raise ValidationError('El paseador ya tiene una reserva en esa fecha y hora.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Reserva de {self.pet} para {self.service}"


class WalkerRating(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='rating')
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=Q(score__gte=1, score__lte=5), name='rating_score_between_1_5'),
        ]

    def __str__(self):
        return f"{self.score}/5 para {self.booking.service.walker}"
