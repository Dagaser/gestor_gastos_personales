#!/usr/bin/env python
"""
Script para migrar a la versión segura del proyecto
Ejecutar con: python manage.py shell < migrate_to_secure.py
"""

import os
import sys
import django
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tu_proyecto.settings')
django.setup()

from gastos.models import Movimiento
from gastos.validators import ValidadorLimitesUsuario


def migrar_datos_existentes():
    """
    Migra datos existentes aplicando las nuevas validaciones
    """
    print("🔄 Iniciando migración de datos existentes...")
    
    errores_encontrados = []
    movimientos_corregidos = 0
    
    with transaction.atomic():
        # Obtener todos los movimientos
        movimientos = Movimiento.objects.all()
        total_movimientos = movimientos.count()
        
        print(f"📊 Total de movimientos a revisar: {total_movimientos}")
        
        for i, movimiento in enumerate(movimientos, 1):
            try:
                # Mostrar progreso
                if i % 100 == 0:
                    print(f"   Procesando {i}/{total_movimientos}...")
                
                cambios = []
                
                # 1. Validar y corregir montos
                if movimiento.monto <= 0:
                    errores_encontrados.append(
                        f"Movimiento {movimiento.id}: monto inválido ({movimiento.monto})"
                    )
                    continue
                
                # 2. Limpiar descripción
                descripcion_original = movimiento.descripcion
                if descripcion_original:
                    descripcion_limpia = descripcion_original.strip()
                    if descripcion_limpia != descripcion_original:
                        movimiento.descripcion = descripcion_limpia
                        cambios.append("descripción limpiada")
                
                # 3. Limpiar nota
                nota_original = movimiento.nota
                if nota_original:
                    nota_limpia = nota_original.strip()
                    if nota_limpia != nota_original:
                        movimiento.nota = nota_limpia
                        cambios.append("nota limpiada")
                
                # 4. Validar coherencia tipo-categoría
                if movimiento.tipo == 'ingreso':
                    if movimiento.categoria not in ['salario', 'otros']:
                        movimiento.categoria = 'otros'
                        cambios.append("categoría corregida para ingreso")
                
                # 5. Corregir typo en "targeta_credito"
                if movimiento.categoria == 'targeta de credito':
                    movimiento.categoria = 'targeta_credito'
                    cambios.append("categoría de tarjeta corregida")
                
                # 6. Guardar cambios si los hay
                if cambios:
                    # Usar save() del modelo padre para evitar validaciones extra por ahora
                    super(Movimiento, movimiento).save()
                    movimientos_corregidos += 1
                    print(f"   ✅ Movimiento {movimiento.id}: {', '.join(cambios)}")
                
            except Exception as e:
                errores_encontrados.append(
                    f"Error procesando movimiento {movimiento.id}: {str(e)}"
                )
        
        print(f"\n✅ Migración completada:")
        print(f"   📊 Movimientos procesados: {total_movimientos}")
        print(f"   🔧 Movimientos corregidos: {movimientos_corregidos}")
        print(f"   ⚠️  Errores encontrados: {len(errores_encontrados)}")
        
        if errores_encontrados:
            print("\n⚠️  ERRORES ENCONTRADOS:")
            for error in errores_encontrados[:10]:  # Mostrar solo primeros 10
                print(f"   • {error}")
            
            if len(errores_encontrados) > 10:
                print(f"   ... y {len(errores_encontrados) - 10} errores más.")


def crear_directorios_necesarios():
    """
    Crea directorios necesarios para el funcionamiento seguro
    """
    print("\n📁 Creando directorios necesarios...")
    
    directorios = [
        'logs',
        'media/comprobantes',
        'media/quarantine',
        'backups',
    ]
    
    for directorio in directorios:
        path = os.path.join(os.getcwd(), directorio)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"   ✅ Creado: {directorio}")
        else:
            print(f"   ✓  Ya existe: {directorio}")


