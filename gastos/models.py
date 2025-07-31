from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import os

def validar_archivo_comprobante(archivo):
    """
    Validador personalizado para archivos de comprobante.
    Verifica tipo, tamaño y extensión del archivo.
    """
    # Extensiones permitidas
    extensiones_permitidas = ['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx']

    # Tamaño máximo: 5MB
    tamaño_maximo = 5 * 1024 * 1024 # 5MB en bytes

    # Verificar extensión
    estension = os.path.splitext(archivo.name)[1].lower()
    if extension not in extensiones_permitidas:
        raise ValidationError(
            f'Tipo de archivo no permitido. Extensiones válidas: {", ".join(extensiones_permitidas)}'
        )
    
    # Verificar tamaño
    if archivo.size > tamaño_maximo:
        raise ValidationError(
            f'El atchivo es muy grande. Tamaño máximo permitido: 5MB'
        )
    
class Movimiento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    monto = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Monto del movimiento (max. 12 dígitos, 2 decimales)"
    )
    tipo = models.CharField(
        max_length=10, 
        choices=[('ingreso', 'Ingreso'), ('gasto', 'Gasto')],
        help_text="Tipo de movimiento"
    )
    descripcion = models.TextField(
        blank=True,
        max_length=50, # Limitar caracteres
        help_text="Descripción del movimiento (máx. 50 caracteres)"
    )

    CATEGORIAS_CHOICES = [
        ('alimento', 'Alimentación'),
        ('transporte', 'Transporte'),
        ('salario', 'Salario'),
        ('gasolina', 'Gasolina'),
        ('arriendo', 'Arriendo'),
        ('servicios', 'Servicios'),
        ('creditos', 'Créditos'),
        ('targeta_credito', 'Targeta de crédito'),
        ('otros', 'Otros'),
    ]

    categoria = models.CharField(
        max_length=50, 
        choices=CATEGORIAS_CHOICES, 
        default='otros'
    )
    fecha = models.DateField(help_text="Fecha del movimiento")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    comprobante = models.FileField(
        upload_to='comprobantes/', 
        blank=True, 
        null=True,
       #validators=[validar_archivo_comprobante],
        help_text="Archivo de comprobante (JPG, PNG, PDF, DOC - máx. 5MB)"
    )
    nota = models.TextField(
        blank=True, 
        null=True,
        max_length=150, # Limitar caracteres
        help_text="Notas adicionales (máx. 150 caracteres)"
    )

    class Meta:
        ordering = ['-fecha', '-creado_en'] # Ordenamiento por defecto
        indexes = [
            models.Index(fields=['usuario', 'fecha']), # Indice compuesto
            models.Index(fields=['usuario', 'tipo']),
            models.Index(fields=['usuario', 'categoria']),
        ]
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"

    def clean(self):
        """
        Validaciones personalizadas que se ejecutan antes de guardar.
        Django llana automáticamente a este método.
        """    
        errors = {}

        # Validar que el monto sea positivo
        if self.monto is not None and self.monto <= 0:
            errors['monto'] = 'El monto debe ser mayor a cero.'

        # Validar que el monto no sea excesivamente grande
        if self.monto is not None and self.monto > Decimal('999999999.99'):
            errors['monto'] = 'El monto es demasiado grande.'

        # Validar fecha no muy futura (máximo 1 año)
        if self.fecha:
            fecha_limite = timezone.now().date().replace(year=timezone.now().year + 1)
            if self.fecha > fecha_limite:
                errors['fecha'] = 'La fecha no puede ser más de un año en el futuro.'
        
        # Validar que la descripción no sea solo espacios en blanco
        if self.descripcion and not self.descripcion.strip():
            errors['descripcion'] = 'La descripción no puede estar vacía o contener solo espacios.'
        
        # Si hay errores, levantarlos
        if errors:
            raise ValidationError(errors)
        
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para ejecutar validaciones adicionales
        """
        # Limpiar espacios en blanco de la descripción
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
        
        if self.nota:
            self.nota = self.nota.strip()
        
        # Ejecutar validaciones personalizadas
        self.full_clean()
        
        # Llamar al save original
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo.title()} de {self.monto} el {self.fecha}"

    # Métodos personalizados útiles
    def es_ingreso(self):
        """Retorna True si es un ingreso"""
        return self.tipo == 'ingreso'
    
    def es_gasto(self):
        """Retorna True si es un gasto"""
        return self.tipo == 'gasto'
    
    def get_monto_formateado(self):
        """Retorna el monto formateado como string"""
        return f"${self.monto:,.2f}"
    
    def tiene_comprobante(self):
        """Retorna True si tiene comprobante adjunto"""
        return bool(self.comprobante)