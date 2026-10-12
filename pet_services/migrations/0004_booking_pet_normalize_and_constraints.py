from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


def normalize_existing_data(apps, schema_editor):
    Booking = apps.get_model('pet_services', 'Booking')
    Pet = apps.get_model('pet_services', 'Pet')
    WalkerRating = apps.get_model('pet_services', 'WalkerRating')

    for booking in Booking.objects.select_related('service').order_by('pk'):
        if booking.walker_id != booking.service.walker_id:
            raise RuntimeError(f'La reserva {booking.pk} y su servicio indican paseadores distintos.')
        pet = Pet.objects.filter(owner_id=booking.owner_id).order_by('pk').first()
        if pet is None:
            raise RuntimeError(f'La reserva {booking.pk} no tiene una mascota del dueño para asignar.')
        booking.pet_id = pet.pk
        booking.save(update_fields=['pet'])

    for rating in WalkerRating.objects.select_related('booking__service').order_by('pk'):
        if rating.owner_id != rating.booking.owner_id:
            raise RuntimeError(f'La calificación {rating.pk} contradice el dueño de su reserva.')
        if rating.walker_id != rating.booking.service.walker_id:
            raise RuntimeError(f'La calificación {rating.pk} contradice el paseador de su servicio.')

    Booking.objects.filter(status='accepted').update(status='confirmed')
    Booking.objects.filter(status='rejected').update(status='canceled')


def restore_old_status_values(apps, schema_editor):
    Booking = apps.get_model('pet_services', 'Booking')
    Booking.objects.filter(status='confirmed').update(status='accepted')
    Booking.objects.filter(status='canceled').update(status='rejected')


def create_overlap_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return
    schema_editor.execute('''
        CREATE TRIGGER pet_services_booking_walker_slot_insert
        BEFORE INSERT ON pet_services_booking
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM pet_services_booking AS existing
            JOIN pet_services_serviceoffer AS existing_offer ON existing_offer.id = existing.service_id
            JOIN pet_services_serviceoffer AS new_offer ON new_offer.id = NEW.service_id
            WHERE existing.date = NEW.date
              AND existing.time = NEW.time
              AND existing_offer.walker_id = new_offer.walker_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'walker already booked at this date and time');
        END;
    ''')
    schema_editor.execute('''
        CREATE TRIGGER pet_services_booking_walker_slot_update
        BEFORE UPDATE OF service_id, date, time ON pet_services_booking
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM pet_services_booking AS existing
            JOIN pet_services_serviceoffer AS existing_offer ON existing_offer.id = existing.service_id
            JOIN pet_services_serviceoffer AS new_offer ON new_offer.id = NEW.service_id
            WHERE existing.id != NEW.id
              AND existing.date = NEW.date
              AND existing.time = NEW.time
              AND existing_offer.walker_id = new_offer.walker_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'walker already booked at this date and time');
        END;
    ''')


def drop_overlap_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return
    schema_editor.execute('DROP TRIGGER IF EXISTS pet_services_booking_walker_slot_insert')
    schema_editor.execute('DROP TRIGGER IF EXISTS pet_services_booking_walker_slot_update')


class Migration(migrations.Migration):
    dependencies = [
        ('pet_services', '0003_booking_owner_confirmed_booking_walker_confirmed_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='pet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='pet_services.pet'),
        ),
        migrations.RunPython(normalize_existing_data, restore_old_status_values),
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(choices=[('pending', 'Pendiente'), ('confirmed', 'Confirmada'), ('canceled', 'Cancelada'), ('completed', 'Completado')], default='pending', max_length=20),
        ),
        migrations.RemoveField(model_name='walkerrating', name='owner'),
        migrations.RemoveField(model_name='walkerrating', name='walker'),
        migrations.RemoveField(model_name='booking', name='walker'),
        migrations.AlterField(
            model_name='booking',
            name='pet',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='pet_services.pet'),
        ),
        migrations.AlterField(
            model_name='walkerrating',
            name='score',
            field=models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
        migrations.AddConstraint(
            model_name='userprofile',
            constraint=models.CheckConstraint(condition=models.Q(('role__in', ['owner', 'walker'])), name='profile_role_valid'),
        ),
        migrations.AddConstraint(
            model_name='serviceoffer',
            constraint=models.CheckConstraint(condition=models.Q(('price__gt', 0)), name='offer_price_positive'),
        ),
        migrations.AddConstraint(
            model_name='serviceoffer',
            constraint=models.CheckConstraint(condition=models.Q(('duration_minutes__gt', 0)), name='offer_duration_positive'),
        ),
        migrations.AddConstraint(
            model_name='booking',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['pending', 'confirmed', 'canceled', 'completed'])), name='booking_status_valid'),
        ),
        migrations.AddConstraint(
            model_name='walkerrating',
            constraint=models.CheckConstraint(condition=models.Q(('score__gte', 1), ('score__lte', 5)), name='rating_score_between_1_5'),
        ),
        migrations.RunPython(create_overlap_triggers, drop_overlap_triggers),
    ]