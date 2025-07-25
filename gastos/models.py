from django.db import models
from django.contrib.auth.models import User

class Movimiento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=[('ingreso', 'Ingreso'), ('gasto', 'Gasto')])
    descripcion = models.TextField(blank=True)
    CATEGORIAS_CHOICES = [
    ('alimento', 'Alimentación'),
    ('transporte', 'Transporte'),
    ('salario', 'Salario'),
    ('gasolina', 'Gasolina'),
    ('arriendo', 'Arriendo'),
    ('servicios', 'Servicios'),
    ('creditos', 'Creditos'),
    ('targeta de credito', 'Targeta de credito'),
    ('otros', 'Otros'),
    ]
    categoria = models.CharField(max_length=50, choices=CATEGORIAS_CHOICES, default='otros')
    fecha = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)
    comprobante = models.FileField(upload_to='comprobantes/', blank=True, null=True)
    nota = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.tipo.title()} de {self.monto} el {self.fecha}"

