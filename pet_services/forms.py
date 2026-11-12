from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Booking, UserProfile


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label='Nombre')
    last_name = forms.CharField(max_length=150, label='Apellido')
    email = forms.EmailField(label='Correo electrónico')
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label='Quiero registrarme como')
    phone = forms.RegexField(
        regex=r'^[0-9]*$',
        max_length=20,
        label='Teléfono (opcional)',
        required=False,
        error_messages={'invalid': 'El teléfono solo puede contener números.'},
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
        }),
    )
    address = forms.CharField(max_length=255, label='Dirección (opcional)', required=False)
    bio = forms.CharField(label='Información adicional', required=False, widget=forms.Textarea(attrs={'rows': 3}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'phone',
            'address',
            'bio',
            'password1',
            'password2',
        )
        labels = {
            'username': 'Usuario',
            'password1': 'Contraseña',
            'password2': 'Confirmar contraseña',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.error_messages.update({
            'password_mismatch': 'Las contraseñas no coinciden.',
        })

        self.fields['username'].help_text = 'Solo puedes usar letras, números y @/./+/-/_.'
        self.fields['username'].error_messages.update({
            'required': 'Escribe un nombre de usuario.',
            'unique': 'Este nombre de usuario ya está en uso.',
        })

        self.fields['password1'].help_text = 'Usa al menos 8 caracteres y evita que sea muy parecida a tu información personal.'
        self.fields['password1'].error_messages.update({
            'required': 'Escribe una contraseña.',
            'password_too_short': 'La contraseña debe tener al menos 8 caracteres.',
            'password_too_common': 'La contraseña es demasiado común.',
            'password_entirely_numeric': 'La contraseña no puede contener solo números.',
        })

        self.fields['password2'].help_text = 'Ingresa la misma contraseña para confirmar.'
        self.fields['password2'].error_messages.update({
            'required': 'Confirma tu contraseña.',
        })

        self.fields['first_name'].error_messages.update({
            'required': 'Escribe tu nombre.',
        })
        self.fields['last_name'].error_messages.update({
            'required': 'Escribe tu apellido.',
        })
        self.fields['email'].error_messages.update({
            'required': 'Escribe tu correo electrónico.',
            'invalid': 'Introduce un correo electrónico válido.',
        })
        self.fields['role'].error_messages.update({
            'required': 'Selecciona el tipo de cuenta.',
        })
        self.fields['phone'].error_messages.update({
            'required': 'Escribe tu teléfono.',
        })
        self.fields['address'].error_messages.update({
            'required': 'Escribe tu dirección.',
        })

        for field_name, field in self.fields.items():
            if field_name == 'role':
                field.widget.attrs.update({'class': 'form-select'} )
            elif field_name == 'bio':
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif field_name in {'password1', 'password2'}:
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
                bio=self.cleaned_data['bio'],
            )
        return user


class ProfileUpdateForm(forms.ModelForm):
    phone = forms.RegexField(
        regex=r'^[0-9]*$',
        max_length=20,
        label='Teléfono',
        required=False,
        error_messages={'invalid': 'El teléfono solo puede contener números.'},
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
    )
    address = forms.CharField(max_length=255, label='Dirección', required=False)
    bio = forms.CharField(
        label='Información adicional',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'Usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
        }

    def __init__(self, *args, profile, **kwargs):
        self.profile = profile
        super().__init__(*args, **kwargs)
        self.fields['phone'].initial = profile.phone
        self.fields['address'].initial = profile.address
        self.fields['bio'].initial = profile.bio
        self.fields['username'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['username'].help_text = 'Solo puedes usar letras, números y @/./+/-/_.'
        self.fields['username'].error_messages.update({
            'required': 'Escribe un nombre de usuario.',
            'unique': 'Este nombre de usuario ya está en uso.',
        })

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            with transaction.atomic():
                user.save()
                self.profile.phone = self.cleaned_data['phone']
                self.profile.address = self.cleaned_data['address']
                self.profile.bio = self.cleaned_data['bio']
                self.profile.save(update_fields=['phone', 'address', 'bio'])
        return user


class BookingForm(forms.ModelForm):
    pickup_address = forms.CharField(
        max_length=255,
        label='Dirección donde buscar a la mascota',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'street-address',
            'placeholder': 'Calle, número y barrio',
        }),
    )

    class Meta:
        model = Booking
        fields = ('pet', 'date', 'time', 'pickup_address', 'notes')
        widgets = {
            'pet': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        pet_field = self.fields['pet']
        if not isinstance(pet_field, forms.ModelChoiceField):
            raise TypeError('El campo de mascota debe ser un ModelChoiceField.')
        pet_field.queryset = owner.pets.all()
        self.fields['date'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_date(self):
        booking_date = self.cleaned_data['date']
        if booking_date < timezone.localdate():
            raise forms.ValidationError('La fecha del paseo no puede ser anterior al día de hoy.')
        return booking_date
