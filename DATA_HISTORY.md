# Datos y huecos de IDs

Antes de cargar los datos demo, la base contenía estos registros relevantes: `auth_user` 1 (`bruno`, administrador y dueño) y 3 (`ezequiel`, paseador); mascota 1 (`Chayio`); servicio 1 (ofrecido por el usuario 3); reserva 1 (dueño 1, servicio 1, completada); y calificación 2 (reserva 1, puntaje 4).

Los IDs `auth_user` 2, 4, 5, 6 y 7; reservas 2 y 3; mascota 2; servicios 2 y 3; y calificación 1 no estaban presentes en `db.sqlite3`. La base actual no guarda el contenido anterior ni un registro de quién o por qué eliminó esas filas, así que no es posible identificar qué datos eran ni explicar su eliminación sin una copia de seguridad o un historial externo. No se borró ninguna fila como parte de estos cambios.

Las cuentas, mascotas, servicios, reservas y calificaciones de prueba nuevas se cargan con `python manage.py seed_demo_data`; la contraseña se configura mediante `CHAYIO_DEMO_PASSWORD` y no queda guardada en este archivo.

Teléfono, dirección y descripción son opcionales para dueños y paseadores; la descripción también es opcional en el registro. El perfil 1 se completó con datos de prueba (`0000000001` y `Dirección de prueba`), no con datos de contacto verificados.