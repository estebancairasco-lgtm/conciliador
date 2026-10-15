# Frontend – Conciliador de facturas y retenciones

Angular 21 (standalone components + signals) · TypeScript 5.9

## Requisitos
- Node.js 20.19+, 22.12+ o 24+ (probado con Node 24 y npm 11). Verifica con `node -v` y `npm -v`.
- El backend corriendo en `http://localhost:8000` (ver `../backend/README.md`).

## Ejecutar en Windows (PowerShell)
```powershell
cd frontend
npm install
npm start
```
Abre http://localhost:4200.

Si PowerShell dice que la ejecución de scripts está deshabilitada al usar `npm`:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## Ejecutar en Linux / macOS
```bash
cd frontend
npm install
npm start
```

## Uso
1. Selecciona `facturas.csv` y `contabilidad.csv` (están en `../datos_prueba`).
2. Pulsa **Procesar**.
3. Revisa el resumen (total, correctas, con inconsistencia y causas) y la tabla de detalle.
4. Filtra por estado (Todos / Correcta / Con inconsistencia) o busca por id de factura.

## Estructura
```
src/app/
├── config.ts                      URL del backend (API_URL)
├── models/resultado.ts            Tipos de la respuesta de la API
├── services/conciliador.service.ts  POST /api/conciliar (multipart)
└── components/
    ├── carga-archivos/            Selección de archivos y botón Procesar
    ├── resumen-cards/             Totales y causas
    └── tabla-resultados/          Tabla con filtro por estado y búsqueda
```
`app.ts` coordina el flujo y muestra los mensajes de carga y de error
(backend apagado, archivo inválido, columnas faltantes).

## Si el backend corre en otro puerto
Edita `API_URL` en `src/app/config.ts`. El backend solo acepta peticiones del
origen `http://localhost:4200` (CORS, configurado en `backend/app/main.py`).

## Compilar para producción
```powershell
npm run build
```
Genera la carpeta `dist/`.
