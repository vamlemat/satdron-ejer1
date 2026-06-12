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
├── main.py
├── ejercicio_p1.py
├── ejercicio_p2.py
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
├── p1_panel_visual.png
├── p2_nbr_pre.tif
├── p2_nbr_post.tif
├── p2_dnbr.tif
├── p2_severidad_incendio.tif
├── p2_resumen_resultados.txt
└── p2_panel_visual.png
```

Descripcion de los archivos:

- `main.py`: menu principal para elegir entre P1 y P2.
- `ejercicio_p1.py`: practica 1, NDVI y composiciones Sentinel-2.
- `ejercicio_p2.py`: practica 2, deteccion de cambios post-incendio con descarga por API y dNBR.
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
- `p2_nbr_pre.tif`: NBR antes del incendio.
- `p2_nbr_post.tif`: NBR despues del incendio.
- `p2_dnbr.tif`: diferencia de NBR.
- `p2_severidad_incendio.tif`: clasificacion de severidad en 4 clases.
- `p2_resumen_resultados.txt`: informe numerico de P2.
- `p2_panel_visual.png`: panel visual de P2.

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

## 8. Ejercicio P2: deteccion de cambios post-incendio

El segundo ejercicio detecta cambios potenciales asociados a un incendio comparando una imagen Sentinel-2 anterior al incendio con otra posterior.

La idea es:

1. Introducir un area de estudio mediante bounding box.
2. Introducir un rango temporal pre-incendio.
3. Introducir un rango temporal post-incendio.
4. Descargar por API las bandas necesarias para NBR.
5. Calcular NBR en la imagen pre-incendio.
6. Calcular NBR en la imagen post-incendio.
7. Calcular dNBR como diferencia entre ambos.
8. Clasificar la severidad potencial del incendio en 4 clases.
9. Exportar GeoTIFF, resumen numerico y panel visual.

Este punto vuelve a usar la API porque el navegador de Copernicus puede no permitir descargar facilmente las imagenes necesarias. No se necesita una API distinta: se usan las mismas credenciales del archivo `.env`.

Las bandas descargadas para P2 son:

- `B08`: infrarrojo cercano o NIR,
- `B12`: SWIR2.

En P2 se usa `maxcc=1.0` para no descartar escenas historicas por el filtro de nubosidad. Con el caso de referencia de julio de 2018, un filtro mas estricto como `maxcc=0.3` puede devolver `dataMask=0`, es decir, imagenes vacias aunque el calculo sea correcto.

Caso de referencia usado como valores por defecto:

```text
Bounding box: oeste=16.52, sur=43.45, este=16.78, norte=43.58
Fecha del incendio en maximo apogeo: 2018-07-17
Rango PRE-incendio: 2018-07-05 a 2018-07-10
Rango POST-incendio: 2018-07-20 a 2018-07-25
```

Estos valores permiten comparar resultados con otros trabajos que usen la misma zona y fechas.

## 9. Que es el NBR

NBR significa `Normalized Burn Ratio`.

Se usa mucho para detectar areas quemadas porque combina:

- `B08`: infrarrojo cercano o NIR.
- `B12`: infrarrojo de onda corta o SWIR2.

Formula:

```text
NBR = (NIR - SWIR2) / (NIR + SWIR2)
```

En Sentinel-2:

```text
NIR = B08
SWIR2 = B12
```

Por tanto:

```text
NBR = (B08 - B12) / (B08 + B12)
```

La vegetacion sana suele tener NBR alto, porque refleja bastante en NIR y menos en SWIR2. Despues de un incendio, el NBR suele bajar porque la vegetacion pierde vigor y aumenta la respuesta en SWIR.

## 10. Que es el dNBR

dNBR significa `differenced Normalized Burn Ratio`.

Formula:

```text
dNBR = NBR_pre - NBR_post
```

Interpretacion:

- Si el NBR baja mucho despues del incendio, el dNBR sera alto.
- Valores altos de dNBR suelen indicar mayor severidad.
- Valores bajos indican poco cambio o ausencia de incendio.

## 11. Clasificacion de severidad en P2

El script clasifica el dNBR en 4 clases:

```text
Clase 1: dNBR < 0.10          Sin cambio o no quemado
Clase 2: 0.10 <= dNBR < 0.27  Severidad baja
Clase 3: 0.27 <= dNBR < 0.66  Severidad moderada
Clase 4: dNBR >= 0.66         Severidad alta
```

Estas clases son una simplificacion util para el ejercicio. En un trabajo real se podrian ajustar los umbrales segun zona, vegetacion, sensor, validacion de campo y bibliografia.

## 12. Productos generados por P2

El ejercicio 2 genera:

```text
p2_nbr_pre.tif
p2_nbr_post.tif
p2_dnbr.tif
p2_severidad_incendio.tif
p2_resumen_resultados.txt
p2_panel_visual.png
```

Descripcion:

- `p2_nbr_pre.tif`: NBR antes del incendio.
- `p2_nbr_post.tif`: NBR despues del incendio.
- `p2_dnbr.tif`: diferencia entre NBR pre y NBR post.
- `p2_severidad_incendio.tif`: mapa clasificado en 4 clases.
- `p2_resumen_resultados.txt`: estadisticas e interpretacion.
- `p2_panel_visual.png`: figura con NBR pre, NBR post, dNBR y severidad.

## 13. Requisitos previos

Necesitas:

- Python 3.10 o superior.
- Conexion a internet.
- Cuenta en Copernicus Data Space Ecosystem.
- Credenciales OAuth de Copernicus: `Client ID` y `Client Secret`.
- QGIS para visualizar los resultados.

## 14. Crear el entorno virtual

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

## 15. Instalar dependencias

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
- `matplotlib`: genera los paneles visuales `p1_panel_visual.png` y `p2_panel_visual.png`.

## 16. Obtener credenciales de Copernicus

1. Entra en:
   <https://shapps.dataspace.copernicus.eu/dashboard/>
2. Inicia sesion.
3. Abre `User Settings`.
4. Entra en `OAuth Clients`.
5. Pulsa `Create`.
6. Copia el `Client ID`.
7. Copia el `Client Secret`.

Estas credenciales permiten que el programa solicite un token OAuth y descargue datos de Copernicus.

## 17. Configurar el archivo .env

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

## 18. Ejecutar la aplicacion

Con el entorno virtual activo:

```bash
python main.py
```

El menu principal permite elegir:

```text
1. P1 - Sentinel-2 L2A, NDVI y composiciones RGB
2. P2 - Deteccion de cambios post-incendio con dNBR
0. Salir
```

Tambien se puede ejecutar cada practica por separado:

```bash
python ejercicio_p1.py
python ejercicio_p2.py
```

Para P1, el programa pedira:

- oeste / longitud minima,
- sur / latitud minima,
- este / longitud maxima,
- norte / latitud maxima,
- fecha de inicio,
- fecha de fin,
- ancho en pixeles,
- alto en pixeles.

Para P2, el programa pedira:

- oeste / longitud minima,
- sur / latitud minima,
- este / longitud maxima,
- norte / latitud maxima,
- rango temporal pre-incendio,
- rango temporal post-incendio,
- ancho en pixeles,
- alto en pixeles.

Los valores por defecto de P2 corresponden al caso de referencia:

```text
Bounding box: 16.52, 43.45, 16.78, 43.58
PRE: 2018-07-05 a 2018-07-10
POST: 2018-07-20 a 2018-07-25
```

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

## 19. Coordenadas: bounding box

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

## 20. Fechas de consulta

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

## 21. Tamano de salida

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

## 22. Explicacion del codigo

El script se organiza en funciones con prefijo `ft_`.

### 22.1 ft_inicializar_api()

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

### 22.2 ft_pedir_parametros_usuario()

Pide al usuario:

- coordenadas,
- fechas,
- tamano de salida.

Tambien valida que las coordenadas sean coherentes.

### 22.3 ft_ejecutar_practica_p1()

Es la funcion principal de procesamiento.

Hace cuatro tareas:

1. Crea la peticion a Sentinel Hub.
2. Descarga las bandas.
3. Calcula NDVI.
4. Exporta los GeoTIFF.

### 22.4 Evalscript

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

### 22.5 Separacion de bandas

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

### 22.6 Calculo del NDVI

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

### 22.7 Exportacion GeoTIFF

Los resultados se guardan con `rasterio`.

Metadatos principales:

- `driver`: `GTiff`.
- `dtype`: `float32`.
- `crs`: `EPSG:4326`.
- `transform`: calculado a partir del bounding box.
- `count`: numero de bandas.

El `transform` es importante porque permite que QGIS coloque el raster en su posicion geografica real.

## 23. Visualizar resultados en QGIS

Para abrir QGIS en este equipo se puede usar:

```bash
qgis-limpio
```

o desde la carpeta del proyecto:

```bash
./abrir_qgis_limpio.sh
```

Estos lanzadores evitan que QGIS herede el entorno virtual de Python del proyecto.

### 23.1 Cargar archivos

1. Abre QGIS.
2. Arrastra al mapa:

```text
p1_resultado_ndvi.tif
p1_color_verdadero.tif
p1_falso_color.tif
```

3. Comprueba que las capas se colocan correctamente.

### 23.2 Simbologia del NDVI

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

## 24. Comprobaciones realizadas

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

## 25. Errores frecuentes

### 25.1 Credenciales no encontradas

Mensaje:

```text
No se encontraron SH_CLIENT_ID o SH_CLIENT_SECRET en el archivo .env
```

Solucion:

- revisa que existe `.env`,
- revisa que las variables tienen el nombre correcto,
- revisa que las claves no estan vacias.

### 25.2 Error de conexion

Mensaje:

```text
Failed to download from...
Please check your internet connection and try again.
```

Solucion:

- revisa internet,
- revisa que Copernicus este disponible,
- vuelve a intentar mas tarde.

### 25.3 Resultado con todas las bandas a cero

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

### 25.4 Coordenadas invertidas

Mensaje:

```text
La coordenada oeste debe ser menor que la coordenada este.
```

Solucion:

- usa el orden correcto: oeste, sur, este, norte.

### 25.5 QGIS muestra error de SIP o Python

Puede ocurrir si QGIS se abre heredando el entorno virtual `venv`.

Solucion:

```bash
qgis-limpio
```

o:

```bash
./abrir_qgis_limpio.sh
```

## 26. Guion para explicar en clase

En esta practica se ha creado una aplicacion en Python para procesar imagenes Sentinel-2. Primero se prepara un entorno virtual y se instalan las librerias necesarias. Despues se configuran las credenciales de Copernicus en un archivo `.env`, que permite conectarse de forma segura a la API.

El usuario introduce una zona de estudio mediante cuatro coordenadas: oeste, sur, este y norte. Con esas coordenadas se crea un bounding box en el sistema WGS84. A continuacion, el programa solicita imagenes Sentinel-2 L2A, que son datos de reflectancia de superficie ya corregidos atmosfericamente. Se usa L2A porque es mas adecuado para calcular indices de vegetacion como NDVI que el nivel L1C.

La API devuelve cuatro bandas: azul, verde, rojo e infrarrojo cercano. Con rojo, verde y azul se genera una composicion de color verdadero. Con infrarrojo, rojo y verde se genera una composicion de falso color. Finalmente, con el infrarrojo cercano y el rojo se calcula el NDVI mediante la formula `(B08 - B04) / (B08 + B04)`.

Los resultados se exportan como GeoTIFF usando `rasterio`, conservando sistema de coordenadas y transformacion espacial. Esto permite abrirlos directamente en QGIS, donde el NDVI se interpreta mejor aplicando una simbologia de pseudocolor con valores entre -1 y 1.

El segundo ejercicio descarga dos imagenes por API: una anterior y otra posterior al incendio. Para ello usa las bandas B08 y B12 de Sentinel-2 L2A, calcula NBR en ambas fechas y despues obtiene dNBR. El dNBR permite estimar la severidad potencial del incendio: cuanto mas alto es el valor, mayor perdida relativa de vegetacion se interpreta. Finalmente se clasifica el resultado en cuatro clases: sin cambio, severidad baja, severidad moderada y severidad alta.

## 27. Comandos principales

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

Ejecutar menu principal:

```bash
python main.py
```

Ejecutar P1 directamente:

```bash
python ejercicio_p1.py
```

Ejecutar P2 directamente:

```bash
python ejercicio_p2.py
```

Abrir QGIS limpio:

```bash
qgis-limpio
```

Comprobar sintaxis:

```bash
python -m py_compile main.py ejercicio_p1.py ejercicio_p2.py
```
