from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Booking, Pet, ServiceOffer, UserProfile


def home(request):
    offers = ServiceOffer.objects.filter(available=True).select_related('walker')[:12]
    return render(request, 'pet_services/home.html', {'offers': offers})


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
            return redirect('dashboard')

    return render(request, 'pet_services/book_service.html', {'offer': offer})


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    pets = Pet.objects.filter(owner=request.user)
    my_offers = ServiceOffer.objects.filter(walker=request.user) if profile.role == 'walker' else []
    bookings = Booking.objects.filter(owner=request.user) | Booking.objects.filter(walker=request.user)
    bookings = bookings.distinct().order_by('-created_at')
    return render(
        request,
        'pet_services/dashboard.html',
        {
            'profile': profile,
            'pets': pets,
            'my_offers': my_offers,
            'bookings': bookings,
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

        if name and species:
            Pet.objects.create(
                owner=request.user,
                name=name,
                species=species,
                breed=breed,
                age=int(age) if age else None,
                notes=notes,
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
