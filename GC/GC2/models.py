from django.db import models
import secrets
import datetime
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Group

class Usuario(models.Model):
    cedula = models.IntegerField(primary_key=True)
    nom_usu = models.CharField(max_length=250)
    ape_usu = models.CharField(max_length=250)
    fecha_nacimiento = models.CharField(max_length=250, null=True, blank=True)
    telefono = models.CharField(max_length=250, null=True, blank=True)
    correo_per = models.CharField(max_length=250, null=True, blank=True)
    correo_ins = models.CharField(max_length=250)
    rol = models.CharField(max_length=250)
    genero = models.CharField(max_length=45,null=True, blank=True)
    vinculacion_laboral = models.CharField(max_length=250, null=True, blank=True)
    dependencia = models.CharField(max_length=250, null=True, blank=True)
    estado = models.CharField(max_length=250, null=True, blank=True)
    contraseña = models.CharField(max_length=250)
    conf_contraseña = models.CharField(max_length=250)
    token_verificacion = models.CharField(max_length=250, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)
    email_verificado = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    imagen_perfil = models.IntegerField(null=True, blank=True)

    grupos = models.ManyToManyField(
    Group,
    through='UsuarioGrupos',  # ⭐ Esto es CRÍTICO
    related_name='usuarios',   # Cambié a plural
    blank=True,
    verbose_name='Grupos de permisos'
)

    class Meta:
        managed = False
        db_table = 'usuario'

    @property
    def password(self):
        return self.contraseña

    @password.setter
    def password(self, value):
        self.contraseña = value

    def get_email_field_name(self):
        return 'correo'

    def get_username(self):
        return self.nom_usu

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    def get_full_name(self):
        return self.nom_usu

    def get_short_name(self):
        return self.nom_usu

    def generar_token_verificacion(self):
        # Crear un token aleatorio
        self.token_verificacion = secrets.token_urlsafe(32)
        # El token expirará en 24 horas
        self.token_expira = timezone.now() + datetime.timedelta(hours=24)
        self.save()

    def enviar_email_verificacion(self, request):
        """Envía un correo electrónico con el enlace de verificación"""
        verificacion_url = request.build_absolute_uri(
            reverse('verificar_email', kwargs={'token': self.token_verificacion})
        )

        asunto = 'Verifica tu dirección de correo electrónico'
        mensaje = f'''
        Hola {self.nom_usu},

        Gracias por registrarte. Por favor, haz clic en el siguiente enlace para verificar tu correo electrónico:

        {verificacion_url}

        Este enlace expirará en 24 horas.

        Si no solicitaste este registro, puedes ignorar este mensaje.
        '''

        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [self.correo_ins],
            fail_silently=False,
        )

class UsuarioGrupos(models.Model):
    id = models.IntegerField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='cedula')
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, db_column='group_id')

    class Meta:
        managed = False
        db_table = 'usuario_grupos'
        unique_together = ('usuario', 'grupo')


class Semillero(models.Model):
    cod_sem = models.IntegerField(primary_key=True)
    sigla = models.CharField(max_length=250)
    nombre = models.CharField(max_length=250)
    desc_sem = models.TextField()
    objetivo = models.TextField()
    estado = models.CharField(max_length=250)

    class Meta:
        managed = False
        db_table = 'semillero'

class Aprendiz(models.Model):
    cedula_apre = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=60)
    apellido = models.CharField(max_length=60)
    fecha_nacimiento = models.CharField(max_length=45)
    genero = models.CharField(max_length=45)
    ficha = models.IntegerField()
    programa = models.CharField(max_length=100)
    correo_per = models.CharField(max_length=250)
    correo_ins = models.CharField(max_length=250)
    medio_bancario = models.CharField(max_length=45)
    numero_cuenta = models.IntegerField()
    modalidad = models.CharField(max_length=45)
    telefono = models.CharField(max_length=45)
    estado_apre = models.CharField(max_length=45)
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'aprendiz'


class Proyecto(models.Model):
    cod_pro = models.IntegerField(primary_key=True)
    nom_pro = models.CharField(max_length=250)
    tipo = models.CharField(max_length=250)
    desc_pro = models.TextField()
    linea_tec = models.CharField(max_length=250)
    linea_inv = models.CharField(max_length=250)
    linea_sem = models.CharField(max_length=250)
    can_entre = models.IntegerField()
    estado_pro = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'proyecto'

class Documento(models.Model):
    cod_doc = models.IntegerField(primary_key=True)
    nom_doc = models.CharField(max_length=250)
    fecha_doc = models.CharField(max_length=250)
    ver_doc = models.IntegerField()
    tipo = models.CharField(max_length=250)
    archivo = models.CharField(max_length=250)

    class Meta:
        managed = False
        db_table = 'documento'


class Entregable(models.Model):
    cod_entre = models.IntegerField(primary_key=True)
    numero = models.IntegerField()
    nom_entre = models.CharField(max_length=250)
    fecha_entre = models.CharField(max_length=250)
    desc_entre = models.CharField(max_length=250)
    estado = models.CharField(max_length=45)
    archivo = models.CharField(max_length=250)
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'entregable'


class Evento(models.Model):
    cod_eve = models.IntegerField(primary_key=True)
    nom_eve = models.CharField(max_length=250)
    fecha_eve = models.CharField(max_length=250)
    desc_eve = models.CharField(max_length=250)
    modalidad_eve = models.CharField(max_length=250)
    direccion_eve = models.CharField(max_length=250)

    class Meta:
        managed = False
        db_table = 'evento'


# Tablas intermedias (relaciones ManyToMany)
class SemilleroDocumento(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cod_doc = models.ForeignKey(Documento, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'semillero_documento'


class SemilleroEvento(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cod_eve = models.ForeignKey(Evento, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'semillero_evento'


class SemilleroProyecto(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'semillero_proyecto'


class SemilleroUsuario(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cedula = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'semillero_usuario'