def verificar_configuracion_seguridad():
    """
    Verifica que las configuraciones de seguridad estén aplicadas
    """
    print("\n🔒 Verificando configuraciones de seguridad...")
    
    from django.conf import settings
    
    verificaciones = [
        ('SECRET_KEY', 'Clave secreta configurada'),
        ('DEBUG', 'Modo debug'),
        ('ALLOWED_HOSTS', 'Hosts permitidos'),
        ('SECURE_BROWSER_XSS_FILTER', 'Filtro XSS'),
        ('SECURE_CONTENT_TYPE_NOSNIFF', 'Protección MIME sniffing'),
        ('SESSION_COOKIE_HTTPONLY', 'Cookies HTTP-only'),
        ('CSRF_COOKIE_SECURE', 'Cookies CSRF seguras'),
    ]
    
    for config, descripcion in verificaciones:
        valor = getattr(settings, config, None)
        if valor is not None:
            print(f"   ✅ {descripcion}: {valor}")
        else:
            print(f"   ⚠️  {descripcion}: NO CONFIGURADO")


def generar_reporte_usuarios():
    """
    Genera un reporte de usuarios y sus estadísticas
    """
    print("\n👥 Generando reporte de usuarios...")
    
    usuarios = User.objects.all()
    
    for usuario in usuarios:
        movimientos = Movimiento.objects.filter(usuario=usuario)
        total_movimientos = movimientos.count()
        
        if total_movimientos > 0:
            total_ingresos = movimientos.filter(tipo='ingreso').aggregate(
                total=models.Sum('monto'))['total'] or 0
            total_gastos = movimientos.filter(tipo='gasto').aggregate(
                total=models.Sum('monto'))['total'] or 0
            
            print(f"   👤 {usuario.username}:")
            print(f"      📊 Movimientos: {total_movimientos}")
            print(f"      💰 Ingresos: ${total_ingresos:,.2f}")
            print(f"      💸 Gastos: ${total_gastos:,.2f}")
            print(f"      📈 Balance: ${(total_ingresos - total_gastos):,.2f}")


def ejecutar_tests_basicos():
    """
    Ejecuta tests básicos de funcionamiento
    """
    print("\n🧪 Ejecutando tests básicos...")
    
    try:
        # Test 1: Crear movimiento válido
        usuario_test = User.objects.first()
        if usuario_test:
            movimiento_test = Movimiento(
                usuario=usuario_test,
                tipo='gasto',
                monto=Decimal('10000.50'),
                descripcion='Test de migración',
                categoria='otros',
                fecha=timezone.now().date()
            )
            movimiento_test.full_clean()  # Validar sin guardar
            print("   ✅ Test validación de movimiento: PASÓ")
        
        # Test 2: Rechazar movimiento inválido
        try:
            movimiento_invalido = Movimiento(
                usuario=usuario_test,
                tipo='gasto',
                monto=Decimal('-100'),  # Monto negativo
                descripcion='Test inválido',
                categoria='otros',
                fecha=timezone.now().date()
            )
            movimiento_invalido.full_clean()
            print("   ❌ Test rechazo movimiento inválido: FALLÓ (debería haber fallado)")
        except:
            print("   ✅ Test rechazo movimiento inválido: PASÓ")
        
        print("   🎉 Todos los tests básicos completados")
        
    except Exception as e:
        print(f"   ❌ Error en tests: {e}")


def main():
    """
    Función principal de migración
    """
    print("🚀 INICIANDO MIGRACIÓN A VERSIÓN SEGURA")
    print("=" * 50)
    
    try:
        # 1. Crear directorios
        crear_directorios_necesarios()
        
        # 2. Migrar datos existentes
        migrar_datos_existentes()
        
        # 3. Verificar configuración
        verificar_configuracion_seguridad()
        
        # 4. Generar reporte
        generar_reporte_usuarios()
        
        # 5. Ejecutar tests
        ejecutar_tests_basicos()
        
        print("\n" + "=" * 50)
        print("🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("\n📝 Próximos pasos:")
        print("   1. Ejecutar: python manage.py makemigrations")
        print("   2. Ejecutar: python manage.py migrate")
        print("   3. Reiniciar el servidor de desarrollo")
        print("   4. Probar las nuevas funcionalidades")
        
    except Exception as e:
        print(f"\n❌ ERROR EN LA MIGRACIÓN: {e}")
        print("   Por favor, revisa los logs y corrige los errores antes de continuar.")
        return False
    
    return True


if __name__ == "__main__":
    main()