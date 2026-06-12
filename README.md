# Practica P1 - Sentinel-2 L2A, NDVI y GeoTIFF

## 1. Objetivo del ejercicio

El objetivo de esta practica es construir una pequena aplicacion en Python capaz de descargar datos Sentinel-2 desde Copernicus Data Space Ecosystem, recortar una zona geografica indicada por el usuario, calcular el indice NDVI y generar archivos GeoTIFF georreferenciados que puedan abrirse en QGIS.

El flujo completo es:

1. Crear un entorno virtual de Python.
2. Instalar las librerias necesarias.
3. Configurar credenciales de Copernicus en un archivo `.env`.
4. Conectarse a la API de Copernicus Data Space Ecosystem.
5. Pedir al usuario las cuatro coordenadas del area de estudio.
6. Descargar bandas Sentinel-2 L2A.
7. Separar las bandas en matrices `numpy`.
8. Calcular NDVI.
9. Exportar tres archivos GeoTIFF.
10. Generar un informe numerico y un panel visual con Matplotlib.
11. Visualizar los resultados en QGIS si se desea.

## 2. Estructura del proyecto

```text
1ejersentinel/
├── ejercicio_p1.py
├── requirements.txt
├── README.md
├── .env
├── .env.example
├── .gitignore
├── abrir_qgis_limpio.sh
├── p1_resultado_ndvi.tif
├── p1_color_verdadero.tif
├── p1_falso_color.tif
├── p1_resumen_resultados.txt
└── p1_panel_visual.png
```

Descripcion de los archivos:

- `ejercicio_p1.py`: programa principal.
- `requirements.txt`: lista de dependencias Python.
- `README.md`: documentacion completa del ejercicio.
- `.env`: credenciales reales de Copernicus. No debe compartirse.
- `.env.example`: ejemplo de estructura para las credenciales.
- `.gitignore`: evita subir credenciales, entorno virtual y resultados pesados.
- `abrir_qgis_limpio.sh`: lanzador para abrir QGIS sin mezclarlo con el entorno virtual.
- `p1_resultado_ndvi.tif`: resultado NDVI.
- `p1_color_verdadero.tif`: composicion de color verdadero.
- `p1_falso_color.tif`: composicion de falso color.
- `p1_resumen_resultados.txt`: informe numerico final.
- `p1_panel_visual.png`: panel visual generado con Matplotlib.

## 3. Fuente de datos: Sentinel-2

Sentinel-2 es una mision del programa europeo Copernicus dedicada a la observacion de la Tierra. Sus satelites capturan imagenes multiespectrales, es decir, no solo recogen informacion visible para el ojo humano, sino tambien informacion en otras longitudes de onda como el infrarrojo cercano.

Esto permite estudiar:

- vegetacion,
- cultivos,
- masas de agua,
- suelo desnudo,
- cambios en el territorio,
- zonas quemadas,
- humedad y vigor vegetal.

## 4. Nivel de procesamiento utilizado: Sentinel-2 L2A

En este proyecto se descargan datos `Sentinel-2 L2A`.

Esto es importante porque el nivel de procesamiento afecta directamente a la interpretacion de los valores.

### 4.1 Que significa L2A

`L2A` significa que el producto contiene reflectancia de superficie. Es decir, los datos ya han pasado por una correccion atmosferica para reducir el efecto de la atmosfera, aerosoles y vapor de agua.

En la practica, L2A es mas adecuado para calcular indices como NDVI porque representa mejor la respuesta real de la superficie terrestre.

### 4.2 Diferencia entre L1C y L2A

`L1C`:

- reflectancia en la parte superior de la atmosfera,
- mantiene mas influencia atmosferica,
- puede servir para visualizacion o ciertos procesamientos,
- no es la opcion mas recomendable si se quiere calcular NDVI de forma directa.

`L2A`:

- reflectancia de superficie,
- incluye correccion atmosferica,
- es mas adecuada para analisis de vegetacion,
- es la opcion usada en este ejercicio.

### 4.3 Donde se ve en el codigo

En `ejercicio_p1.py` se indica aqui:

```python
data_collection=DataCollection.SENTINEL2_L2A.define_from(
    "s2l2a_cdse",
    service_url=configuracion_api.sh_base_url,
)
```

La parte clave es:

