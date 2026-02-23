# NeuroOptic

## Generalized Visual Entrainment Engine (Gamma-Optimized)

NeuroOptic is a research-grade visual oscillator designed for precise brainwave entrainment. It supports configurable frequencies (1–120 Hz) with hardware-aware safety limits and drift-free phase accumulation.

### Features

*   **Precision Oscillator**: 0.01 Hz resolution using a monotonic high-resolution clock.
*   **Hardware-Aware**: Automatically detects monitor refresh rates and enforces Nyquist safety limits (e.g., Max 30Hz on a 60Hz screen).
*   **Waveforms**:
    *   **Sine**: Physiological oscillatory mimicry (Default).
    *   **Square**: Strong entrainment (Binary On/Off).
    *   **AM Carrier**: High-frequency carrier modulated at target frequency.
*   **Tech Stack**: Python, GLFW, OpenGL (VSync enabled).

### Installation

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

Run the engine via command line:

```bash
# Default (40Hz Gamma, Sine wave)
python entrainment_engine.py

# Custom Frequency (e.g., 10Hz Alpha)
python entrainment_engine.py --freq 10.0

# Square Wave (Strong entrainment)
python entrainment_engine.py --freq 40.0 --waveform square

# Amplitude Modulated
python entrainment_engine.py --freq 40.0 --waveform am
```