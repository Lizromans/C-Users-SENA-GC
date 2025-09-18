from django.db import models

class Usuario(models.Model):
    cedula = models.IntegerField(primary_key=True)
    nom_usu = models.CharField(max_length=250)
    ape_usu = models.CharField(max_length=250)
    link = models.CharField(max_length=250, null=True, blank=True)
    telefono = models.CharField(max_length=250, null=True, blank=True)
    correo_per = models.CharField(max_length=250, null=True, blank=True)
    correo_ins = models.CharField(max_length=250)
    rol = models.CharField(max_length=250)
    vinculacion_laboral = models.CharField(max_length=250, null=True, blank=True)
    dependencia = models.CharField(max_length=250, null=True, blank=True)
    estado = models.CharField(max_length=250)
    contraseña = models.CharField(max_length=250)
    conf_contraseña = models.CharField(max_length=250)
    token_verificacion = models.CharField(max_length=250, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)
    email_verificado = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    imagen_perfil = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.nom_usu} {self.ape_usu}"


class Semillero(models.Model):
    cod_sem = models.IntegerField(primary_key=True)
    sigla = models.CharField(max_length=250)
    nombre = models.CharField(max_length=250)
    desc_sem = models.TextField()
    objetivo = models.TextField()
    estado = models.CharField(max_length=250)

    def __str__(self):
        return self.nombre


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
    numero_cuenta = models.IntegerField()
    modalidad = models.CharField(max_length=45)
    telefono = models.CharField(max_length=45)
    estado_apre = models.CharField(max_length=45)
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


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
    cod_form = models.IntegerField()

    def __str__(self):
        return self.nom_pro


class Documento(models.Model):
    cod_doc = models.IntegerField(primary_key=True)
    nom_doc = models.CharField(max_length=250)
    fecha_doc = models.CharField(max_length=250)
    ver_doc = models.IntegerField()
    tipo = models.CharField(max_length=250)
    archivo = models.CharField(max_length=250)

    def __str__(self):
        return self.nom_doc


class Entregable(models.Model):
    cod_entre = models.IntegerField(primary_key=True)
    numero = models.IntegerField()
    nom_entre = models.CharField(max_length=250)
    fecha_entre = models.CharField(max_length=250)
    desc_entre = models.CharField(max_length=250)
    estado = models.CharField(max_length=45)
    archivo = models.CharField(max_length=250)
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE)

    def __str__(self):
        return self.nom_entre


class Evento(models.Model):
    cod_eve = models.IntegerField(primary_key=True)
    nom_eve = models.CharField(max_length=250)
    fecha_eve = models.CharField(max_length=250)
    desc_eve = models.CharField(max_length=250)
    modalidad_eve = models.CharField(max_length=250)
    direccion_eve = models.CharField(max_length=250)

    def __str__(self):
        return self.nom_eve


# Tablas intermedias (relaciones ManyToMany)
class SemilleroDocumento(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cod_doc = models.ForeignKey(Documento, on_delete=models.CASCADE)


class SemilleroEvento(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cod_eve = models.ForeignKey(Evento, on_delete=models.CASCADE)


class SemilleroProyecto(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cod_pro = models.ForeignKey(Proyecto, on_delete=models.CASCADE)


class SemilleroUsuario(models.Model):
    cod_sem = models.ForeignKey(Semillero, on_delete=models.CASCADE)
    cedula = models.ForeignKey(Usuario, on_delete=models.CASCADE)