```python
DataCollection.SENTINEL2_L2A
```

Esto indica que se solicita Sentinel-2 en nivel L2A.

El identificador:

```text
s2l2a_cdse
```

es un nombre local usado para definir esta coleccion dentro del servicio de Copernicus Data Space Ecosystem.

## 5. Bandas utilizadas

El programa descarga cuatro bandas:

```text
B02 = Azul
B03 = Verde
B04 = Rojo
B08 = Infrarrojo cercano / NIR
```

Estas bandas se solicitan en el `evalscript`:

```javascript
input: ["B02", "B03", "B04", "B08"]
```

Uso de cada banda:

- `B02`, `B03`, `B04`: permiten construir una imagen de color verdadero.
- `B08`: permite analizar vegetacion porque la vegetacion sana refleja mucho en el infrarrojo cercano.
- `B04` y `B08`: permiten calcular NDVI.

## 6. Productos generados

El programa genera tres archivos GeoTIFF, un resumen de texto y un panel visual:

```text
p1_resultado_ndvi.tif
p1_color_verdadero.tif
p1_falso_color.tif
p1_resumen_resultados.txt
p1_panel_visual.png
```

### 6.1 p1_resultado_ndvi.tif

Archivo monobanda con el indice NDVI.

Sirve para analizar vegetacion y diferenciar zonas con mayor o menor actividad vegetal.

### 6.2 p1_color_verdadero.tif

Imagen RGB parecida a lo que veria el ojo humano.

Combinacion:

```text
Rojo = B04
Verde = B03
Azul = B02
```

### 6.3 p1_falso_color.tif

Imagen RGB usando infrarrojo cercano.

Combinacion:

```text
Rojo = B08
Verde = B04
Azul = B03
```

En falso color, la vegetacion suele aparecer destacada en tonos rojizos porque refleja mucho en el infrarrojo cercano.

### 6.4 p1_resumen_resultados.txt

Archivo de texto con el resumen numerico del NDVI.

Incluye:

- parametros usados,
- bounding box,
- rango de fechas,
- tamano de salida,
- valores estadisticos del color verdadero por canal,
- valores estadisticos del falso color por canal,
- minimo, maximo, media y mediana del NDVI,
- percentiles,
- distribucion por rangos,
- advertencias si las bandas estan vacias,
- interpretacion global.

Este archivo permite interpretar el resultado sin abrir QGIS.

En clase es util porque permite explicar los resultados por partes:

- primero la imagen visible o color verdadero,
- despues la imagen de falso color,
- finalmente el NDVI y su interpretacion.

### 6.5 p1_panel_visual.png

Imagen PNG generada con `matplotlib`.

Contiene cuatro paneles:

- color verdadero,
- falso color,
- mapa NDVI con rampa rojo-amarillo-verde,
- histograma de distribucion del NDVI.

Este archivo es util para una exposicion en clase porque permite ver en una sola imagen:

- como se ve la zona en bandas visibles,
- como cambia al usar infrarrojo cercano,
- donde aparecen valores altos o bajos de NDVI,
- como se distribuyen numericamente los valores del indice.

## 7. Que es el NDVI

NDVI significa `Normalized Difference Vegetation Index`.

Es un indice utilizado para estimar la presencia, densidad o vigor de la vegetacion.

Formula:

```text
NDVI = (NIR - Rojo) / (NIR + Rojo)
```

En este ejercicio:

```text
NIR = B08
Rojo = B04
```

Por tanto:

```text
NDVI = (B08 - B04) / (B08 + B04)
```

Interpretacion aproximada:

- Menor que 0: agua, sombras, nubes o superficies sin vegetacion.
- 0 a 0.2: suelo desnudo, urbano o vegetacion muy escasa.
- 0.2 a 0.4: vegetacion moderada o posiblemente estresada.
- Mayor que 0.4: vegetacion densa o sana.

## 8. Requisitos previos

Necesitas:

- Python 3.10 o superior.
- Conexion a internet.
- Cuenta en Copernicus Data Space Ecosystem.
- Credenciales OAuth de Copernicus: `Client ID` y `Client Secret`.
- QGIS para visualizar los resultados.

## 9. Crear el entorno virtual

Desde la carpeta del proyecto:

```bash
python -m venv venv
```

