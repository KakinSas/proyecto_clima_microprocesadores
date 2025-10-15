# Proyecto de Monitoreo Climático 🌤️

Sistema de monitoreo y predicción de datos meteorológicos utilizando Arduino, Raspberry Pi y Machine Learning.

## Descripción

Este proyecto captura datos climáticos mediante sensores conectados a Arduinos y Raspberry Pi, procesa la información con un modelo de predicción, y visualiza los datos en una aplicación web en tiempo real.

## Tecnologías Utilizadas

### Backend

- **Python 3.13+**
- **Flask** - Framework web
- **SQLite** - Base de datos

### Frontend

- **HTML5/CSS3/JavaScript**
- **Chart.js** - Visualización de gráficos

## Estructura del Proyecto

```
proyecto_clima/
├── app.py                 # Aplicación principal Flask
├── database.py            # Gestión de base de datos
├── requirements.txt       # Dependencias Python
├── data/                  # Base de datos SQLite
├── static/                # Archivos estáticos
│   ├── css/              # Estilos
│   ├── js/               # JavaScript
│   └── img/              # Imágenes
└── templates/             # Templates HTML
    └── index.html
```

## Instalación

### Prerequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos para configurar el proyecto

1. **Clonar el repositorio**

```bash
git clone <url-del-repositorio>
cd proyecto_clima
```

2. **Crear entorno virtual**

```bash
# Windows (PowerShell)
py -m venv venv

# Linux/Mac
python3 -m venv venv
```

3. **Activar entorno virtual**

```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat

# Desactivar
Para desactivar el entorno virtual, utilizar comando "deactivate"
```

4. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

5. **Base de datos**

```bash
# Inicializar la base de datos (e insertar datos de prueba)
python database.py

# Para visualizarla directamente, se puede utilizar la extensión "SQLite" de VsCode, al instalarla:
1. Se presiona Ctrl+Shift+P.
2. Se busca SQLite
3. Se presiona "SQLite: Open Database" y se selecciona el archivo clima.db que se generó al ejecutar database.py.
4. En la parte inferior izquierda de la pantalla se creará el menú "SQLite explorer", donde se pueden viasualizar las tablas.
```

6. **Ejecutar la aplicación**

```bash
python app.py
```

7. **Abrir en el navegador**

```
http://localhost:5000
```
