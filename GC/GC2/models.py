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
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=250, null=True, blank=True)
    correo_per = models.CharField(max_length=250, null=True, blank=True)
    correo_ins = models.CharField(max_length=250)
    rol = models.CharField(max_length=250)
    vinculacion_laboral = models.CharField(max_length=250, null=True, blank=True)
    dependencia = models.CharField(max_length=250, null=True, blank=True)
    estado = models.CharField(max_length=250, null=True, blank=True)
    contraseña = models.CharField(max_length=250)
    conf_contraseña = models.CharField(max_length=250)
    token_verificacion = models.CharField(max_length=250, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)
    email_verificado = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    imagen_perfil = models.ImageField(upload_to='fotos_perfil/', null=True, blank=True)
    rol_original = models.CharField(max_length=250, null=True, blank=True)
    
    grupos = models.ManyToManyField(
    Group,
    through='UsuarioGrupos', 
    related_name='usuarios',   
    blank=True,
    verbose_name='Grupos de permisos'
    )

    # Relación ManyToMany a través de tabla intermedia
    semilleros = models.ManyToManyField(
        'Semillero',
        through='SemilleroUsuario',
        related_name='usuarios'
    )

    proyectos = models.ManyToManyField(
        'Proyecto',
        through='UsuarioProyecto',
        related_name='usuarios'
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
    
    @property
    def get_iniciales(self):
        return f"{self.nom_usu[0]}{self.ape_usu[0]}".upper()
    
class UsuarioGrupos(models.Model):
    id = models.IntegerField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='cedula')
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, db_column='group_id')

    class Meta:
        managed = False
        db_table = 'usuario_grupos'
        unique_together = ('usuario', 'grupo')


class Semillero(models.Model):
    id_sem = models.AutoField(primary_key=True)
    cod_sem = models.CharField(max_length=20)
    sigla = models.CharField(max_length=250)
    nombre = models.CharField(max_length=250)
    desc_sem = models.TextField()
    objetivo = models.TextField()
    estado = models.CharField(max_length=250)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)

    # Relación ManyToMany con Proyecto (a través de tabla intermedia)
    proyectos = models.ManyToManyField(
        'Proyecto',
        through='SemilleroProyecto',
        related_name='semilleros',
        blank=True
    )

    class Meta:
        db_table = 'semillero'


class Aprendiz(models.Model):
    cedula_apre = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=60)
    apellido = models.CharField(max_length=60)
    fecha_nacimiento = models.CharField(max_length=45)
    ficha = models.IntegerField()
    programa = models.CharField(max_length=100)
    correo_per = models.CharField(max_length=250)
    correo_ins = models.CharField(max_length=250)
    medio_bancario = models.CharField(max_length=45)
    numero_cuenta = models.CharField(max_length=15)
    modalidad = models.CharField(max_length=45)
    telefono = models.CharField(max_length=45)
    estado_apre = models.CharField(max_length=45)
    id_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE, db_column='id_sem')

    class Meta:
        managed = False
        db_table = 'aprendiz'

    @property
    def get_iniciales(self):
        return f"{self.nombre[0]}{self.apellido[0]}".upper()
    
    proyectos = models.ManyToManyField(
        'Proyecto',
        through='ProyectoAprendiz',
        related_name='aprendices'
    )

class Proyecto(models.Model):
    cod_pro = models.IntegerField(primary_key=True)
    nom_pro = models.CharField(max_length=250)
    tipo = models.CharField(max_length=250)
    desc_pro = models.TextField()
    linea_tec = models.CharField(max_length=250)
    linea_inv = models.CharField(max_length=250)
    linea_sem = models.CharField(max_length=250)
    estado_pro = models.CharField(max_length=50)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    notas = models.TextField()

    class Meta:
        managed = False
        db_table = 'proyecto'

class Documento(models.Model):
    cod_doc = models.IntegerField(primary_key=True)
    nom_doc = models.CharField(max_length=250)
    fecha_doc = models.CharField(max_length=250)
    tipo = models.CharField(max_length=250)
    archivo = models.FileField(upload_to='documentos/', null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'documento'

class Entregable(models.Model):
    cod_entre = models.IntegerField(primary_key=True)
    nom_entre = models.CharField(max_length=250)
    fecha_inicio = models.CharField(max_length=250)
    fecha_fin = models.CharField(max_length=250)
    desc_entre = models.CharField(max_length=250)
    estado = models.CharField(max_length=45)
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE,db_column='cod_pro')

    class Meta:
        managed = False
        db_table = 'entregable'

class Archivo(models.Model):
    entregable = models.ForeignKey(
        Entregable,
        related_name='archivos',
        on_delete=models.CASCADE,
        db_column='cod_entre'
    )
    archivo = models.FileField(upload_to='entregables/%Y/%m/%d/')
    nombre = models.CharField(max_length=255, blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'archivo'
        managed = True

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
    id_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE, db_column='id_sem')
    cod_doc = models.ForeignKey(Documento, on_delete=models.CASCADE, db_column='cod_doc')

    class Meta:
        managed = False
        db_table = 'semillero_documento'
        unique_together = ('id_sem', 'cod_doc')  # evita duplicados


class SemilleroEvento(models.Model):
    id_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE, db_column='id_sem')
    cod_eve = models.ForeignKey(Evento, on_delete=models.CASCADE, db_column='cod_eve')

    class Meta:
        managed = False
        db_table = 'semillero_evento'
        unique_together = ('id_sem', 'cod_eve')  # evita duplicados


class SemilleroProyecto(models.Model):
    sempro_id = models.AutoField(primary_key=True)
    id_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE, db_column='id_sem')
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE, db_column='cod_pro')
    
    class Meta:
        managed = False
        db_table = 'semillero_proyecto'
        unique_together = ('id_sem', 'cod_pro')


class SemilleroUsuario(models.Model):
    semusu_id = models.AutoField(primary_key=True)
    es_lider = models.BooleanField(default=False)

    id_sem = models.ForeignKey(
        'Semillero',
        on_delete=models.CASCADE,
        db_column='id_sem' 
    )
    cedula = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        db_column='cedula' 
    )

    class Meta:
        db_table = 'semillero_usuario'
        unique_together = (('id_sem', 'cedula'),)

    def __str__(self):
        return f"{self.cedula.nom_usu} en {self.id_sem.nom_sem}"

class UsuarioProyecto(models.Model):
    usupro_id = models.AutoField(primary_key=True)
    cedula = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='cedula')
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE, db_column='cod_pro')
    es_lider_pro = models.BooleanField(default=False)
    estado = models.CharField(max_length=10, default="activo")

    class Meta:
        managed = False
        db_table = 'usuario_proyecto'
        unique_together = (('cedula', 'cod_pro'),)  # evita duplicados

class ProyectoAprendiz(models.Model):
    proapre_id = models.AutoField(primary_key=True)
    cedula_apre = models.ForeignKey(Aprendiz, on_delete=models.CASCADE, db_column='cedula_apre')
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE, db_column='cod_pro')
    estado = models.CharField(max_length=10, default="activo")  

    class Meta:
        managed = False
        db_table = 'proyecto_aprendiz'
        unique_together = ('cedula_apre', 'cod_pro')  # evita duplicados