Activar en Linux o macOS:

```bash
source venv/bin/activate
```

Activar en Windows con CMD:

```cmd
venv\Scripts\activate
```

Activar en Windows con PowerShell:

```powershell
.\venv\Scripts\activate
```

El entorno virtual aisla las librerias de este proyecto para no mezclarlas con las del sistema.

## 10. Instalar dependencias

Con el entorno virtual activo:

```bash
pip install -r requirements.txt
```

Contenido de `requirements.txt`:

```text
numpy
rasterio
sentinelhub
python-dotenv
matplotlib
```

Funcion de cada libreria:

- `numpy`: trabaja con matrices y calcula el NDVI.
- `rasterio`: escribe archivos GeoTIFF con informacion geoespacial.
- `sentinelhub`: conecta con Copernicus/Sentinel Hub y descarga los datos.
- `python-dotenv`: carga las credenciales desde `.env`.
- `matplotlib`: genera el panel visual `p1_panel_visual.png`.

## 11. Obtener credenciales de Copernicus

1. Entra en:
   <https://shapps.dataspace.copernicus.eu/dashboard/>
2. Inicia sesion.
3. Abre `User Settings`.
4. Entra en `OAuth Clients`.
5. Pulsa `Create`.
6. Copia el `Client ID`.
7. Copia el `Client Secret`.

Estas credenciales permiten que el programa solicite un token OAuth y descargue datos de Copernicus.

## 12. Configurar el archivo .env

El archivo `.env` debe estar en la raiz del proyecto.

Formato:

```env
SH_CLIENT_ID=tu_client_id_real
SH_CLIENT_SECRET=tu_client_secret_real
```

Reglas:

- No cambiar los nombres `SH_CLIENT_ID` y `SH_CLIENT_SECRET`.
- No dejar espacios antes o despues del signo `=`.
- No compartir este archivo.
- No subirlo a Git.

El proyecto incluye `.gitignore` para evitar que `.env` se suba por accidente.

## 13. Ejecutar la aplicacion

Con el entorno virtual activo:

```bash
python ejercicio_p1.py
```

El programa pedira:

- oeste / longitud minima,
- sur / latitud minima,
- este / longitud maxima,
- norte / latitud maxima,
- fecha de inicio,
- fecha de fin,
- ancho en pixeles,
- alto en pixeles.

Si pulsas `Enter`, usa el valor por defecto mostrado entre corchetes.

Ejemplo:

```text
Introduce las coordenadas del area en grados decimales (WGS84).
Orden esperado: oeste, sur, este, norte.
Oeste / longitud minima [-4.56]: -4.60
Sur / latitud minima [37.02]: 37.00
Este / longitud maxima [-4.54]: -4.50
Norte / latitud maxima [37.04]: 37.08
Fecha inicio YYYY-MM-DD [2026-05-01]: 2026-05-01
Fecha fin YYYY-MM-DD [2026-06-01]: 2026-06-01
Ancho de salida en pixeles [512]: 512
Alto de salida en pixeles [512]: 512
```

## 14. Coordenadas: bounding box

El area de estudio se define como un rectangulo geografico llamado `bounding box`.

El orden usado es:

```text
[oeste, sur, este, norte]
```

Significado:

- `oeste`: longitud minima.
- `sur`: latitud minima.
- `este`: longitud maxima.
- `norte`: latitud maxima.

Reglas:

- `oeste` debe ser menor que `este`.
- `sur` debe ser menor que `norte`.
- las longitudes van de -180 a 180,
- las latitudes van de -90 a 90.

Ejemplo:

```text
Oeste = -4.56
Sur = 37.02
Este = -4.54
Norte = 37.04
```

Conviene empezar con areas pequenas. Si el area es muy grande o la salida tiene muchos pixeles, la descarga sera mas lenta y puede consumir mas recursos.

## 15. Fechas de consulta

Las fechas se introducen en formato:

```text
YYYY-MM-DD
```

Ejemplo:

```text
2026-05-01
2026-06-01
```

La API busca imagenes Sentinel-2 L2A dentro de ese intervalo. Si no hay resultados adecuados, se puede ampliar el rango de fechas o elegir otro periodo con menos nubosidad.

