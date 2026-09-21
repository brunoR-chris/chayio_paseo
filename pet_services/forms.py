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
