# Gestor de Gastos Personales

Una aplicación web completa para gestionar gastos e ingresos personales, desarrollada con Django.

## 🚀 Características

- **Gestión completa de movimientos**: Crear, editar, eliminar ingresos y gastos
- **Categorización inteligente**: Categorías predefinidas para mejor organización
- **Filtros avanzados**: Búsqueda por fecha, tipo, categoría y notas
- **Dashboard interactivo**: Estadísticas en tiempo real y gráficos
- **Exportación PDF**: Generar reportes en formato PDF
- **Interfaz moderna**: Diseño responsive y amigable
- **Seguridad robusta**: Validaciones, autenticación y protección CSRF
- **Comprobantes**: Subida de archivos de comprobantes (imágenes, PDFs)

## 📋 Requisitos

- Python 3.8+
- Django 4.2+
- Virtual environment (recomendado)

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd gestor_gastos_personales
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp env.example .env
# Editar .env con tus configuraciones
```

### 5. Aplicar migraciones
```bash
python manage.py migrate
```

### 6. Crear superusuario (opcional)
```bash
python manage.py createsuperuser
```

### 7. Ejecutar el servidor
```bash
python manage.py runserver
```

## 🌐 Uso

1. **Acceder a la aplicación**: http://127.0.0.1:8000/
2. **Registrarse/Iniciar sesión**: Usar el sistema de autenticación de Django
3. **Dashboard**: Ver estadísticas generales y resúmenes
4. **Crear movimientos**: Agregar ingresos y gastos con categorías
5. **Gestionar movimientos**: Ver, editar y eliminar movimientos
6. **Exportar reportes**: Generar PDFs de movimientos

## 📁 Estructura del Proyecto

```
gestor_gastos_personales/
├── core/                   # Configuración principal de Django
├── gastos/                 # Aplicación principal
│   ├── models.py          # Modelos de datos
│   ├── views.py           # Vistas y lógica de negocio
│   ├── forms.py           # Formularios con validaciones
│   ├── urls.py            # URLs de la aplicación
│   └── templates/         # Templates HTML
├── static/                # Archivos estáticos (CSS, JS)
├── media/                 # Archivos subidos por usuarios
├── logs/                  # Archivos de log
├── requirements.txt       # Dependencias de Python
└── manage.py             # Script de gestión de Django
```

## 🔧 Configuración

### Variables de Entorno

- `SECRET_KEY`: Clave secreta de Django
- `DEBUG`: Modo debug (True/False)
- `ALLOWED_HOSTS`: Hosts permitidos
- `DATABASE_URL`: URL de la base de datos (opcional)

### Configuración de Producción

1. Cambiar `DEBUG=False` en `.env`
2. Configurar `ALLOWED_HOSTS` con tu dominio
3. Usar una base de datos PostgreSQL
4. Configurar archivos estáticos
5. Configurar HTTPS

## 📊 Funcionalidades Principales

### Dashboard
- Balance total y del mes actual
- Top categorías de gastos
- Últimos movimientos
- Estadísticas por mes

### Gestión de Movimientos
- Crear ingresos y gastos
- Categorización automática
- Subida de comprobantes
- Validaciones de seguridad

### Filtros y Búsqueda
- Por fecha (rango)
- Por tipo (ingreso/gasto)
- Por categoría
- Por notas (búsqueda de texto)

### Exportación
- PDF de todos los movimientos
- PDF por mes específico
- Formato profesional

## 🔒 Seguridad

- **Autenticación**: Sistema de login/logout
- **Autorización**: Usuarios solo ven sus datos
- **Validaciones**: En formularios y modelos
- **CSRF Protection**: Protección contra ataques CSRF
- **File Upload Security**: Validación de archivos
- **SQL Injection Protection**: ORM de Django
- **XSS Protection**: Escape automático de datos

## 🚀 Despliegue

### Opciones de Despliegue

1. **Heroku**: Configurar Procfile y variables de entorno
2. **DigitalOcean**: Usar App Platform o Droplet
3. **AWS**: EC2 con nginx y gunicorn
4. **VPS**: Configurar servidor manualmente

### Comandos de Despliegue

```bash
# Recolectar archivos estáticos
python manage.py collectstatic

# Aplicar migraciones
python manage.py migrate

# Ejecutar con gunicorn
gunicorn core.wsgi:application
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Si tienes problemas o preguntas:

1. Revisar la documentación
2. Buscar en issues existentes
3. Crear un nuevo issue con detalles del problema

## 🔄 Actualizaciones

Para mantener el proyecto actualizado:

```bash
git pull origin main
pip install -r requirements.txt
python manage.py migrate
```

---

**Desarrollado con ❤️ usando Django**