La fecha de inicio debe ser anterior a la fecha de fin. No conviene usar el mismo dia como inicio y fin, porque puede no existir una escena util para esa fecha exacta y el resultado puede salir vacio o con valores cero.

El script solicita escenas con un maximo aproximado de nubosidad del 30% y usa el criterio de menor nubosidad disponible dentro del intervalo.

## 16. Tamano de salida

El programa pide ancho y alto en pixeles.

Valor recomendado para pruebas:

```text
512 x 512
```

Un tamano mayor da mas detalle, pero tambien aumenta:

- tiempo de descarga,
- memoria usada,
- tamano de los archivos,
- consumo de cuota.

## 17. Explicacion del codigo

El script se organiza en funciones con prefijo `ft_`.

### 17.1 ft_inicializar_api()

Esta funcion:

1. Carga `.env`.
2. Lee `SH_CLIENT_ID`.
3. Lee `SH_CLIENT_SECRET`.
4. Crea una configuracion `SHConfig`.
5. Define los endpoints de Copernicus Data Space Ecosystem.

Endpoint principal:

```text
https://sh.dataspace.copernicus.eu
```

Endpoint de autenticacion:

```text
https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
```

### 17.2 ft_pedir_parametros_usuario()

Pide al usuario:

- coordenadas,
- fechas,
- tamano de salida.

Tambien valida que las coordenadas sean coherentes.

### 17.3 ft_ejecutar_practica_p1()

Es la funcion principal de procesamiento.

Hace cuatro tareas:

1. Crea la peticion a Sentinel Hub.
2. Descarga las bandas.
3. Calcula NDVI.
4. Exporta los GeoTIFF.

### 17.4 Evalscript

El `evalscript` indica a la API que bandas queremos:

```javascript
//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "B08"],
    output: { bands: 4, sampleType: "FLOAT32" }
  };
}

function evaluatePixel(samples) {
  return [samples.B02, samples.B03, samples.B04, samples.B08];
}
```

La salida tiene cuatro canales en este orden:

```text
B02, B03, B04, B08
```

### 17.5 Separacion de bandas

La matriz descargada tiene esta forma:

```text
alto x ancho x canales
```

El codigo separa cada banda:

```python
banda_azul = matriz_p1[:, :, 0]
banda_verde = matriz_p1[:, :, 1]
banda_rojo = matriz_p1[:, :, 2]
banda_nir = matriz_p1[:, :, 3]
```

### 17.6 Calculo del NDVI

El calculo se realiza con `numpy`:

```python
denominador_ndvi = banda_nir + banda_rojo
matriz_ndvi = np.divide(
    banda_nir - banda_rojo,
    denominador_ndvi,
    out=np.zeros_like(banda_nir, dtype="float32"),
    where=denominador_ndvi != 0,
)
```

Se usa `np.divide()` con `where` para evitar divisiones por cero.

### 17.7 Exportacion GeoTIFF

Los resultados se guardan con `rasterio`.

Metadatos principales:

- `driver`: `GTiff`.
- `dtype`: `float32`.
- `crs`: `EPSG:4326`.
- `transform`: calculado a partir del bounding box.
- `count`: numero de bandas.

El `transform` es importante porque permite que QGIS coloque el raster en su posicion geografica real.

## 18. Visualizar resultados en QGIS

Para abrir QGIS en este equipo se puede usar:

```bash
qgis-limpio
```

o desde la carpeta del proyecto:

```bash
./abrir_qgis_limpio.sh
```

Estos lanzadores evitan que QGIS herede el entorno virtual de Python del proyecto.

### 18.1 Cargar archivos

1. Abre QGIS.
2. Arrastra al mapa:

```text
p1_resultado_ndvi.tif
p1_color_verdadero.tif
p1_falso_color.tif
```

3. Comprueba que las capas se colocan correctamente.

### 18.2 Simbologia del NDVI

El archivo `p1_resultado_ndvi.tif` es monobanda, por eso necesita pseudocolor.

Pasos:

1. Clic derecho sobre `p1_resultado_ndvi`.
2. `Propiedades`.
3. `Simbologia`.
4. Tipo de renderizado: `Pseudocolor monobanda`.
5. Banda: `Banda 1`.
6. Minimo: `-1`.
7. Maximo: `1`.
8. Rampa: rojo-amarillo-verde, por ejemplo `RdYlGn`.
9. Pulsa `Clasificar`.
10. Pulsa `Aplicar`.

