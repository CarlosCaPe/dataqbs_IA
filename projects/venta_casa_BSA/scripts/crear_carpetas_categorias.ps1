# Script para renombrar fotos según categoría
# Ejecutar en PowerShell desde la carpeta del proyecto

# Carpeta de origen
$origen = "c:\Users\Lenovo\dataqbs_IA\projects\venta_casa_BSA\fotos_originales"

# Crear carpetas de categorías
$categorias = @(
    "01_fachada",
    "02_cochera",
    "03_sala",
    "04_cocina",
    "05_comedor",
    "06_oficina",
    "07_recamara_principal",
    "08_recamara_2",
    "09_recamara_3",
    "10_banos",
    "11_area_lavado",
    "12_jardin",
    "13_pasillos",
    "14_paneles_solares",
    "15_detalles",
    "16_exteriores"
)

foreach ($cat in $categorias) {
    $ruta = Join-Path "c:\Users\Lenovo\dataqbs_IA\projects\venta_casa_BSA\fotos_categorizadas" $cat
    if (!(Test-Path $ruta)) {
        New-Item -ItemType Directory -Path $ruta -Force
    }
}

Write-Host "✅ Carpetas creadas en: c:\Users\Lenovo\dataqbs_IA\projects\venta_casa_BSA\fotos_categorizadas\"
Write-Host ""
Write-Host "📁 Categorías disponibles:"
foreach ($cat in $categorias) {
    Write-Host "   - $cat"
}
Write-Host ""
Write-Host "Ahora mueve manualmente cada foto a su carpeta correspondiente"
