# REPORTE — Requerimiento de Bodegas

**Fecha**: 2026-01-08 16:06
**Dataset**: C:\Users\Lenovo\dataqbs_IA\projects\real_estate\easybrokers\properties\data

## bodega_chica
**Requerimiento**: Bodega chica 200-300 m², renta 15k-25k MXN, altura >=5m, zonas Periférico Sur/Miramar/Santa Ana Tepetitlán/Las Pintas.
**Propiedades analizadas**: 260
**Coincidencias exactas**: 0

### Coincidencias exactas
No se encontraron coincidencias exactas con este dataset.

### Casi coincidencias (para revisión)
- **EB-RT0376** — Bodega en Renta zona La Tijera (fallas: 1)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-zona-la-tijera
  - Datos: Renta: $19,500 MXN | Superficie: 210.0 m² | Altura: 6.0 m | Portón: 4.5 m
  - Sí cumple: Zona, Renta, Superficie, Altura
  - No cumple: Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-SD7086** — Amplia bodega nueva en renta zona La Tijera (fallas: 2)
  - Link: https://www.easybroker.com/mx/listings/amplia-bodega-nueva-en-renta-zona-la-tijera
  - Datos: Renta: $33,000 MXN | Superficie: 300.0 m² | Altura: 7.0 m
  - Sí cumple: Zona, Superficie, Altura
  - No cumple: Renta: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-RB5524** — Bodega en Renta en La Tijera casi esquina Camino Real a Colima (fallas: 3)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-en-la-tijera-caso-esquina-camino-real-a-colima
  - Datos: Renta: $48,000 MXN | Superficie: 510.0 m² | Altura: 8.0 m | Portón: 4.0 m
  - Sí cumple: Zona, Altura
  - No cumple: Renta: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-RC2517** — Bodega en renta en La Tijera (fallas: 3)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-en-la-tijera
  - Datos: Renta: $30,000 MXN | Superficie: 170.0 m² | Altura: 7.0 m | Portón: 4.0 m
  - Sí cumple: Zona, Altura
  - No cumple: Renta: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-OX3030** — AMPLIA BODEGA FRENTE A CARRETERA IXTLAHUACAN DEL RIO (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/amplia-bodega-frente-a-carretera-ixtlahuacan-del-rio
  - Datos: Renta: $33,000 MXN | Superficie: 500.0 m² | Altura: 18.0 m
  - Sí cumple: Altura
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-HW0701** — BODEGAS EN RENTA HUENTITAN CERCA ZOOLOGICO (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/bodegas-en-renta-huentitan-cerca-zoologico
  - Datos: Renta: $30,000 MXN | Superficie: 330.0 m²
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-UA2061** — BODEGA EN VENTA EN COLONIA LAS GLORIAS DEL COLLI ZONA AV GUADALUPE Y PERIFERICO (fallas: 6)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-venta-en-colonia-las-glorias-del-colli-zona-av-guadalupe-y-periferico
  - Datos: Compra: $5,500,000 MXN | Superficie: 360.0 m²
  - No cumple: Zona: fuera de las zonas aceptadas; Operación: no coincide (renta/venta); Renta: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente

## bodega_grande
**Requerimiento**: Bodega grande >=500 m², renta 30k-45k MXN con opción a compra, compra 4-8 M MXN, 220V, mismas zonas.
**Propiedades analizadas**: 260
**Coincidencias exactas**: 0

### Coincidencias exactas
No se encontraron coincidencias exactas con este dataset.

### Casi coincidencias (para revisión)
- **EB-RC2517** — Bodega en renta en La Tijera (fallas: 3)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-en-la-tijera
  - Datos: Renta: $30,000 MXN | Superficie: 170.0 m² | Altura: 7.0 m | Portón: 4.0 m
  - Sí cumple: Zona, Renta, Altura, 220V
  - No cumple: Compra: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-SD7086** — Amplia bodega nueva en renta zona La Tijera (fallas: 3)
  - Link: https://www.easybroker.com/mx/listings/amplia-bodega-nueva-en-renta-zona-la-tijera
  - Datos: Renta: $33,000 MXN | Superficie: 300.0 m² | Altura: 7.0 m
  - Sí cumple: Zona, Renta, Altura, 220V
  - No cumple: Compra: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-OX3030** — AMPLIA BODEGA FRENTE A CARRETERA IXTLAHUACAN DEL RIO (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/amplia-bodega-frente-a-carretera-ixtlahuacan-del-rio
  - Datos: Renta: $33,000 MXN | Superficie: 500.0 m² | Altura: 18.0 m
  - Sí cumple: Renta, Superficie, Altura
  - No cumple: Zona: fuera de las zonas aceptadas; Compra: fuera de rango o no indicada; Electricidad: no se encontró 220V (obligatorio); Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-RB5524** — Bodega en Renta en La Tijera casi esquina Camino Real a Colima (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-en-la-tijera-caso-esquina-camino-real-a-colima
  - Datos: Renta: $48,000 MXN | Superficie: 510.0 m² | Altura: 8.0 m | Portón: 4.0 m
  - Sí cumple: Zona, Superficie, Altura
  - No cumple: Renta: fuera de rango o no indicada; Compra: fuera de rango o no indicada; Electricidad: no se encontró 220V (obligatorio); Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-HW0701** — BODEGAS EN RENTA HUENTITAN CERCA ZOOLOGICO (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/bodegas-en-renta-huentitan-cerca-zoologico
  - Datos: Renta: $30,000 MXN | Superficie: 330.0 m²
  - Sí cumple: Renta, Altura
  - No cumple: Zona: fuera de las zonas aceptadas; Compra: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Electricidad: no se encontró 220V (obligatorio); Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-RT0376** — Bodega en Renta zona La Tijera (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-zona-la-tijera
  - Datos: Renta: $19,500 MXN | Superficie: 210.0 m² | Altura: 6.0 m | Portón: 4.5 m
  - Sí cumple: Zona, Altura
  - No cumple: Renta: fuera de rango o no indicada; Compra: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Electricidad: no se encontró 220V (obligatorio); Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-UA2061** — BODEGA EN VENTA EN COLONIA LAS GLORIAS DEL COLLI ZONA AV GUADALUPE Y PERIFERICO (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-venta-en-colonia-las-glorias-del-colli-zona-av-guadalupe-y-periferico
  - Datos: Compra: $5,500,000 MXN | Superficie: 360.0 m²
  - Sí cumple: Compra, Altura
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Superficie: fuera de rango o no indicada; Electricidad: no se encontró 220V (obligatorio); Esquema: no se encontró 'renta con opción a compra' (obligatorio)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente

## bodega_gym_12x16
**Requerimiento**: Bodega 12x16 (≈192 m²), renta 30k MXN, altura 8m, zonas anteriores + Mariano Otero y cerca de Centro Sur.
**Propiedades analizadas**: 260
**Coincidencias exactas**: 0

### Coincidencias exactas
No se encontraron coincidencias exactas con este dataset.

### Casi coincidencias (para revisión)
- **EB-RB5524** — Bodega en Renta en La Tijera casi esquina Camino Real a Colima (fallas: 3)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-en-la-tijera-caso-esquina-camino-real-a-colima
  - Datos: Renta: $48,000 MXN | Superficie: 510.0 m² | Altura: 8.0 m | Portón: 4.0 m
  - Sí cumple: Zona, Superficie, Altura
  - No cumple: Renta: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-RC2517** — Bodega en renta en La Tijera (fallas: 3)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-en-la-tijera
  - Datos: Renta: $30,000 MXN | Superficie: 170.0 m² | Altura: 7.0 m | Portón: 4.0 m
  - Sí cumple: Zona, Renta, Superficie
  - No cumple: Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-HW0701** — BODEGAS EN RENTA HUENTITAN CERCA ZOOLOGICO (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/bodegas-en-renta-huentitan-cerca-zoologico
  - Datos: Renta: $30,000 MXN | Superficie: 330.0 m²
  - Sí cumple: Renta, Superficie
  - No cumple: Zona: fuera de las zonas aceptadas; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-OX3030** — AMPLIA BODEGA FRENTE A CARRETERA IXTLAHUACAN DEL RIO (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/amplia-bodega-frente-a-carretera-ixtlahuacan-del-rio
  - Datos: Renta: $33,000 MXN | Superficie: 500.0 m² | Altura: 18.0 m
  - Sí cumple: Superficie, Altura
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-RT0376** — Bodega en Renta zona La Tijera (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/bodega-en-renta-zona-la-tijera
  - Datos: Renta: $19,500 MXN | Superficie: 210.0 m² | Altura: 6.0 m | Portón: 4.5 m
  - Sí cumple: Zona, Superficie
  - No cumple: Renta: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-SD7086** — Amplia bodega nueva en renta zona La Tijera (fallas: 4)
  - Link: https://www.easybroker.com/mx/listings/amplia-bodega-nueva-en-renta-zona-la-tijera
  - Datos: Renta: $33,000 MXN | Superficie: 300.0 m² | Altura: 7.0 m
  - Sí cumple: Zona, Superficie
  - No cumple: Renta: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-DI3255** — LOCAL EN VENTA / RENTA "PLAZA  PUNTO FARO" (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/local-en-venta-punta-faro
  - Datos: Renta: $15,500 MXN | Compra: $2,500,000 MXN
  - Sí cumple: Superficie
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-LB8465** — LOCAL COMERCIAL EN ATOTONILCO EL ALTO (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/local-comercial-en-atotonilco-el-alto
  - Datos: Renta: $17,500 MXN | Superficie: 84.0 m²
  - Sí cumple: Superficie
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-QB5271** — LOCAL COMERCIAL EN SANTA TERE (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/local-comercial-en-santa-tere-005c3806-332a-4181-a947-3411e17d6597
  - Datos: Renta: $16,500 MXN | Superficie: 100.0 m²
  - Sí cumple: Superficie
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente
- **EB-QB5286** — LOCAL COMERCIAL EN SANTA TERE (fallas: 5)
  - Link: https://www.easybroker.com/mx/listings/local-comercial-en-santa-tere-408ede88-6575-4c3c-bef0-048bf3da4d0e
  - Datos: Renta: $16,500 MXN | Superficie: 100.0 m²
  - Sí cumple: Superficie
  - No cumple: Zona: fuera de las zonas aceptadas; Renta: fuera de rango o no indicada; Altura: fuera de rango o no indicada; Portón: altura insuficiente o no indicada (obligatorio); Medidas: no coincide con 12x16 (o no indicada)
  - Revisar: Uso: no se menciona (maquila/alimentos/gym), revisar manualmente

