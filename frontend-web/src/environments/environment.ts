/**
 * Configuración de entorno del frontend web.
 * `apiUrl` apunta al backend FastAPI (prefijo /api/v1 incluido).
 */
const apiHost = window.location.hostname || '127.0.0.1';

export const environment = {
  production: true,
  // Desde un celular en el mismo Wi-Fi usa automáticamente la IP/nombre del PC
  // que sirvió la página, en vez del localhost del propio teléfono.
  apiUrl: `http://${apiHost}:8000/api/v1`,
};
