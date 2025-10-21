from django import forms
from .models import Usuario
from django.core.exceptions import ValidationError

class UsuarioRegistroForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['cedula', 'nom_usu', 'ape_usu', 'correo_ins', 'rol', 'contraseña', 'conf_contraseña']
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
                choices=[('', 'Selecciona tu rol'), ('Instructor', 'Instructor'), ('Investigador', 'Investigador')]
            ),
            'contraseña': forms.PasswordInput(attrs={
                'class': 'input', 
                'id': 'password',
                'data-toggle': 'password',
                'placeholder': 'Contraseña'
            }),
            'conf_contraseña': forms.PasswordInput(attrs={
                'class': 'input', 
                'id': 'confpassword',
                'data-toggle': 'password',
                'placeholder': 'Confirmar Contraseña'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        contraseña = cleaned_data.get('contraseña')
        confcontraseña = cleaned_data.get('conf_contraseña')
        
        if contraseña and confcontraseña and contraseña != confcontraseña:
            raise ValidationError("Las contraseñas no coinciden")
        
        return cleaned_data

    def clean_correo_ins(self):
        correo_ins = self.cleaned_data.get('correo_ins')
        if Usuario.objects.filter(correo_ins=correo_ins).exists():
            raise ValidationError("Este correo electrónico ya está registrado")
        return correo_ins

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        
        # Convertir a string para validar longitud
        cedula_str = str(cedula)
        
        if len(cedula_str) < 7:
            raise ValidationError("El número de cédula debe tener al menos 7 dígitos")
        elif len(cedula_str) > 10:
            raise ValidationError("El número de cédula no debe tener más de 10 dígitos")
        
        # Verificar unicidad de cédula
        if Usuario.objects.filter(cedula=cedula).exists():
            raise ValidationError("Esta cédula ya está registrada")

        return cedula

    def clean_contraseña(self):
        contraseña = self.cleaned_data.get('contraseña')
        if len(contraseña) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")
        return contraseña

    def save(self, commit=True):
        usuario = super().save(commit=False)
        
        if commit:
            usuario.save()
        
        return usuario