from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label='Nombre')
    last_name = forms.CharField(max_length=150, label='Apellido')
    email = forms.EmailField(label='Correo electrónico')
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label='Quiero registrarme como')
    phone = forms.CharField(max_length=20, label='Teléfono')
    address = forms.CharField(max_length=255, label='Dirección')
    bio = forms.CharField(label='Información adicional', required=False, widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
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
