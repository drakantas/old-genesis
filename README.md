# Genesis

-----

App web para gestionar proyectos de tesis.

## Consultas

Antes de comenzar con la configuración de la app, es necesario crear un usuario y base de datos que pertenezca a este usuario. El nuevo usuario es necesario por motivos de seguridad, aunque eres libre de user el usuario postgres.

### Usuario

```sql
CREATE USER genesis_app WITH LOGIN NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT -1 PASSWORD 'contraseña';
```

### BD

```sql
CREATE DATABASE genesis WITH OWNER = genesis_app ENCODING = 'UTF8' CONNECTION LIMIT = -1;
```
