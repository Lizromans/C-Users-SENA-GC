from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Usuario, Aprendiz
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


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

def cifrar(dato):
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key)).encrypt(str(dato).encode()).decode()

from django import forms
from django.core.exceptions import ValidationError
from .models import Aprendiz
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
import base64
import hashlib

def cifrar(dato):
    if not dato:
        return dato
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key)).encrypt(str(dato).encode()).decode()

class AprendizForm(forms.ModelForm):
    TIPO_DOC_CHOICES = [
        ('', 'Seleccione tipo de documento'), 
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('CE', 'Cédula de Extranjería'),
        ('PEP', 'Permiso Especial de Permanencia'),
    ]
    
    MEDIO_BANCARIO_CHOICES = [
        ('', 'Seleccione entidad bancaria'), 
        ('Bre-B', 'Bre-B'), 
        ('Bancolombia', 'Bancolombia'),
        ('Davivienda', 'Davivienda'),
        ('Banco de Bogotá', 'Banco de Bogotá'),
        ('BBVA', 'BBVA'),
        ('Nequi', 'Nequi'),
        ('Daviplata', 'Daviplata'),
    ]
    
    MODALIDAD_CHOICES = [
        ('', 'Seleccione modalidad'),  
        ('Presencial', 'Presencial'),
        ('Virtual', 'Virtual'),
        ('A Distancia', 'A Distancia'),
    ]
    
    tipo_doc = forms.ChoiceField(
        label='Tipo de Documento',
        choices=TIPO_DOC_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    medio_bancario = forms.ChoiceField(
        label='Entidad Bancaria',
        choices=MEDIO_BANCARIO_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    modalidad = forms.ChoiceField(
        label='Modalidad de Estudio',
        choices=MODALIDAD_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    acepta_tratamiento_datos = forms.BooleanField(
        required=True,
        label='',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={
            'required': 'Debe aceptar el tratamiento de datos personales para continuar.'
        }
    )
    
    class Meta:
        model = Aprendiz
        exclude = ['proyectos', 'estado_apre', 'id_sem', 'fecha_registro', 'fecha_aceptacion_datos']
        
        widgets = {
            'cedula_apre': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1234567890'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ficha': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número de ficha'}),
            'programa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del programa'}),
            'correo_per': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@personal.com'}),
            'correo_ins': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@institucional.edu.co'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de cuenta'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '3001234567'}),
        }
        
        labels = {
            'cedula_apre': 'Cédula',
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'ficha': 'Número de Ficha',
            'programa': 'Programa de Formación',
            'correo_per': 'Correo Personal',
            'correo_ins': 'Correo Institucional',
            'numero_cuenta': 'Número de Cuenta',
            'telefono': 'Teléfono',
        }
    
    # =================== VALIDACIONES ===================
    
    def clean_acepta_tratamiento_datos(self):
        acepta = self.cleaned_data.get('acepta_tratamiento_datos')
        if not acepta:
            raise ValidationError(
                "Debe aceptar el tratamiento de datos personales y financieros "
                "para poder registrarse y recibir viáticos del semillero."
            )
        return acepta
    
    def clean_tipo_doc(self):
        tipo_doc = self.cleaned_data.get('tipo_doc')
        if not tipo_doc:
            raise ValidationError("Debe seleccionar un tipo de documento.")
        return tipo_doc
    
    def clean_medio_bancario(self):
        medio = self.cleaned_data.get('medio_bancario')
        if not medio:
            raise ValidationError("Debe seleccionar una entidad bancaria.")
        return medio
    
    def clean_modalidad(self):
        modalidad = self.cleaned_data.get('modalidad')
        if not modalidad:
            raise ValidationError("Debe seleccionar una modalidad.")
        return modalidad
    
    def clean_cedula_apre(self):
        cedula = self.cleaned_data.get('cedula_apre')
        if not cedula:
            raise ValidationError("La cédula es obligatoria.")
            
        queryset = Aprendiz.objects.filter(cedula_apre=cedula)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError("Esta cédula ya está registrada.")
        
        cedula_str = str(cedula)
        if len(cedula_str) < 7 or len(cedula_str) > 10:
            raise ValidationError("La cédula debe tener entre 7 y 10 dígitos.")
        
        return cedula
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono:
            raise ValidationError("El teléfono es obligatorio.")
            
        telefono = telefono.replace(' ', '').replace('-', '')
        
        if not telefono.isdigit():
            raise ValidationError("El teléfono debe contener solo números.")
        
        if len(telefono) != 10:
            raise ValidationError("El teléfono debe tener exactamente 10 dígitos.")
        
        if not telefono.startswith('3'):
            raise ValidationError("El número debe comenzar con 3.")
        
        return telefono
    
    def clean_correo_ins(self):
        correo = self.cleaned_data.get('correo_ins')
        if not correo:
            raise ValidationError("El correo institucional es obligatorio.")
            
        queryset = Aprendiz.objects.filter(correo_ins=correo)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise ValidationError("Este correo institucional ya está registrado.")
        
        return correo
    
    def clean_correo_per(self):
        correo = self.cleaned_data.get('correo_per')
        if not correo:
            raise ValidationError("El correo personal es obligatorio.")
            
        queryset = Aprendiz.objects.filter(correo_per=correo)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise ValidationError("Este correo personal ya está registrado.")
        
        return correo
    
    def clean_ficha(self):
        ficha = self.cleaned_data.get('ficha')
        if not ficha:
            raise ValidationError("El número de ficha es obligatorio.")
        return ficha
    
    def clean_programa(self):
        programa = self.cleaned_data.get('programa')
        if not programa or not programa.strip():
            raise ValidationError("El programa de formación es obligatorio.")
        return programa.strip()
    
    def clean_numero_cuenta(self):
        numero = self.cleaned_data.get('numero_cuenta')
        if not numero:
            raise ValidationError("El número de cuenta es obligatorio.")
        
        numero = numero.replace(' ', '').replace('-', '')
        
        if not numero.isdigit():
            raise ValidationError("El número de cuenta debe contener solo números.")
        
        if len(numero) < 6 or len(numero) > 20:
            raise ValidationError("El número de cuenta debe tener entre 6 y 20 dígitos.")
        
        return numero
    
    # =================== GUARDAR (CIFRAR NÚMERO DE CUENTA) ===================
    def save(self, commit=True):
        aprendiz = super().save(commit=False)
        
        # Cifrar el número de cuenta
        numero_cuenta = self.cleaned_data.get('numero_cuenta')
        if numero_cuenta:
            aprendiz.numero_cuenta = cifrar(numero_cuenta)
        
        # Guardar fecha de aceptación
        if self.cleaned_data.get('acepta_tratamiento_datos'):
            aprendiz.fecha_aceptacion_datos = timezone.now()
        
        if commit:
            aprendiz.save()
        
        return aprendiz

class FormularioSoporte(forms.Form):
    nombreCompleto = forms.CharField(max_length=100, label="Nombre completo")
    email = forms.EmailField(label="Email de contacto")
    asunto = forms.CharField(max_length=200, label="Asunto")
    descripcion = forms.CharField(widget=forms.Textarea, label="Descripción detallada del problema")
    urgencia = forms.ChoiceField(
        choices=[
            ('critico', 'Crítico'),
            ('importante', 'Importante'),
            ('general', 'Generales'),
        ],
        label="Nivel de urgencia"
    )
   