from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Usuario


class UsuarioRegistroForm(forms.ModelForm):
    contraseña = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'id': 'password',
            'placeholder': 'Contraseña'
        })
    )

    conf_contraseña = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'id': 'confpassword',
            'placeholder': 'Confirmar Contraseña'
        })
    )

    class Meta:
        model = Usuario
        fields = [
            'cedula',
            'nom_usu',
            'ape_usu',
            'correo_ins',
            'rol',
            'contraseña',
            'conf_contraseña'
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={
                'class': 'input',
                'id': 'cedula',
                'placeholder': 'Cédula'
            }),
            'nom_usu': forms.TextInput(attrs={
                'class': 'input',
                'id': 'nombre',
                'placeholder': 'Nombre'
            }),
            'ape_usu': forms.TextInput(attrs={
                'class': 'input',
                'id': 'apellido',
                'placeholder': 'Apellido'
            }),
            'correo_ins': forms.EmailInput(attrs={
                'class': 'input',
                'id': 'email',
                'placeholder': 'Correo Institucional'
            }),
            'rol': forms.Select(
                attrs={'class': 'select', 'id': 'rol'},
                choices=[
                    ('', 'Selecciona tu rol'),
                    ('Instructor', 'Instructor'),
                    ('Investigador', 'Investigador')
                ]
            ),
        }

    # ------------------- VALIDACIONES -------------------

    def clean(self):
        cleaned_data = super().clean()
        contraseña = cleaned_data.get('contraseña')
        conf_contraseña = cleaned_data.get('conf_contraseña')

        # Validar coincidencia
        if contraseña and conf_contraseña and contraseña != conf_contraseña:
            self.add_error('conf_contraseña', "Las contraseñas no coinciden.")
        else:
            # Validar fortaleza con los validadores de Django
            try:
                validate_password(contraseña)
            except ValidationError as e:
                self.add_error('contraseña', e)

        return cleaned_data

    def clean_correo_ins(self):
        correo_ins = self.cleaned_data.get('correo_ins')
        if Usuario.objects.filter(correo_ins=correo_ins).exists():
            raise ValidationError("Este correo ya está registrado.")
        return correo_ins

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')

        if Usuario.objects.filter(cedula=cedula).exists():
            raise ValidationError("Esta cédula ya está registrada.")

        if len(str(cedula)) < 7 or len(str(cedula)) > 10:
            raise ValidationError("La cédula debe tener entre 7 y 10 dígitos.")

        return cedula

    # ------------------- GUARDADO -------------------

    def save(self, commit=True):
        usuario = super().save(commit=False)
        # Guardar la contraseña cifrada correctamente
        usuario.set_password(self.cleaned_data['contraseña'])
        if commit:
            usuario.save()
        return usuario