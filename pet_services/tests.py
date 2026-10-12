from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Booking, Pet, ServiceOffer, UserProfile, WalkerRating


class BookingAndDataConstraintTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='owner-test')
        self.walker = User.objects.create_user(username='walker-test')
        UserProfile.objects.create(user=self.owner, role='owner')
        UserProfile.objects.create(user=self.walker, role='walker')
        self.pet = Pet.objects.create(owner=self.owner, name='Luna', species='perro')
        self.service = ServiceOffer.objects.create(
            walker=self.walker,
            title='Paseo principal',
            description='Servicio de prueba',
            price=Decimal('10.00'),
            duration_minutes=30,
            city='Posadas',
        )
        self.other_service = ServiceOffer.objects.create(
            walker=self.walker,
            title='Paseo alternativo',
            description='Otro servicio del mismo paseador',
            price=Decimal('12.00'),
            duration_minutes=45,
            city='Posadas',
        )

    def make_booking(self, service=None, status='pending'):
        return Booking.objects.create(
            owner=self.owner,
            pet=self.pet,
            service=service or self.service,
            date=date(2026, 12, 1),
            time=time(10, 0),
            status=status,
        )

    def assert_database_rejects(self, operation):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                operation()

    def test_walker_cannot_be_booked_twice_across_services(self):
        self.make_booking()

        with self.assertRaises(ValidationError):
            self.make_booking(service=self.other_service)

        self.assert_database_rejects(lambda: Booking.objects.bulk_create([
            Booking(
                owner=self.owner,
                pet=self.pet,
                service=self.other_service,
                date=date(2026, 12, 1),
                time=time(10, 0),
                status='pending',
            ),
        ]))

    def test_database_rejects_invalid_domain_values(self):
        self.assert_database_rejects(lambda: UserProfile.objects.filter(user=self.owner).update(role='admin'))
        self.assert_database_rejects(lambda: ServiceOffer.objects.filter(pk=self.service.pk).update(price=0))
        self.assert_database_rejects(lambda: ServiceOffer.objects.filter(pk=self.service.pk).update(duration_minutes=0))
        self.assert_database_rejects(lambda: Booking.objects.bulk_create([
            Booking(
                owner=self.owner,
                pet=self.pet,
                service=self.service,
                date=date(2026, 12, 2),
                time=time(10, 0),
                status='unknown',
            ),
        ]))

        booking = self.make_booking(status='completed')
        self.assert_database_rejects(lambda: WalkerRating.objects.bulk_create([
            WalkerRating(booking=booking, score=0),
        ]))