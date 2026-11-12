from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .forms import BookingForm, RegistrationForm
from .dog_breeds import MIXED_BREED
from .models import Booking, Pet, ServiceOffer, UserProfile, WalkerRating
from .templatetags.currency import currency


class CurrencyFormatTests(TestCase):
    def test_currency_uses_comma_decimals_and_dot_thousands(self):
        self.assertEqual(currency(Decimal('15.00')), '15,00')
        self.assertEqual(currency(Decimal('1234.5')), '1.234,50')


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
                'pickup_address': 'Av. Siempre Viva 123',
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
                'pickup_address': 'Av. Siempre Viva 123',
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
                'pickup_address': 'Av. Siempre Viva 123',
                'notes': '',
            },
            owner=self.owner,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_booking_form_requires_pickup_address(self):
        form = BookingForm(
            data={
                'pet': self.pet.pk,
                'date': timezone.localdate().isoformat(),
                'time': '10:00',
                'pickup_address': '',
                'notes': '',
            },
            owner=self.owner,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('pickup_address', form.errors)


class BookingPickupAddressDisplayTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='pickup-owner', password='test-password')
        self.walker = User.objects.create_user(username='pickup-walker', password='test-password')
        UserProfile.objects.create(user=self.owner, role='owner')
        UserProfile.objects.create(user=self.walker, role='walker')
        self.pet = Pet.objects.create(owner=self.owner, name='Luna', species='perro')
        self.service = ServiceOffer.objects.create(
            walker=self.walker,
            title='Paseo con dirección',
            description='Servicio de prueba',
            price=Decimal('10.00'),
            duration_minutes=30,
            city='Posadas',
        )

    def test_booking_saves_pickup_address_and_shows_it_to_walker(self):
        self.client.force_login(self.owner)
        address = 'Av. Siempre Viva 123, Posadas'

        response = self.client.post(f'/reservar/{self.service.pk}/', {
            'pet': self.pet.pk,
            'date': timezone.localdate().isoformat(),
            'time': '10:00',
            'pickup_address': address,
            'notes': '',
        })

        self.assertEqual(response.status_code, 200)
        booking = Booking.objects.get(owner=self.owner, service=self.service)
        self.assertEqual(booking.pickup_address, address)

        self.client.force_login(self.walker)
        response = self.client.get('/mis-reservas/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, address)


class PetRegistrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='pet-owner', password='test-password')
        self.client.force_login(self.user)
        self.url = '/mascota/nueva/'

    def pet_data(self, breed):
        return {
            'name': 'Luna',
            'species': 'Perro',
            'breed': breed,
            'age': '3',
            'notes': '',
            'available': 'on',
        }

    def test_registration_page_shows_dog_breeds_and_mixed_option(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Golden Retriever')
        self.assertContains(response, 'Mestizo / sin raza definida')

    def test_registration_saves_selected_breed_and_mixed_breed(self):
        for breed in ('Golden Retriever', MIXED_BREED):
            with self.subTest(breed=breed):
                response = self.client.post(self.url, self.pet_data(breed))

                self.assertEqual(response.status_code, 200)
                self.assertTrue(Pet.objects.filter(owner=self.user, breed=breed).exists())

    def test_registration_accepts_an_unlisted_breed_when_other_is_selected(self):
        data = self.pet_data('__other__')
        data['other_breed'] = 'Raza de prueba'

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Pet.objects.filter(owner=self.user, breed='Raza de prueba').exists())

    def test_registration_rejects_unlisted_breed_without_other_option(self):
        response = self.client.post(self.url, self.pet_data('Raza inventada'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selecciona una raza de la lista o elige otra raza.')
        self.assertFalse(Pet.objects.filter(owner=self.user).exists())

    def test_registration_page_explains_only_dogs_are_supported(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Por ahora solo se pueden registrar perros.')
        self.assertContains(response, 'selecciona «Otra raza»')

    def test_registration_rejects_non_dog_species(self):
        data = self.pet_data('Golden Retriever')
        data['species'] = 'Gato'

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Por ahora solo se pueden registrar perros.')
        self.assertFalse(Pet.objects.filter(owner=self.user).exists())


class ProfileUpdateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='profile-owner',
            first_name='Nombre',
            last_name='Anterior',
            email='old@example.com',
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='owner',
            phone='111222',
            address='Dirección anterior',
            bio='Información anterior',
        )
        self.client.force_login(self.user)

    def test_owner_can_update_personal_and_contact_information(self):
        response = self.client.post('/perfil/editar/', {
            'username': 'profile-owner-updated',
            'first_name': 'Nombre nuevo',
            'last_name': 'Apellido nuevo',
            'email': 'new@example.com',
            'phone': '123456789',
            'address': 'Dirección nueva',
            'bio': 'Información nueva',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'se actualizaron correctamente')
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.username, 'profile-owner-updated')
        self.assertEqual(self.user.first_name, 'Nombre nuevo')
        self.assertEqual(self.user.last_name, 'Apellido nuevo')
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertEqual(self.profile.phone, '123456789')
        self.assertEqual(self.profile.address, 'Dirección nueva')
        self.assertEqual(self.profile.bio, 'Información nueva')
        self.assertEqual(self.profile.role, 'owner')

    def test_walker_can_edit_profile_without_changing_role(self):
        self.profile.role = 'walker'
        self.profile.save(update_fields=['role'])

        response = self.client.post('/perfil/editar/', {
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'phone': '',
            'address': '',
            'bio': '',
            'role': 'owner',
        })

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.role, 'walker')

    def test_dashboard_only_shows_services_card_for_walkers(self):
        owner_response = self.client.get('/dashboard/')
        self.assertNotContains(owner_response, '>Mis servicios<')
        self.assertContains(owner_response, '>Mis mascotas<')

        self.profile.role = 'walker'
        self.profile.save(update_fields=['role'])
        walker_response = self.client.get('/dashboard/')
        self.assertContains(walker_response, '>Mis servicios<')

    def test_edit_page_requires_authentication(self):
        self.client.logout()

        response = self.client.get('/perfil/editar/')

        self.assertEqual(response.status_code, 302)


class ServiceReviewDisplayTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.walker = User.objects.create_user(
            username='review-walker',
            first_name='Paseador',
            last_name='Prueba',
        )
        self.owner = User.objects.create_user(
            username='review-owner',
            first_name='Dueño',
            last_name='Prueba',
        )
        self.pet = Pet.objects.create(owner=self.owner, name='Luna', species='Perro')
        self.description = 'Descripción completa ' + ('con muchos detalles. ' * 12)
        self.service = ServiceOffer.objects.create(
            walker=self.walker,
            title='Paseo con comentarios',
            description=self.description,
            price=Decimal('15.00'),
            duration_minutes=45,
            city='Posadas',
        )

    def create_booking(self, status, comment):
        booking = Booking.objects.create(
            owner=self.owner,
            pet=self.pet,
            service=self.service,
            date=date(2026, 12, 10 if status == 'completed' else 11),
            time=time(10, 0),
            status=status,
        )
        WalkerRating.objects.create(booking=booking, score=5, comment=comment)
        return booking

    def test_home_shows_full_service_description_and_completed_owner_comments(self):
        self.create_booking('completed', 'Comentario completo del paseo.')
        self.create_booking('pending', 'Este comentario no debe mostrarse todavía.')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.description)
        self.assertContains(response, 'Comentario completo del paseo.')
        self.assertContains(response, 'Dueño Prueba')
        self.assertNotContains(response, 'Este comentario no debe mostrarse todavía.')

    def test_home_formats_service_price_with_decimal_comma(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '$ 15,00')

    def test_booking_page_shows_full_description_and_reviews(self):
        self.create_booking('completed', 'Reseña visible en el detalle.')
        self.client.force_login(self.owner)

        response = self.client.get(f'/reservar/{self.service.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.description)
        self.assertContains(response, 'Reseña visible en el detalle.')
        self.assertContains(response, '$15,00')