from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegistrationForm
from .models import Booking, Pet, ServiceOffer, UserProfile, WalkerRating


def home(request):
    offers = ServiceOffer.objects.filter(available=True).select_related('walker').annotate(
        walker_rating=Avg('walker__received_ratings__score'),
    )[:12]
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
    offer = ServiceOffer.objects.select_related('walker').get(id=offer_id)

    if request.method == 'POST':
        date = request.POST.get('date', '').strip()
        time = request.POST.get('time', '').strip()
        notes = request.POST.get('notes', '').strip()

        if date and time:
            Booking.objects.create(
                owner=request.user,
                walker=offer.walker,
                service=offer,
                date=date,
                time=time,
                notes=notes,
            )
            return render(request, 'pet_services/booking_created.html', {'offer': offer})

    return render(request, 'pet_services/book_service.html', {'offer': offer})


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
    bookings = Booking.objects.filter(owner=request.user) | Booking.objects.filter(walker=request.user)
    bookings = bookings.distinct().order_by('-created_at')

    history_base = Booking.objects.filter(owner=request.user).select_related('service', 'walker').order_by('-date', '-time')
    if selected_status != 'all':
        history_base = history_base.filter(status=selected_status)
    if selected_period != 'all':
        history_base = history_base.filter(date__year=selected_period[:4], date__month=selected_period[5:7])

    owner_history = history_base

    walker_history = Booking.objects.filter(walker=request.user).select_related('service', 'owner').order_by('-date', '-time')
    if selected_status != 'all':
        walker_history = walker_history.filter(status=selected_status)
    if selected_period != 'all':
        walker_history = walker_history.filter(date__year=selected_period[:4], date__month=selected_period[5:7])

    total_earnings = walker_history.filter(status='completed').aggregate(total=Sum('service__price'))['total'] or 0

    all_periods = sorted({
        booking.date.strftime('%Y-%m') for booking in Booking.objects.filter(owner=request.user) | Booking.objects.filter(walker=request.user)
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
                ('accepted', 'Aceptado'),
                ('rejected', 'Rechazado'),
                ('completed', 'Completado'),
            ],
        },
    )


@login_required
def create_pet(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        species = request.POST.get('species', '').strip()
        breed = request.POST.get('breed', '').strip()
        age = request.POST.get('age', '').strip()
        notes = request.POST.get('notes', '').strip()
        available = request.POST.get('available') == 'on'

        if name and species:
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

    return render(request, 'pet_services/create_pet.html')


@login_required
def create_offer(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        duration = request.POST.get('duration_minutes', '60').strip()
        city = request.POST.get('city', '').strip()

        if title and description and price and city:
            ServiceOffer.objects.create(
                walker=request.user,
                title=title,
                description=description,
                price=price,
                duration_minutes=int(duration) if duration else 60,
                city=city,
            )
            return render(request, 'pet_services/offer_created.html')

    return render(request, 'pet_services/create_offer.html')


@login_required
def bookings_for_walker(request):
    offers = ServiceOffer.objects.filter(walker=request.user)
    bookings = Booking.objects.filter(walker=request.user).select_related('owner', 'service').order_by('-created_at')
    return render(request, 'pet_services/walker_bookings.html', {'bookings': bookings, 'offers': offers})


@login_required
def confirm_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, owner=request.user)
    if request.method == 'POST' and booking.status == 'accepted':
        booking.owner_confirmed = True
        booking.save(update_fields=['owner_confirmed'])
    return redirect('dashboard')


@login_required
def respond_booking(request, booking_id, response):
    booking = get_object_or_404(Booking, id=booking_id, walker=request.user)
    if request.method == 'POST' and booking.status == 'pending':
        if response == 'accept':
            booking.status = 'accepted'
            booking.walker_confirmed = True
        elif response == 'reject':
            booking.status = 'rejected'
        booking.save(update_fields=['status', 'walker_confirmed'])
    return redirect('walker_bookings')


@login_required
def complete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, walker=request.user)
    if request.method == 'POST' and booking.status == 'accepted' and booking.owner_confirmed and booking.walker_confirmed:
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
                owner=request.user,
                walker=booking.walker,
                score=int(score),
                comment=request.POST.get('comment', '').strip(),
            )
    return redirect('dashboard')
