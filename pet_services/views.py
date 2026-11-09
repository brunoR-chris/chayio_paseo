from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect, render
from decimal import Decimal, InvalidOperation

from .forms import BookingForm, ProfileUpdateForm, RegistrationForm
from .dog_breeds import DOG_BREEDS, MIXED_BREED, OTHER_BREED_VALUE
from .models import Booking, Pet, ServiceOffer, UserProfile, WalkerRating


def home(request):
    completed_bookings = Booking.objects.filter(
        status='completed',
        rating__isnull=False,
    ).select_related('owner').prefetch_related('rating')
    offers = ServiceOffer.objects.filter(available=True).select_related('walker').annotate(
        walker_rating=Avg('bookings__rating__score'),
    ).prefetch_related(Prefetch(
        'bookings',
        queryset=completed_bookings,
        to_attr='completed_bookings',
    ))[:12]
    return render(request, 'pet_services/home.html', {'offers': offers})


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def book_service(request, offer_id):
    completed_bookings = Booking.objects.filter(
        status='completed',
        rating__isnull=False,
    ).select_related('owner').prefetch_related('rating')
    offer = ServiceOffer.objects.select_related('walker').prefetch_related(Prefetch(
        'bookings',
        queryset=completed_bookings,
        to_attr='completed_bookings',
    )).get(id=offer_id)
    form = BookingForm(request.POST or None, owner=request.user)

    if request.method == 'POST' and form.is_valid():
        booking = form.save(commit=False)
        booking.owner = request.user
        booking.service = offer
        try:
            with transaction.atomic():
                booking.save()
            return render(request, 'pet_services/booking_created.html', {'offer': offer, 'booking': booking})
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, 'El paseador ya tiene una reserva en esa fecha y hora.')

    return render(request, 'pet_services/book_service.html', {'offer': offer, 'form': form})


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        avatar = request.FILES.get('avatar')
        if avatar:
            profile.avatar = avatar
            profile.save(update_fields=['avatar'])
        return redirect('dashboard')

    selected_status = request.GET.get('status', 'all')
    selected_period = request.GET.get('period', 'all')

    pets = Pet.objects.filter(owner=request.user)
    available_pets = Pet.objects.filter(available=True).select_related('owner') if profile.role == 'walker' else []
    my_offers = ServiceOffer.objects.filter(walker=request.user) if profile.role == 'walker' else []
    bookings = Booking.objects.filter(owner=request.user) | Booking.objects.filter(service__walker=request.user)
    bookings = bookings.distinct().order_by('-created_at')

    history_base = Booking.objects.filter(owner=request.user).select_related('service__walker', 'pet').order_by('-date', '-time')
    if selected_status != 'all':
        history_base = history_base.filter(status=selected_status)
    if selected_period != 'all':
        history_base = history_base.filter(date__year=selected_period[:4], date__month=selected_period[5:7])

    owner_history = history_base

    walker_history = Booking.objects.filter(service__walker=request.user).select_related('service', 'owner', 'pet').order_by('-date', '-time')
    if selected_status != 'all':
        walker_history = walker_history.filter(status=selected_status)
    if selected_period != 'all':
        walker_history = walker_history.filter(date__year=selected_period[:4], date__month=selected_period[5:7])

    total_earnings = walker_history.filter(status='completed').aggregate(total=Sum('service__price'))['total'] or 0

    all_periods = sorted({
        booking.date.strftime('%Y-%m') for booking in Booking.objects.filter(owner=request.user) | Booking.objects.filter(service__walker=request.user)
    }, reverse=True)

    return render(
        request,
        'pet_services/dashboard.html',
        {
            'profile': profile,
            'pets': pets,
            'available_pets': available_pets,
            'my_offers': my_offers,
            'bookings': bookings,
            'owner_history': owner_history,
            'walker_history': walker_history,
            'total_earnings': total_earnings,
            'selected_status': selected_status,
            'selected_period': selected_period,
            'history_periods': all_periods,
            'status_choices': [
                ('all', 'Todos'),
                ('pending', 'Pendiente'),
                ('confirmed', 'Confirmada'),
                ('canceled', 'Cancelada'),
                ('completed', 'Completado'),
            ],
        },
    )


