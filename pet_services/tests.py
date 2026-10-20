from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .forms import BookingForm, RegistrationForm
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


class RegistrationAndBookingFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='form-owner')
        self.pet = Pet.objects.create(owner=self.owner, name='Luna', species='perro')

    def test_registration_phone_accepts_only_numeric_characters(self):
        phone_field = RegistrationForm.base_fields['phone']

        self.assertEqual(phone_field.clean('0123456789'), '0123456789')
        self.assertEqual(phone_field.clean(''), '')
        with self.assertRaises(ValidationError):
            phone_field.clean('123abc')

    def test_booking_form_accepts_future_dates_and_sets_date_picker_minimum(self):
        today = timezone.localdate()
        form = BookingForm(
            data={
                'pet': self.pet.pk,
                'date': (today + timedelta(days=1)).isoformat(),
                'time': '10:00',
                'notes': '',
            },
            owner=self.owner,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.fields['date'].widget.attrs['min'], today.isoformat())

    def test_booking_form_accepts_today(self):
        form = BookingForm(
            data={
                'pet': self.pet.pk,
                'date': timezone.localdate().isoformat(),
                'time': '10:00',
                'notes': '',
            },
            owner=self.owner,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_booking_form_rejects_past_dates(self):
        form = BookingForm(
            data={
                'pet': self.pet.pk,
                'date': (timezone.localdate() - timedelta(days=1)).isoformat(),
                'time': '10:00',
                'notes': '',
            },
            owner=self.owner,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)