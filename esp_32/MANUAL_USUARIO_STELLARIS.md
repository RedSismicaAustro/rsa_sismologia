# Manual de Usuario — DEV_HW107 "STELLARIS UNO E3 MAX"

**Tarjeta:** `DEV_HW107_STELLARIS_UNO_E3_MAX`
**MCU:** ESP32-WROOM-32D (Espressif), 4 MB de flash integrada, antena PCB
**Estándar de diseño:** KiCad 10.0.0 · Perfil de fabricación `jlcpcb_smd_avanzado`
**Versión del manual:** 1.0 — basado en el esquemático y el PCB vigentes del proyecto

> Este manual se generó leyendo directamente los 9 archivos del proyecto (esquemático raíz + 8 hojas
> y el PCB). Todo dato de pin, red y componente citado aquí proviene de esos archivos, no de hojas de
> datos genéricas. Donde el diseño no permite una conclusión 100 % cierta se indica explícitamente
> con **⚠ Verificar**.

---

## Índice

1. [Qué es esta tarjeta](#1-qué-es-esta-tarjeta)
2. [Seguridad y advertencias](#2-seguridad-y-advertencias)
3. [Puesta en marcha y alimentación](#3-puesta-en-marcha-y-alimentación)
4. [Programación de la tarjeta (flasheo)](#4-programación-de-la-tarjeta-flasheo)
5. [Mapa maestro de GPIO](#5-mapa-maestro-de-gpio)
6. [Manejo de periféricos](#6-manejo-de-periféricos)
7. [Ejemplos de código listos para usar](#7-ejemplos-de-código-listos-para-usar)
8. [Diagnóstico y solución de problemas](#8-diagnóstico-y-solución-de-problemas)
9. [Estado del diseño y notas de fabricación](#9-estado-del-diseño-y-notas-de-fabricación)
10. [Anexo A — Inventario de bloques](#anexo-a--inventario-de-bloques)
11. [Anexo B — Archivos del proyecto](#anexo-b--archivos-del-proyecto)

---

## 1. Qué es esta tarjeta

Placa de adquisición y monitoreo con formato compatible Arduino UNO, basada en ESP32 (WiFi + BLE),
pensada como plataforma común para instrumentación RSA (adquisición, sismógrafos, dIFS, monitoreo).
Está organizada en ocho bloques funcionales, cada uno en su propia hoja de esquemático:

| # | Hoja | Función |
|---|------|---------|
| 1 | `FUENTE.kicad_sch` | Entrada DC + USB, reguladores lineales 5 V y 3.3 V, protección de polaridad inversa |
| 2 | `USB-UART.kicad_sch` | Conector USB-C 16 p, CH340K, auto-programación DTR/RTS, protección ESD |
| 3 | `DEV_HW107_...kicad_sch` (raíz) | Módulo ESP32-WROOM-32D y su circuitería de arranque |
| 4 | `BOTONES.kicad_sch` | Pulsadores BOOT (IO0) y RESET (EN) con sus redes de temporización |
| 5 | `LEDs.kicad_sch` | 12 indicadores LED azules con driver MOSFET por canal |
| 6 | `MICRO SD.kicad_sch` | Socket microSD (TF-015) sobre bus SPI |
| 7 | `SENSORES.kicad_sch` | AHT20 (temperatura/humedad) + LIS3DHTR (acelerómetro) sobre I²C |
| 8 | `SIID.kicad_sch` | Bloque de identificación / interfaz del sistema |
| 9 | `CONECTORES.kicad_sch` | Peinetas de expansión (4 × 1×8, 2 × 1×6, 2 × 1×10) |

**Recursos principales**

- ESP32-WROOM-32D con flash de 4 MB y antena integrada.
- USB-C con puente USB-Serial CH340K y **circuito de auto-descarga** (no hace falta pulsar botones para flashear).
- Alimentación triple: USB-C 5 V, jack DC y conector JST PH de 2 pines.
- I²C con dos sensores a bordo: AHT20 y LIS3DHTR.
- Lector microSD por SPI.
- 12 indicadores LED con driver, más los LED de actividad TX/RX del puerto serie.
- 8 peinetas de expansión con todas las señales de bus, alimentación y GPIO libres.

---

## 2. Seguridad y advertencias

- **Tensión de operación:** todas las señales son **3.3 V**. No aplicar 5 V a ningún GPIO, peineta o línea de bus.
- **Entrada DC:** respetar polaridad del jack. La placa tiene protección con MOSFET P (`AO3401A`), pero no
  protegerla indefinidamente contra sobretensión: la cadena es `VIN → AMS1117-5.0 → VDD5V → AMS1117-3.3 → VDD33`.
  Mantener la entrada entre **7 V y 12 V** para que el AMS1117-5.0 tenga margen de dropout.
- **USB-C:** el conector entrega VBUS a través de `F1` (polyfuse `MF-PSMF050X-2`) y `D1` (Schottky `B5819W`),
  con protección ESD `U1` (`SRV05-4`). No alimentar por USB y por DC con tensiones que puedan pelearse.
- **Antena:** no colocar plano de masa, baterías metálicas ni piezas de blindaje sobre la zona marcada
  `ANTENA` en el silkscreen. El footprint del módulo incluye un *keepout* de cobre en ambas caras.
- **GPIO de strapping:** `IO0`, `IO2`, `IO12`, `IO15` definen el modo de arranque. Si se conectan cargas
  externas en esos pines, verificar su nivel durante el reset (§5).
- **Backfeed por USB:** si la placa se alimenta por DC, no inyectar 5 V por el conector USB-C desde una
  fuente externa. El diodo `D1` evita el retorno, pero no es una protección de potencia.

---

## 3. Puesta en marcha y alimentación

### 3.1 Entradas de alimentación

| Entrada | Componente | Tensión | Notas |
|---|---|---|---|
| USB-C (16 p) | `J1` `TYPE-C16PIN` | 5 V | VBUS → `F1` → `D1` → rail de 5 V. Requiere el puente soldable marcado **`Close`** de la hoja `FUENTE` cerrado para alimentar toda la placa desde USB |
| Jack DC | `DC-005-5A-2.0-SMT` | 7–12 V | Entrada principal. Pasa por `AO3401A` (protección de polaridad) |
| JST PH 2 pines | `PH-2PWB` | — | Entrada alternativa de la misma rail de entrada |

### 3.2 Rieles

| Rail | Origen | Uso |
|---|---|---|
| `VIN` | Entrada DC / JST | Entrada de los reguladores |
| `VDD5V` | `AMS1117-5.0` (y VBUS por el puente `Close`) | Peinetas `VDD5V`, divisores, periféricos de 5 V |
| `VDD33` | `AMS1117-3.3` desde `VDD5V` | **ESP32, CH340K, sensores, microSD, LEDs** |

Capacidad de desacoplo: `CL31A226KAHNNNE` (22 µF) a la entrada/salida de cada regulador, más un
electrolítico `RST47UF25V035` (47 µF) en la entrada, y 100 nF locales en cada circuito integrado.

### 3.3 Secuencia de encendido

1. Conectar alimentación (USB-C o DC/JST). Debe encender el LED indicador de alimentación del bloque `FUENTE`.
2. Verificar **3.3 V** en cualquier pin `VDD33` de las peinetas.
3. Si no hay 3.3 V: revisar el puente `Close` de la hoja `FUENTE`, el polyfuse `F1` y la entrada DC.

El micro consume del orden de 100–250 mA en transmisión WiFi; el AMS1117-3.3 con 22 µF es suficiente,
pero para uso intensivo de WiFi con tarjeta SD conviene alimentar por DC.

---

## 4. Programación de la tarjeta (flasheo)

### 4.1 ¿Qué es `esptool`?

`esptool` es la **herramienta oficial de Espressif** para hablar con el bootloader de la ROM del ESP32 a
través del puerto serie. No es un programa de la placa ni un driver: es el "cargador" que:

- resetea el chip y lo pone en **modo descarga** usando las líneas DTR/RTS del conversor USB-serie,
- borra, lee y escribe la flash en cualquier dirección,
- verifica la escritura y reinicia la aplicación al terminar.

Todo el flujo de carga de Arduino IDE, PlatformIO y ESP-IDF lo usa por debajo. Viene como paquete de
Python (`pip install esptool`) y en Windows suele instalarse en
`C:\Users\<usuario>\AppData\Local\Arduino15\packages\esp32\tools\esptool_py\`.

### 4.2 Camino 1 — Arduino IDE (recomendado para empezar)

1. Instalar el *core* `esp32` de Espressif en el Gestor de Tarjetas.
2. Instalar el driver CH340 (`CH341SER`) si el puerto no aparece.
3. Conectar el cable USB-C al `J1`. Debe crearse un puerto **COMx**.
4. Configuración de placa:

   | Opción | Valor |
   |---|---|
   | Board | **ESP32 Dev Module** |
   | Upload Speed | **921600** (bajar a 460800 o 115200 si hay errores) |
   | Flash Size | **4MB (32Mb)** |
   | Flash Frequency | 80 MHz |
   | Partition Scheme | Default 4MB with spiffs |
   | PSRAM | Disabled |
   | Port | COMx del CH340 |

5. Pulsar *Upload*. La tarjeta entra sola al bootloader por el circuito de auto-descarga.

### 4.3 Camino 2 — PlatformIO

```ini
; platformio.ini
[env:stellaris]
platform  = espressif32
board     = esp32dev
framework = arduino
upload_speed = 921600
monitor_speed = 115200
```

```bash
pio run -t upload
pio device monitor
```

### 4.4 Camino 3 — `esptool` directo

```bash
# Identificar el chip y la flash
esptool --chip esp32 --port COM3 flash_id

# Grabar un firmware completo desde 0x0
esptool --chip esp32 --port COM3 --baud 921600 write_flash 0x0 firmware.bin

# Borrar todo (útil tras corrupción de NVS o de tabla de particiones)
esptool --chip esp32 --port COM3 erase_flash

# Respaldar la flash completa (4 MB) antes de experimentar
esptool --chip esp32 --port COM3 read_flash 0x0 0x400000 respaldo.bin
```

### 4.5 Entrada manual al modo descarga

Si el auto-reset no funciona (por ejemplo, después de cargar un firmware que bloquea el arranque):

1. Mantener pulsado **BOOT** (`S1`, línea `IO0`).
2. Pulsar y soltar **RESET** (`S2`, línea `EN`).
3. Soltar **BOOT**.
4. Flashear. Al terminar, pulsar **RESET** para salir del bootloader.

### 4.6 Cómo funciona el circuito de auto-descarga (para diagnóstico)

La hoja `USB-UART` implementa el clásico arreglo de dos transistores `SS8050` (`Q1`, `Q2`) que traduce
DTR/RTS del CH340K en EN/IO0 del ESP32:

```
 DTR RTS -> EN IO0
  1   1     1   1
  0   0     1   1
  1   0     0   1
  0   1     1   0
```

- DTR bajo y RTS bajando → reset en **modo RUN**.
- RTS alto y DTR subiendo → reset en **modo BOOTLOADER**.

Los LED `D3` (TXD) y `D2` (RXD) parpadean durante la carga: son el mejor indicador de que el enlace vive.

### 4.7 Consola serie

- Puerto serie de la consola: **UART0** (`GPIO1` = `TXD0`, `GPIO3` = `RXD0`), a **115200 baudios**.
- El CH340K está alimentado desde `VDD33`, por lo que su Tx/Rx son de **3.3 V** (3.3 V y 5 V tolerantes según hoja de datos, pero no exponer a 5 V en la práctica).

---

## 5. Mapa maestro de GPIO

Tabla derivada directamente de los pads del footprint `RSA_ICs:ESP32-WROOM-32D` en el PCB (números de
pin = pinout del módulo) y de las redes del esquemático.

| Pin | GPIO | Red en la placa | Uso / restricción |
|---|---|---|---|
| 1 | — | `GND` | Masa |
| 2 | — | `VDD33` | Alimentación 3.3 V |
| 3 | `EN` | `EN` | Reset del chip · botón `S2` · pull-up 10 kΩ + 1 nF |
| 4 | 36 | `SENSOR_VP` | **Solo entrada** (ADC1_CH0) · peineta |
| 5 | 39 | `SENSOR_VN` | **Solo entrada** (ADC1_CH3) · peineta |
| 6 | 34 | `IO34` | **Solo entrada** (ADC1_CH6) · peineta |
| 7 | 35 | `IO35` | **Solo entrada** (ADC1_CH7) · peineta |
| 8 | 32 | `IO32` | GPIO / ADC1_CH4 / táctil · peineta |
| 9 | 33 | `IO33` | GPIO / ADC1_CH5 / táctil · peineta |
| 10 | 25 | `IO25` | GPIO / DAC1 · LED + peineta 1×8 |
| 11 | 26 | `IO26` | GPIO / DAC2 · LED + peineta 1×10 + interrupción del LIS3DH por `J6` |
| 12 | 27 | `IO27` | GPIO · LED + peineta 1×10 + interrupción del LIS3DH por `J7` |
| 13 | 14 | `IO14` | GPIO / HSPI_CLK · LED + peineta 1×8 |
| 14 | 12 | `IO12` | **Strapping (MTDI)** · hoja `MICRO SD` (`R39` 1 kΩ + `JP8`) · debe estar **bajo** al arrancar |
| 15 | — | `GND` | Masa |
| 16 | 13 | `IO13` | GPIO / táctil · LED + peineta 1×8 |
| 17–22 | 9, 10, 11, 6, 7, 8 | *(sin red)* | **Ocupados por la flash SPI interna** · no usar |
| 23 | 15 | `IO15_TOUCH` | **Strapping (MTDO)** · pads 10 y 12 del socket microSD (detector/shell) · debe estar **alto** al arrancar |
| 24 | 2 | `IO2` | **Strapping** · peineta |
| 25 | 0 | `IO0` | **BOOT** · botón `S1` · colector de `Q2` (auto-descarga) · pull-up 12 kΩ |
| 26 | 4 | `IO4` | GPIO / ADC2_CH0 · peineta |
| 27 | 16 | `IO16` | GPIO / U2RXD · LED + peineta 1×8 |
| 28 | 17 | `IO17` | GPIO / U2TXD · LED + peineta 1×8 |
| 29 | 5 | `IO5` | **CS del microSD** · LED + peineta 1×10 · strapping (debe estar alto al arrancar) |
| 30 | 18 | `IO18` | **CLK del microSD** · LED + peineta 1×10 |
| 31 | 19 | `IO19` | **MISO del microSD (DAT0)** · LED + peineta 1×10 |
| 32 | — | *(NC)* | Sin conexión |
| 33 | 21 | `SDA_0` | **I²C SDA** · AHT20 + LIS3DHTR · peinetas |
| 34 | 3 | `RXD0` | **UART0 RX** ← CH340 TXD · LED `D2` |
| 35 | 1 | `TXD0` | **UART0 TX** → CH340 RXD · LED `D3` |
| 36 | 22 | `SCL_0` | **I²C SCL** · AHT20 + LIS3DHTR · peinetas |
| 37 | 23 | `IO23` | **MOSI del microSD (CMD)** · LED + peineta 1×10 |
| 38 | — | `GND` | Masa |
| 39 | — | `GND` | Pad térmico |

**Resumen de pines libres para el usuario:** 13, 14, 16, 17, 25, 32, 33 (más los de solo entrada 34, 35,
36, 39 y el 4). Los pines 18, 19, 23, 5 están tomados por el microSD; 21 y 22 por el I²C; 26 y 27 por las
interrupciones del acelerómetro; 0 y 2 por el arranque.

---

## 6. Manejo de periféricos

### 6.1 Pulsadores

| Pulsador | Red | Función | Notas |
|---|---|---|---|
| `S1` — **BOOT** | `IO0` | Forzar modo descarga | Pull-up `R40` 12 kΩ, antirrebote `C17` 1 nF y `R42` 4.7 kΩ. `IO0` debe estar **alto** para arrancar en modo RUN |
| `S2` — **RESET** | `EN` | Reset del ESP32 | Pull-up `R41` 10 kΩ, `C18` 1 nF. `EN` debe estar **alto** para habilitar el chip |

**Uso en firmware**

```cpp
const int PIN_BOOT = 0;               // activo en BAJO
void setup() {
  Serial.begin(115200);
  pinMode(PIN_BOOT, INPUT_PULLUP);    // la placa ya tiene 12 k, es redundante pero seguro
}
void loop() {
  if (digitalRead(PIN_BOOT) == LOW) {
    Serial.println("BOOT pulsado -> modo configuración");
    delay(300);
  }
}
```

> **Precaución:** si el firmware se cuelga y `IO0` queda en bajo, la placa arrancará siempre en modo
> bootloader. Para recuperarla, cargar firmware nuevo o usar BOOT+RESET manualmente.

### 6.2 UART0 / consola de depuración

- `TXD0` (GPIO1) → RXD del CH340K → `D3` (LED de actividad de transmisión).
- `RXD0` (GPIO3) ← TXD del CH340K → `D2` (LED de actividad de recepción).
- Alimentado y referenciado a 3.3 V. **Usar `Serial` a 115200** en `setup()`.

### 6.3 Bus I²C

| Señal | GPIO | Red |
|---|---|---|
| SDA | **21** | `SDA_0` |
| SCL | **22** | `SCL_0` |

- Pull-ups de **10 kΩ** a `VDD33` en la placa (`R44`/`R45`, hoja `SENSORES`).
- El bus está expuesto en las peinetas de 1×10 y en la familia de 1×8 que lo incluye.
- Dos dispositivos a bordo:

| Dispositivo | Ref | Dirección I²C | Notas |
|---|---|---|---|
| **AHT20** (temp. + humedad) | `U5B` | `0x38` (fija) | Desacoplo 100 nF + 10 µF |
| **LIS3DHTR** (acelerómetro 3 ejes) | `U4B` | `0x18` ó `0x19` | Depende de `SDO/SA0`; el barrido del §7.2 lo detecta |

Inicialización en Arduino: `Wire.begin(21, 22);` — **nunca** `Wire.begin()` sin argumentos en esta placa
(el core usaría GPIO21/22 por defecto, pero ser explícito evita sorpresas si se cambia de core).

### 6.4 Acelerómetro LIS3DHTR e interrupciones

- Bus I²C (`SDA_0`/`SCL_0`), resolución seleccionable, FIFO interno.
- Las dos interrupciones del sensor (INT1 / INT2) van a **`GPIO26` y `GPIO27`** a través de los puentes
  soldables **`J6` y `J7`, que vienen ABIERTOS de fábrica** (`Open`). Es decir: **hasta no cerrarlos con
  estaño, el ESP32 no recibe las interrupciones** (el bus I²C funciona igual).
- El pin `SDO/SA0` define la dirección (`0x18` con SA0 a GND, `0x19` con SA0 a VDD33).

**Procedimiento para habilitar las interrupciones**

1. Verificar con un barrido I²C (§7.2) en qué dirección responde.
2. Puentear `J6` (uno de los dos GPIO) y `J7` (el otro) con estaño.
3. Confirmar con continuidad qué GPIO quedó asociado a INT1 y a cuál INT2 (**⚠ Verificar**: el
   esquemático etiqueta las redes `INT1_ACEL` / `INT2_ACEL` y los puentes van a 26/27, pero el par
   exacto se confirma con el multímetro o con el autotest del §7.6).

### 6.5 Lector microSD (SPI)

Conector `J5B` `TF-015` (microSD push-push). Conexionado real medido en el PCB:

| Pad del socket | Señal | Red / GPIO |
|---|---|---|
| 1 | DAT2 | *(sin conectar)* |
| 2 | CS / DAT3 | **`IO5` (GPIO5)** |
| 3 | CMD / MOSI (DI) | **`IO23` (GPIO23)** |
| 4 | VDD | `VDD33` (3.3 V) |
| 5 | CLK | **`IO18` (GPIO18)** |
| 6 | VSS | `GND` |
| 7 | DAT0 / MISO (DO) | **`IO19` (GPIO19)** |
| 8 | DAT1 | *(sin conectar)* |
| 9 | — | red suelta `NetJ5B_9`, sin uso |
| 10 y 12 | Detector / shell | **`IO15` (`IO15_TOUCH`)** |
| 11 y 13 | Shell | *(sin conectar)* |

- Solo **modo SPI (1 bit)**: DAT1/DAT2 no están ruteados, no intentar modo 4 bits.
- La hoja también usa `IO12` con `R39` (1 kΩ) y el jumper `JP8` (`Close`): `IO12` es pin de *strapping*
  (debe estar bajo al arrancar). Si se usa, revisar que no se fuerce a alto durante el reset.
- Desacoplo local: 100 nF (`C16`) junto al socket.

### 6.6 Indicadores LED

- **12 LED azules** `D4`–`D15`, modelo `19-217/BHC-ZL1M2RY/6T`.
- Cada canal lleva un driver **MOSFET N `PMZ550UNEYL`** (`Q3`–`Q14`), con **1 kΩ en la puerta** y
  **pull-down de 4.7 kΩ**, más su resistencia serie de LED.
- Encendido en **ALTO** sobre la línea de control.
- Las líneas de control que usa la hoja `LEDs` son:
  **`IO13`, `IO14`, `IO16`, `IO17`, `IO18`, `IO19`, `IO23`, `IO25`, `IO26`, `IO27`**.
- Además, `D3` (TXD) y `D2` (RXD) en la hoja `USB-UART` son testigos de actividad de la UART.

> **Importante — pines compartidos.** `IO18`, `IO19` e `IO23` son el bus SPI del microSD, y `IO26`/`IO27`
> son las interrupciones del LIS3DH. Por diseño, esos LED funcionan como **testigos de actividad de bus**
> y parpadearán solos cuando haya tráfico SPI o interrupciones. No son GPIO exclusivos para LEDs.
> Como la hoja declara 12 LED sobre 10 líneas, **⚠ Verificar** el mapa canal ↔ GPIO con el autotest del
> §7.6 antes de usar la barra como display.

### 6.7 Peinetas de expansión

Ocho conectores, agrupados en pares macho/hembra para apilado:

| Familia | Cantidad | Señales que expone |
|---|---|---|
| `SIP-1X10` (×2) | 2 | `IO26`, `IO27`, `IO5`, `IO23`, `IO19`, `IO18`, `SDA_0`, `SCL_0` + alimentación |
| `SIP-1X8` — bloque A (×2) | 2 | `IO13`, `IO14`, `IO16`, `IO17`, `IO25` + alimentación |
| `SIP-1X8` — bloque B (×2) | 2 | `SDA_0`, `SCL_0` y GPIO del bloque digital |
| `SIP-1X6` (×2) | 2 | Señales de expansión / alimentación |

Cada pin está rotulado en el silkscreen con el **nombre de red** (`IO13`, `SDA_0`, `VDD33`, `VDD5V`, `GND`…),
de modo que la serigrafía coincide 1:1 con la tabla del §5 y con la hoja `CONECTORES`.

### 6.8 Puentes soldables (jumpers) del diseño

| Jumper | Valor de BOM | Función |
|---|---|---|
| `Close` en hoja `FUENTE` | *Close* | Une **VBUS** (USB) con el riel de **5 V**. Debe estar cerrado para alimentar la placa por USB |
| `JP1`, `JP2` | *Close* | Puentes de configuración de alimentación del bloque USB-UART |
| `JP8` (hoja `MICRO SD`) | *Close* | Puente en la red de `IO12` |
| `J2` (hoja `LEDs`) | *Close* | Puente de configuración de la barra de LED |
| `J6`, `J7` (hoja `SENSORES`) | **Open** | Habilitan las interrupciones del LIS3DH hacia `IO26`/`IO27` |

---

## 7. Ejemplos de código listos para usar

Todas las placas usan el core Arduino-ESP32. Velocidad de monitor: **115200**.

### 7.1 Verificación básica (arranque y consola)

```cpp
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.printf("STELLARIS UNO E3 MAX\n");
  Serial.printf("Chip: %s  Cores: %d  Rev: %d\n",
                ESP.getChipModel(), ESP.getChipCores(), ESP.getChipRevision());
  Serial.printf("Flash: %u bytes (%.1f MB)\n",
                ESP.getFlashChipSize(), ESP.getFlashChipSize() / 1048576.0);
  Serial.printf("SDK: %s\n", ESP.getSdkVersion());
}
void loop() { delay(1000); }
```

### 7.2 Barrido del bus I²C

```cpp
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);          // SDA = GPIO21, SCL = GPIO22
  Wire.setClock(100000);
  delay(200);
  Serial.println("Barrido I2C (SDA=21, SCL=22):");
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0)
      Serial.printf("  dispositivo en 0x%02X%s\n", a,
                    a == 0x38 ? "  <- AHT20" :
                    (a == 0x18 || a == 0x19) ? "  <- LIS3DHTR" : "");
  }
  Serial.println("Fin del barrido.");
}
void loop() {}
```

### 7.3 AHT20 — lectura por I²C con `Wire` (sin librerías)

```cpp
#include <Wire.h>
#define AHT20 0x38

void aht20_init() {
  Wire.beginTransmission(AHT20); Wire.write(0xBE);
  Wire.write(0x08); Wire.write(0x00);        // calibración
  Wire.endTransmission();
  delay(40);
}

bool aht20_read(float &tempC, float &humPct) {
  Wire.beginTransmission(AHT20);
  Wire.write(0xAC); Wire.write(0x33); Wire.write(0x00);   // trigger
  Wire.endTransmission();
  delay(80);
  if (Wire.requestFrom((uint8_t)AHT20, (uint8_t)6) != 6) return false;
  uint8_t b[6];
  for (int i = 0; i < 6; i++) b[i] = Wire.read();
  if (b[0] & 0x80) return false;                            // ocupado
  uint32_t rawH = ((uint32_t)b[1] << 12) | ((uint32_t)b[2] << 4) | (b[3] >> 4);
  uint32_t rawT = ((uint32_t)(b[3] & 0x0F) << 16) | ((uint32_t)b[4] << 8) | b[5];
  humPct = (rawH * 100.0f) / 1048576.0f;
  tempC = (rawT * 200.0f) / 1048576.0f - 50.0f;
  return true;
}

void setup() {
  Serial.begin(115200); Wire.begin(21, 22); delay(200);
  aht20_init();
}
void loop() {
  float t, h;
  if (aht20_read(t, h))
    Serial.printf("AHT20  T=%.2f C  HR=%.2f %%\n", t, h);
  else
    Serial.println("AHT20: lectura fallida");
  delay(2000);
}
```

*(Alternativa con librería: `Adafruit AHTX0` — `aht.begin(&Wire)` con `Wire.begin(21,22)` previo.)*

### 7.4 LIS3DHTR — acelerómetro

Con librería `Adafruit LIS3DH`:

```cpp
#include <Wire.h>
#include <Adafruit_LIS3DH.h>
Adafruit_LIS3DH lis;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  if (!lis.begin(0x18)) {                       // probar 0x19 si falla
    Serial.println("LIS3DH no encontrado (probar 0x19)");
    while (1) delay(1000);
  }
  lis.setRange(LIS3DH_RANGE_4_G);
  lis.setDataRate(LIS3DH_DATARATE_100_HZ);
  Serial.println("LIS3DH listo");
}

void loop() {
  lis.read();
  Serial.printf("X=%6d  Y=%6d  Z=%6d\n", lis.x, lis.y, lis.z);
  delay(200);
}
```

Lectura directa de registros (sin librerías):

```cpp
#include <Wire.h>
uint8_t lis_addr = 0x18;

void lis_write(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(lis_addr); Wire.write(reg); Wire.write(val); Wire.endTransmission();
}
void lis_read(uint8_t reg, uint8_t *buf, uint8_t n) {
  Wire.beginTransmission(lis_addr); Wire.write(reg | 0x80); Wire.endTransmission(false);
  Wire.requestFrom(lis_addr, n);
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
}

void setup() {
  Serial.begin(115200); Wire.begin(21, 22); delay(100);
  lis_write(0x20, 0x57);   // CTRL_REG1: 100 Hz, XYZ on
}
void loop() {
  uint8_t d[6];
  lis_read(0x28, d, 6);    // OUT_X_L .. OUT_Z_H
  int16_t x = (int16_t)(d[0] | (d[1] << 8)) >> 4;
  int16_t y = (int16_t)(d[2] | (d[3] << 8)) >> 4;
  int16_t z = (int16_t)(d[4] | (d[5] << 8)) >> 4;
  Serial.printf("X=%6d  Y=%6d  Z=%6d\n", x, y, z);
  delay(200);
}
```

### 7.5 microSD por SPI

```cpp
#include <SPI.h>
#include <SD.h>

#define SD_CS   5     // GPIO5
#define SD_CLK  18    // GPIO18
#define SD_MISO 19    // GPIO19
#define SD_MOSI 23    // GPIO23

void setup() {
  Serial.begin(115200);
  delay(200);
  SPI.begin(SD_CLK, SD_MISO, SD_MOSI, SD_CS);
  if (!SD.begin(SD_CS)) {
    Serial.println("microSD: no se pudo montar (revisar tarjeta FAT32 <= 32 GB)");
    return;
  }
  Serial.printf("microSD OK  tipo=%d  tamano=%llu MB\n",
                SD.cardType(), SD.cardSize() / (1024ULL * 1024ULL));

  File f = SD.open("/prueba.txt", FILE_WRITE);
  if (f) { f.println("STELLARIS UNO E3 MAX"); f.close(); Serial.println("escritura OK"); }

  f = SD.open("/prueba.txt");
  while (f && f.available()) Serial.write(f.read());
  if (f) f.close();
}
void loop() {}
```

> Recordar: `GPIO5` es también *strapping*; el pull-up de `CS` del socket y la red del módulo lo mantienen
> alto al arrancar, pero **no alimentar la tarjeta SD desde otra fuente** ni inyectar señal sin la placa encendida.

### 7.6 Autotest de LEDs y mapeo canal ↔ GPIO

Este sketch recorre las líneas de control de la barra una por una y las reporta por consola, para
construir la tabla real canal ↔ GPIO de la placa:

```cpp
const int lineas[] = {13, 14, 16, 17, 18, 19, 23, 25, 26, 27};
const int N = sizeof(lineas) / sizeof(lineas[0]);

void setup() {
  Serial.begin(115200);
  delay(300);
  for (int i = 0; i < N; i++) {
    pinMode(lineas[i], OUTPUT);
    digitalWrite(lineas[i], LOW);
  }
  Serial.println("Autotest de LEDs: anotar que LED enciende con cada GPIO");
}

void loop() {
  for (int i = 0; i < N; i++) {
    Serial.printf("-> GPIO%d\n", lineas[i]);
    digitalWrite(lineas[i], HIGH);
    delay(800);
    digitalWrite(lineas[i], LOW);
    delay(200);
  }
  Serial.println("--- fin de la vuelta ---");
  delay(2000);
}
```

### 7.7 Pulsador BOOT

```cpp
void setup() {
  Serial.begin(115200);
  pinMode(0, INPUT_PULLUP);
}
void loop() {
  if (digitalRead(0) == LOW) {
    Serial.println("BOOT pulsado");
    while (digitalRead(0) == LOW) delay(10);   // esperar liberacion
  }
  delay(20);
}
```

---

## 8. Diagnóstico y solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| No aparece el puerto COM | Driver CH340 ausente, cable USB sin datos, o placa sin `VDD33` | Instalar `CH341SER`, cambiar cable, medir 3.3 V en las peinetas |
| Aparece el COM pero no flashea | Auto-descarga no engancha | BOOT + RESET manual (§4.5); bajar baudios a 115200 |
| `Failed to connect ... Timed out waiting for packet header` | `IO0` retenido en bajo por carga externa o firmware colgado | Desconectar la peineta de `IO0`, entrar en modo descarga manual |
| `A fatal error occurred: MD5 of file does not match` | Flash corrupta o cable marginal | `esptool erase_flash` + regrabar con cable corto |
| Arranca en bucle de reset | `EN` con ruido, fuente débil en WiFi, o `IO12`/`IO15` en el nivel equivocado | Alimentar por DC, revisar cargas en los pines de *strapping* |
| I²C no responde | Sin pull-ups externos, bus mal referenciado, o sensor sin alimentar | Los 10 kΩ están en placa; verificar 3.3 V en `VDD33` y continuidad de `SDA_0`/`SCL_0` |
| LIS3DH no aparece | Dirección equivocada (0x18 vs 0x19) | Correr el barrido I²C del §7.2 |
| No hay interrupciones del acelerómetro | `J6`/`J7` abiertos de fábrica | Puentearlos con estaño (§6.4) |
| microSD no monta | Contacto sucio, tarjeta exFAT/64 GB+, o CS mal definido | Probar tarjeta FAT32 ≤ 32 GB, limpiar contactos, confirmar `CS=GPIO5` |
| LED de la barra encienden solos | Son testigos de bus en `IO18/19/23/26/27` | Es el comportamiento previsto (§6.6) |

---

## 9. Estado del diseño y notas de fabricación

Estados reportados por el proyecto (no re-verificados en esta sesión más allá de la lectura de archivos):

- Esquemático: 9 hojas con símbolos visibles, ERC con 0 errores en los reportes `ERC_cero_errores.rpt`.
- PCB: DRC con 0 errores en `DRC_cero_errores.rpt`, modelo 3D STEP global disponible (110 MB).

Observaciones a resolver **antes de fabricar**:

1. **Footprints heredados:** en el PCB existen 13 pads soldables `JPAD-0402` cuyo `sheetname` es
   `ESP32-WROOM-32D-N4`, una hoja que **no existe** en el proyecto actual. Revisar si forman parte del
   diseño vigente o si son residuo de una jerarquía anterior, y depurarlos con **F8 (Update PCB from
   Schematic)** desde KiCad antes de generar los Gerbers.
2. **Pines compartidos LED / microSD / interrupciones:** documentado en §6.6. Decidir si se usan como
   testigos de actividad o si se liberan cambiando la barra de LED a GPIOs exclusivos.
3. **Puentes `Close`/`Open`:** confirmar en fabricación el estado de cada uno (`Close` = cerrado con
   estaño/0 Ω; `J6`/`J7` = abiertos), porque definen si la placa arranca por USB y si hay interrupciones.
4. **`IO12`:** intervenir solo después de leer la nota de *strapping* (§5).

---

## Anexo A — Inventario de bloques

| Bloque | Componentes clave |
|---|---|
| Alimentación | `AMS1117-5.0`, `AMS1117-3.3`, `AO3401A` (protección), `DC-005` (jack), `PH-2PWB` (JST), `CL31A226KAHNNNE` 22 µF, `RST47UF25V035` 47 µF, `CC0603KRX7R9BB104` 100 nF |
| USB-UART | `CH340K` (`U2`), `TYPE-C16PIN` (`J1`), `SS8050` (`Q1`, `Q2`), `SRV05-4-P-T7` (`U1`), `B5819W_SL` (`D1`), `MF-PSMF050X-2` (`F1`), 22 nF ×3, `0402WGF4701TCE` 4.7 kΩ, `0402WGF1202TCE` 12 kΩ |
| MCU | `ESP32-WROOM-32D` (`U3`), 4 MB flash interna |
| Pulsadores | `S1` BOOT (`IO0`), `S2` RESET (`EN`), pull-ups 12 kΩ / 10 kΩ, 1 nF ×2 |
| LEDs | 12 × `19-217/BHC-ZL1M2RY/6T` (`D4`–`D15`), 12 × `PMZ550UNEYL` (`Q3`–`Q14`), 1 kΩ en puerta, 4.7 kΩ pulldown |
| microSD | `TF-015` (`J5`), `C16` 100 nF, `R39` 1 kΩ, `JP8` |
| Sensores | `AHT20` (`U5`), `LIS3DHTR` (`U4`), pull-ups 10 kΩ, 100 nF + 10 µF, `J6`/`J7` |
| Expansión | 4 × `SIP-1X8P`, 2 × `SIP-1X6P`, 2 × `SIP-1X10P` |

## Anexo B — Archivos del proyecto

```
DEV_HW107_STELLARIS_UNO_E3_MAX/
├── DEV_HW107_STELLARIS_UNO_E3_MAX.kicad_pro    # proyecto
├── DEV_HW107_STELLARIS_UNO_E3_MAX.kicad_sch    # esquemático raíz
├── DEV_HW107_STELLARIS_UNO_E3_MAX.kicad_pcb    # PCB
├── DEV_HW107_STELLARIS_UNO_E3_MAX.kicad_dru    # reglas de diseño
├── DEV_HW107_STELLARIS_UNO_E3_MAX.step         # modelo 3D del ensamble
├── FUENTE.kicad_sch · USB-UART.kicad_sch · BOTONES.kicad_sch
├── LEDs.kicad_sch · MICRO SD.kicad_sch · SENSORES.kicad_sch
├── SIID.kicad_sch · CONECTORES.kicad_sch
├── ERC_cero_errores.rpt · DRC_cero_errores.rpt
└── MANUAL_USUARIO_STELLARIS.md                 # este documento
```

---

*Manual generado por el agente EDA a partir de los archivos del proyecto KiCad 10.0.0. Para cualquier
dato no verificable desde el proyecto se ha marcado explícitamente con ⚠ Verificar en lugar de asumirlo.*
