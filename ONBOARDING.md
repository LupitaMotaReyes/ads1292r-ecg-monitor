# CWXS ADS1292R ECG Monitor — Cómo correr la app

Esta guía asume que el hardware (Arduino + módulo ADS1292R) ya está cableado y
con el firmware cargado. Aquí solo va la parte de instalar y usar la app en la
PC.

## 1. Instalar

```powershell
git clone https://github.com/LupitaMotaReyes/cwxs-ads1292r-ecg-monitor.git
cd cwxs-ads1292r-ecg-monitor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest        # deben pasar 11 tests
```

Requiere Python 3.12+.

## 2. Conectar el Arduino y ver qué puerto le tocó

Conecta el Arduino por USB a la PC. Para saber en qué puerto COM quedó:

```powershell
python tools\serial_inspector.py --list
```

Anota el puerto (por ejemplo `COM8`).

## 3. Correr la app

```powershell
.venv\Scripts\activate
python -m src.main
```

1. **Settings > Connection**: selecciona el puerto COM que viste en el paso 2,
   y baud rate `115200`.
2. **Connect**.
3. **Start**.
4. Deberías ver la traza ECG moviéndose y el corazón latiendo junto al BPM.

## Problemas comunes

- **No aparece ningún puerto / "Acceso denegado"**: cierra cualquier otra
  ventana que tenga el puerto abierto (Arduino IDE, otro monitor serie, etc.)
  y vuelve a intentar.
- **Connect funciona pero no grafica nada**: revisa que le diste **Start**
  después de **Connect** — Connect solo abre el puerto, Start empieza a leer
  datos.
- **BPM se queda en `-- BPM`**: aún no hay suficientes latidos detectados —
  revisa que los electrodos tengan buen contacto.
