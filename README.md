# CCC · Calculadora web de optimización

Aplicación pública para resolver el problema de ubicación de plantas de **Cosmic Computer Company**, ejemplo 8.4 de Mathur y Solow (1996).

## Características

- Editar las capacidades, los costos fijos, las demandas y los costos de transporte.
- Resolver automáticamente mediante programación entera mixta (SciPy `milp`).
- Identificar plantas abiertas, rutas elegidas y costo mínimo.
- Comprobar la demanda y descargar las cantidades enviadas como CSV.
- Informar si la demanda es imposible de cubrir.

## Ejecutar en tu PC

Abre una terminal en esta carpeta y ejecuta:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abre la dirección local que aparezca en la terminal (habitualmente http://localhost:8501).

## Publicar para que cualquiera pueda entrar

1. Crea un repositorio público en [GitHub](https://github.com/new).
2. Sube a la raíz del repositorio **`app.py`**, **`solver_ccc.py`** y **`requirements.txt`**.
3. Entra a [Streamlit Community Cloud](https://share.streamlit.io/) y entra con GitHub.
4. Selecciona **Create app**, el repositorio y el archivo principal `app.py`.
5. Pulsa **Deploy**. El servicio creará un enlace `https://<nombre>.streamlit.app` para compartir.

No se necesita ejecutar tu computador cuando la aplicación esté alojada en Streamlit Community Cloud. La disponibilidad está sujeta a las políticas del proveedor.

## Notas

- El programa usa los valores originales del ejemplo como configuración inicial.
- No incluye inicio de sesión ni guarda datos en una base de datos: cada sesión edita sus propios valores temporalmente.
- Los costos en el ejemplo se expresan en las mismas unidades monetarias del libro.
- Se necesita un repositorio y una cuenta de alojamiento para generar un enlace público. El archivo ZIP por sí solo no constituye un sitio publicado.
