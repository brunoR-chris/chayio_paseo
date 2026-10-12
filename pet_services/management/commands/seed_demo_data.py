import os
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from pet_services.models import Booking, Pet, ServiceOffer, UserProfile, WalkerRating


class Command(BaseCommand):
    help = 'Crea cuentas y registros demo de forma idempotente.'

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get('CHAYIO_DEMO_PASSWORD')
        if not password:
            raise CommandError('Define CHAYIO_DEMO_PASSWORD para crear las cuentas demo.')

        User = get_user_model()
        accounts = {
            'bruno': ('Bruno', 'Administrador', 'owner', '0000000001', 'Dirección de prueba'),
            'ana_duena': ('Ana', 'Gómez', 'owner', '0000000002', 'Calle Demo 12'),
            'lucia_duena': ('Lucía', 'Pérez', 'owner', '0000000003', 'Calle Demo 24'),
            'mateo_dueno': ('Mateo', 'Díaz', 'owner', '0000000004', 'Calle Demo 36'),
            'ezequiel': ('Ezequiel', 'Alarcón', 'walker', '3764998811', 'Las petunias'),
            'sofia_paseadora': ('Sofía', 'López', 'walker', '0000000005', 'Calle Demo 48'),
            'tomas_paseador': ('Tomás', 'Ruiz', 'walker', '0000000006', 'Calle Demo 60'),
        }

        users = {}
        for username, (first_name, last_name, role, phone, address) in accounts.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f'{username}@example.test',
                    'password': make_password(password),
                },
            )
            if username == 'bruno':
                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=['first_name', 'last_name'])

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': role,
                    'phone': phone,
                    'bio': 'Perfil de prueba para Chayio.',
                    'address': address,
                },
            )
            users[username] = user

        pets = {}
        pet_specs = [
            ('ana_duena', 'Luna', 'mestiza'),
            ('ana_duena', 'Milo', 'beagle'),
            ('lucia_duena', 'Nube', 'caniche'),
            ('mateo_dueno', 'Rocky', 'labrador'),
        ]
        for owner_name, pet_name, breed in pet_specs:
            pet, _ = Pet.objects.get_or_create(
                owner=users[owner_name],
                name=pet_name,
                defaults={'species': 'perro', 'breed': breed},
            )
            pets[pet_name] = pet

        offers = {}
        offer_specs = [
            ('ezequiel', 'Paseos urbanos con Ezequiel', '6500.00', '60', 'Posadas'),
            ('sofia_paseadora', 'Paseos tranquilos con Sofía', '7200.00', '45', 'Posadas'),
            ('tomas_paseador', 'Paseos activos con Tomás', '8000.00', '60', 'Garupá'),
        ]
        for walker_name, title, price, duration, city in offer_specs:
            offer, _ = ServiceOffer.objects.get_or_create(
                walker=users[walker_name],
                title=title,
                defaults={
                    'description': 'Servicio de prueba para recorridos seguros.',
                    'price': price,
                    'duration_minutes': int(duration),
                    'city': city,
                },
            )
            offers[walker_name] = offer

        start_date = timezone.localdate() + timedelta(days=30)
        booking_specs = [
            ('ana_duena', 'Luna', 'ezequiel', 1, time(9, 0), 'pending', None),
            ('lucia_duena', 'Nube', 'sofia_paseadora', 2, time(10, 0), 'confirmed', None),
            ('mateo_dueno', 'Rocky', 'tomas_paseador', 3, time(11, 0), 'canceled', None),
            ('ana_duena', 'Milo', 'sofia_paseadora', 4, time(12, 0), 'completed', 5),
            ('lucia_duena', 'Nube', 'tomas_paseador', 5, time(13, 0), 'completed', 4),
        ]
        for owner_name, pet_name, walker_name, day_offset, booking_time, status, score in booking_specs:
            marker = f'Datos demo: {owner_name}, {pet_name}, {walker_name}, {day_offset}'
            booking, _ = Booking.objects.get_or_create(
                owner=users[owner_name],
                service=offers[walker_name],
                notes=marker,
                defaults={
                    'pet': pets[pet_name],
                    'date': start_date + timedelta(days=day_offset),
                    'time': booking_time,
                    'status': status,
                    'owner_confirmed': status in {'confirmed', 'completed'},
                    'walker_confirmed': status in {'confirmed', 'completed'},
                },
            )
            if score is not None:
                WalkerRating.objects.get_or_create(
                    booking=booking,
                    defaults={'score': score, 'comment': 'Calificación de prueba.'},
                )

        self.stdout.write(self.style.SUCCESS(
            f'Datos demo listos: {User.objects.count()} usuarios, {Pet.objects.count()} mascotas, '
            f'{ServiceOffer.objects.count()} servicios, {Booking.objects.count()} reservas y '
            f'{WalkerRating.objects.count()} calificaciones.'
        ))