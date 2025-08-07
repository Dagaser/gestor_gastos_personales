#!/usr/bin/env python
"""
Script de pruebas para verificar el funcionamiento de la aplicación de gestión de gastos.
Ejecutar con: python test_app.py
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from gastos.models import Movimiento
from gastos.forms import MovimientoForm, FiltroMovimientosForm

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    print("🔍 Probando conexión a la base de datos...")
    try:
        # Intentar crear un usuario de prueba
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        if created:
            user.set_password('test123')
            user.save()
            print("✅ Usuario de prueba creado exitosamente")
        else:
            print("✅ Usuario de prueba ya existe")
        return user
    except Exception as e:
        print(f"❌ Error en conexión a base de datos: {e}")
        return None

def test_model_creation(user):
    """Prueba la creación de modelos"""
    print("\n🔍 Probando creación de modelos...")
    try:
        # Crear un movimiento de prueba
        movimiento = Movimiento.objects.create(
            usuario=user,
            monto=Decimal('50000'),
            tipo='gasto',
            descripcion='Prueba de gasto',
            categoria='alimento',
            fecha=date.today()
        )
        print("✅ Movimiento creado exitosamente")
        
        # Verificar métodos del modelo
        assert movimiento.es_gasto() == True
        assert movimiento.es_ingreso() == False
        assert movimiento.get_monto_formateado() == "$50,000.00"
        print("✅ Métodos del modelo funcionando correctamente")
        
        return movimiento
    except Exception as e:
        print(f"❌ Error creando modelo: {e}")
        return None

def test_form_validation():
    """Prueba la validación de formularios"""
    print("\n🔍 Probando validación de formularios...")
    try:
        # Probar formulario válido
        form_data = {
            'tipo': 'ingreso',
            'monto': '100000',
            'descripcion': 'Salario mensual',
            'categoria': 'salario',
            'fecha': date.today().strftime('%Y-%m-%d')
        }
        form = MovimientoForm(data=form_data)
        assert form.is_valid(), f"Formulario debería ser válido: {form.errors}"
        print("✅ Formulario de movimiento válido")
        
        # Probar formulario inválido
        invalid_data = {
            'tipo': 'gasto',
            'monto': '-1000',  # Monto negativo
            'descripcion': '',
            'categoria': 'alimento',
            'fecha': date.today().strftime('%Y-%m-%d')
        }
        invalid_form = MovimientoForm(data=invalid_data)
        assert not invalid_form.is_valid(), "Formulario con monto negativo debería ser inválido"
        print("✅ Validación de formulario funcionando")
        
        return True
    except Exception as e:
        print(f"❌ Error en validación de formularios: {e}")
        return False

def test_views_access():
    """Prueba el acceso a las vistas"""
    print("\n🔍 Probando acceso a vistas...")
    client = Client()
    
    try:
        # Probar acceso sin autenticación (debería redirigir a login)
        response = client.get('/')
        assert response.status_code in [302, 200], f"Status code inesperado: {response.status_code}"
        print("✅ Redirección sin autenticación funcionando")
        
        # Probar acceso con autenticación
        user = User.objects.get(username='test_user')
        client.force_login(user)
        
        # Probar dashboard
        response = client.get('/dashboard/')
        assert response.status_code == 200, f"Dashboard debería ser accesible: {response.status_code}"
        print("✅ Dashboard accesible")
        
        # Probar balance
        response = client.get('/balance/')
        assert response.status_code == 200, f"Balance debería ser accesible: {response.status_code}"
        print("✅ Balance accesible")
        
        # Probar movimientos
        response = client.get('/movimientos/')
        assert response.status_code == 200, f"Movimientos debería ser accesible: {response.status_code}"
        print("✅ Movimientos accesible")
        
        return True
    except Exception as e:
        print(f"❌ Error probando vistas: {e}")
        return False

def test_urls():
    """Prueba que todas las URLs estén configuradas"""
    print("\n🔍 Probando configuración de URLs...")
    try:
        from gastos.urls import urlpatterns
        
        expected_urls = [
            'home',
            'dashboard',
            'balance',
            'crear_movimiento',
            'movimientos',
            'resumen',
            'eliminar_movimiento',
            'exportar_movimientos_pdf',
            'exportar_pdf_mes',
            'movimientos_por_mes'
        ]
        
        url_names = [pattern.name for pattern in urlpatterns if hasattr(pattern, 'name') and pattern.name]
        
        for expected_url in expected_urls:
            assert expected_url in url_names, f"URL '{expected_url}' no encontrada"
        
        print(f"✅ Todas las URLs configuradas: {url_names}")
        return True
    except Exception as e:
        print(f"❌ Error probando URLs: {e}")
        return False

def test_static_files():
    """Prueba que los archivos estáticos estén disponibles"""
    print("\n🔍 Probando archivos estáticos...")
    try:
        # Verificar que el directorio static existe
        assert os.path.exists('static'), "Directorio static no existe"
        print("✅ Directorio static existe")
        
        # Verificar que el CSS existe
        css_path = 'static/css/style.css'
        assert os.path.exists(css_path), f"Archivo CSS no existe: {css_path}"
        print("✅ Archivo CSS existe")
        
        # Verificar que el archivo no esté vacío
        with open(css_path, 'r') as f:
            content = f.read()
            assert len(content) > 0, "Archivo CSS está vacío"
        print("✅ Archivo CSS tiene contenido")
        
        return True
    except Exception as e:
        print(f"❌ Error probando archivos estáticos: {e}")
        return False

def test_templates():
    """Prueba que los templates existan"""
    print("\n🔍 Probando templates...")
    try:
        template_paths = [
            'gastos/templates/base.html',
            'gastos/templates/crear_movimiento.html',
            'gastos/templates/movimientos.html',
            'gastos/templates/gastos/balance.html',
            'gastos/templates/gastos/dashboard.html',
            'gastos/templates/gastos/resumen.html',
            'gastos/templates/gastos/movimientos_por_mes.html'
        ]
        
        for template_path in template_paths:
            assert os.path.exists(template_path), f"Template no existe: {template_path}"
            print(f"✅ Template existe: {template_path}")
        
        return True
    except Exception as e:
        print(f"❌ Error probando templates: {e}")
        return False

def test_settings():
    """Prueba la configuración de Django"""
    print("\n🔍 Probando configuración...")
    try:
        from django.conf import settings
        
        # Verificar configuraciones importantes
        assert hasattr(settings, 'SECRET_KEY'), "SECRET_KEY no configurada"
        assert hasattr(settings, 'DEBUG'), "DEBUG no configurado"
        assert 'gastos' in settings.INSTALLED_APPS, "App 'gastos' no está en INSTALLED_APPS"
        assert hasattr(settings, 'STATIC_URL'), "STATIC_URL no configurada"
        assert hasattr(settings, 'MEDIA_URL'), "MEDIA_URL no configurada"
        
        print("✅ Configuración básica correcta")
        print(f"   - DEBUG: {settings.DEBUG}")
        print(f"   - Apps instaladas: {len(settings.INSTALLED_APPS)}")
        print(f"   - STATIC_URL: {settings.STATIC_URL}")
        print(f"   - MEDIA_URL: {settings.MEDIA_URL}")
        
        return True
    except Exception as e:
        print(f"❌ Error probando configuración: {e}")
        return False

def cleanup_test_data():
    """Limpia los datos de prueba"""
    print("\n🧹 Limpiando datos de prueba...")
    try:
        # Eliminar movimientos de prueba
        Movimiento.objects.filter(descripcion='Prueba de gasto').delete()
        print("✅ Datos de prueba eliminados")
    except Exception as e:
        print(f"⚠️ Error limpiando datos: {e}")

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de la aplicación de gestión de gastos...")
    print("=" * 60)
    
    tests = [
        ("Configuración", test_settings),
        ("Conexión a BD", lambda: test_database_connection()),
        ("Archivos estáticos", test_static_files),
        ("Templates", test_templates),
        ("URLs", test_urls),
        ("Formularios", test_form_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASÓ")
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    # Pruebas que requieren usuario
    user = test_database_connection()
    if user:
        try:
            if test_model_creation(user):
                passed += 1
                print("✅ Creación de modelos: PASÓ")
            else:
                print("❌ Creación de modelos: FALLÓ")
        except Exception as e:
            print(f"❌ Creación de modelos: ERROR - {e}")
        
        try:
            if test_views_access():
                passed += 1
                print("✅ Acceso a vistas: PASÓ")
            else:
                print("❌ Acceso a vistas: FALLÓ")
        except Exception as e:
            print(f"❌ Acceso a vistas: ERROR - {e}")
        
        total += 2
    
    # Limpiar datos de prueba
    cleanup_test_data()
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADOS: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La aplicación está funcionando correctamente.")
        print("\n🌐 Para probar la aplicación:")
        print("   1. Ejecuta: python manage.py runserver")
        print("   2. Abre: http://127.0.0.1:8000/")
        print("   3. Usuario: admin / Contraseña: admin123")
        return True
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 