@login_required
def edit_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileUpdateForm(
        request.POST or None,
        instance=request.user,
        profile=profile,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return render(request, 'pet_services/edit_profile.html', {
            'form': form,
            'saved': True,
        })

    return render(request, 'pet_services/edit_profile.html', {'form': form})


@login_required
def create_pet(request):
    breed_value = ''
    other_breed_value = ''
    form_error = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        species = request.POST.get('species', '').strip()
        breed_value = request.POST.get('breed', '').strip()
        other_breed_value = request.POST.get('other_breed', '').strip()
        if breed_value == OTHER_BREED_VALUE:
            breed = other_breed_value
            if not breed:
                form_error = 'Escribe el nombre de la raza.'
            elif len(breed) > 100:
                form_error = 'La raza no puede superar los 100 caracteres.'
        elif breed_value == MIXED_BREED or breed_value == '':
            breed = breed_value
        elif breed_value in DOG_BREEDS:
            breed = breed_value
        else:
            breed = ''
            form_error = 'Selecciona una raza de la lista o elige otra raza.'

        age = request.POST.get('age', '').strip()
        notes = request.POST.get('notes', '').strip()
        available = request.POST.get('available') == 'on'

        if name and species and not form_error:
            Pet.objects.create(
                owner=request.user,
                name=name,
                species=species,
                breed=breed,
                age=int(age) if age else None,
                notes=notes,
                available=available,
            )
            return render(request, 'pet_services/pet_created.html')

    return render(request, 'pet_services/create_pet.html', {
        'dog_breeds': DOG_BREEDS,
        'mixed_breed': MIXED_BREED,
        'other_breed_value': OTHER_BREED_VALUE,
        'breed_value': breed_value,
        'other_breed': other_breed_value,
        'form_error': form_error,
    })


@login_required
def create_offer(request):
    error = None
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        duration = request.POST.get('duration_minutes', '60').strip()
        city = request.POST.get('city', '').strip()

        try:
            price_value = Decimal(price)
            duration_value = int(duration) if duration else 60
            if not price_value.is_finite() or price_value <= 0 or duration_value <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            error = 'El precio y la duración deben ser mayores que cero.'
        else:
            if title and description and city:
                offer = ServiceOffer(
                    walker=request.user,
                    title=title,
                    description=description,
                    price=price_value,
                    duration_minutes=duration_value,
                    city=city,
                )
                try:
                    offer.full_clean()
                except ValidationError as validation_error:
                    error = 'Revisa el precio y la duración del servicio.'
                else:
                    offer.save()
                    return render(request, 'pet_services/offer_created.html')

    return render(request, 'pet_services/create_offer.html', {'error': error})


@login_required
def bookings_for_walker(request):
    offers = ServiceOffer.objects.filter(walker=request.user)
    bookings = Booking.objects.filter(service__walker=request.user).select_related('owner', 'service', 'pet').order_by('-created_at')
    return render(request, 'pet_services/walker_bookings.html', {'bookings': bookings, 'offers': offers})


@login_required
def confirm_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, owner=request.user)
    if request.method == 'POST' and booking.status == 'confirmed':
        booking.owner_confirmed = True
        booking.save(update_fields=['owner_confirmed'])
    return redirect('dashboard')


@login_required
def respond_booking(request, booking_id, response):
    booking = get_object_or_404(Booking, id=booking_id, service__walker=request.user)
    if request.method == 'POST' and booking.status == 'pending':
        if response == 'accept':
            booking.status = 'confirmed'
            booking.walker_confirmed = True
        elif response == 'reject':
            booking.status = 'canceled'
        booking.save(update_fields=['status', 'walker_confirmed'])
    return redirect('walker_bookings')


@login_required
def complete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, service__walker=request.user)
    if request.method == 'POST' and booking.status == 'confirmed' and booking.owner_confirmed and booking.walker_confirmed:
        booking.status = 'completed'
        booking.save(update_fields=['status'])
    return redirect('walker_bookings')


@login_required
def rate_walker(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, owner=request.user, status='completed')
    if request.method == 'POST' and not hasattr(booking, 'rating'):
        score = request.POST.get('score', '')
        if score in {'1', '2', '3', '4', '5'}:
            WalkerRating.objects.create(
                booking=booking,
                score=int(score),
                comment=request.POST.get('comment', '').strip(),
            )
    return redirect('dashboard')