Interpretacion visual:

- Verde: vegetacion sana o densa.
- Amarillo: valores intermedios.
- Rojo/naranja: suelo desnudo, zonas urbanas o vegetacion escasa.
- Valores negativos: agua, sombras o nubes.

## 19. Comprobaciones realizadas

Se comprobo que:

- el script compila correctamente,
- el archivo `.env` carga credenciales,
- la API de Copernicus responde,
- se descargan datos Sentinel-2 L2A,
- se generan los tres GeoTIFF,
- se genera `p1_resumen_resultados.txt`,
- `p1_resultado_ndvi.tif` tiene una banda,
- `p1_color_verdadero.tif` tiene tres bandas,
- `p1_falso_color.tif` tiene tres bandas,
- los archivos tienen CRS `EPSG:4326`,
- QGIS queda instalado y puede abrir los GeoTIFF.

## 20. Errores frecuentes

### 20.1 Credenciales no encontradas

Mensaje:

```text
No se encontraron SH_CLIENT_ID o SH_CLIENT_SECRET en el archivo .env
```

Solucion:

- revisa que existe `.env`,
- revisa que las variables tienen el nombre correcto,
- revisa que las claves no estan vacias.

### 20.2 Error de conexion

Mensaje:

```text
Failed to download from...
Please check your internet connection and try again.
```

Solucion:

- revisa internet,
- revisa que Copernicus este disponible,
- vuelve a intentar mas tarde.

### 20.3 Resultado con todas las bandas a cero

Mensaje:

```text
Todas las bandas descargadas tienen valor maximo 0.
```

Puede ocurrir si:

- el rango de fechas es demasiado estrecho,
- se ha usado el mismo dia como inicio y fin,
- no hay una escena util para esa zona,
- la zona tiene demasiadas nubes,
- el bounding box no cubre correctamente el area esperada.

Solucion:

- usa un intervalo de varios dias o semanas,
- prueba `2026-05-01` a `2026-06-01`,
- reduce o cambia el bounding box,
- prueba otro mes.

### 20.4 Coordenadas invertidas

Mensaje:

```text
La coordenada oeste debe ser menor que la coordenada este.
```

Solucion:

- usa el orden correcto: oeste, sur, este, norte.

### 20.5 QGIS muestra error de SIP o Python

Puede ocurrir si QGIS se abre heredando el entorno virtual `venv`.

Solucion:

```bash
qgis-limpio
```

o:

```bash
./abrir_qgis_limpio.sh
```

## 21. Guion para explicar en clase

En esta practica se ha creado una aplicacion en Python para procesar imagenes Sentinel-2. Primero se prepara un entorno virtual y se instalan las librerias necesarias. Despues se configuran las credenciales de Copernicus en un archivo `.env`, que permite conectarse de forma segura a la API.

El usuario introduce una zona de estudio mediante cuatro coordenadas: oeste, sur, este y norte. Con esas coordenadas se crea un bounding box en el sistema WGS84. A continuacion, el programa solicita imagenes Sentinel-2 L2A, que son datos de reflectancia de superficie ya corregidos atmosfericamente. Se usa L2A porque es mas adecuado para calcular indices de vegetacion como NDVI que el nivel L1C.

La API devuelve cuatro bandas: azul, verde, rojo e infrarrojo cercano. Con rojo, verde y azul se genera una composicion de color verdadero. Con infrarrojo, rojo y verde se genera una composicion de falso color. Finalmente, con el infrarrojo cercano y el rojo se calcula el NDVI mediante la formula `(B08 - B04) / (B08 + B04)`.

Los resultados se exportan como GeoTIFF usando `rasterio`, conservando sistema de coordenadas y transformacion espacial. Esto permite abrirlos directamente en QGIS, donde el NDVI se interpreta mejor aplicando una simbologia de pseudocolor con valores entre -1 y 1.

## 22. Comandos principales

Crear entorno:

```bash
python -m venv venv
```

Activar entorno:

```bash
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar practica:

```bash
python ejercicio_p1.py
```

Abrir QGIS limpio:

```bash
qgis-limpio
```

Comprobar sintaxis:

```bash
python -m py_compile ejercicio_p1.py
```
