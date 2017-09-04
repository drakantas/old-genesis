# Genesis

-----

App web para gestionar proyectos de tesis.

## Creación de BD

Antes de comenzar con la configuración de la app, es necesario crear un usuario y base de datos que pertenezca a este usuario. El nuevo usuario es necesario por motivos de seguridad, aunque eres libre de user el usuario postgres.

### Usuario

```sql
CREATE USER genesis_app WITH LOGIN NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT -1 PASSWORD 'contraseña';
```

### BD

```sql
CREATE DATABASE genesis WITH OWNER = genesis_app ENCODING = 'UTF8' CONNECTION LIMIT = -1;
```

## Instalar entorno virtual

### Instalar pipenv
```
python -m pip install pipenv
```

### Crear entorno virtual para la app
```
pipenv --python "C:\Users\<MiUsuario>\AppData\Local\Programs\Python\Python36\python.exe"
```
Reemplazar la dirección por donde sea tengas instalado Python3.6

### Instalar dependencias
```
pipenv install
```

## Activar entorno virtual

```
pipenv shell
python app.py
```

O tambien:
```
pipenv run python app.py
```

## Configuración

Crear un archivo llamado `config.py`, este estarán la configuración del servidor y app. Los siguientes valores son soportados:
```python
from modules import users

host = '127.0.0.1'
port = 80
templates_path = 'views'
static_resources_path = 'static'
db_dsn = 'postgresql://usuario:contraseña@host/bd' # Reemplazar por la configuración que tienes

modules = (users,) # Los módulos de la aplicación, por ahora solo se tiene este

```

También, es necesario que se generen los archivos estáticos, los cuales he decidido no subirlos para no corromper las estadísticas del repositorio. Para generar los archivos estáticos, instalar Node.js v8 y luego ejecutar lo siguiente en la consola, habiendo habilitado el entorno de trabajo:
```
npm install
```
Luego, para entorno de desarrollo:
```
npm run dev
```
y producción:
```
npm run prod
```
