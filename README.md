# NeuroOptic

<p align="center">
  <img src="https://github.com/Aegean-E/NeuroOptic/blob/main/banner.jpg?raw=true" alt="NeuroOptic Banner" width="1200">
</p>

## Generalized Visual Entrainment Engine

NeuroOptic is a research-grade visual oscillator designed for precise brainwave entrainment. It supports configurable frequencies (1–120 Hz) with hardware-aware safety limits and drift-free phase accumulation.

### Features

*   **Precision Oscillator**: 0.01 Hz resolution using a monotonic high-resolution clock.
*   **Hardware-Aware**: Automatically detects monitor refresh rates and enforces Nyquist safety limits (e.g., Max 30Hz on a 60Hz screen).
*   **Waveforms**:
    *   **Sine**: Physiological oscillatory mimicry (Default).
    *   **Square**: Strong entrainment (Binary On/Off).
    *   **Triangle**: Linear fade in/out.
    *   **AM Carrier**: High-frequency carrier modulated at target frequency.
*   **Stimulation Modes**:
    *   **Full Screen**: Standard entrainment.
    *   **Split Hemifield**: Independent Left/Right control for binocular beats or lateralized stimulation.
    *   **Peripheral Ring**: Foveal sparing stimulation.
    *   **Quadrants**: Retinotopic mapping support (Top-Left, Bottom-Right, etc.).
*   **Research & Sham Control**:
    *   **Detune**: Frequency drifts slightly to prevent entrainment.
    *   **Low Amp**: Sub-threshold intensity.
    *   **Jitter**: Randomized phase timing.
    *   **Static**: Non-flickering control.
*   **Tech Stack**: Python, GLFW, OpenGL (VSync enabled).

### Installation

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

#### Graphical Interface (Recommended)
Launch the GUI controller:
```bash
python launcher.py
```

#### Command Line Interface
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

# Split Hemifield (Binocular Beats: Left 10Hz, Right 11Hz)
python entrainment_engine.py --mode split --freq 10.0 --freq-right 11.0

# Research Mode (Sham: Detuned Frequency)
python entrainment_engine.py --freq 40.0 --sham detune

# Session Control (10 min session, 5s ramp-up)
python entrainment_engine.py --duration 600 --ramp 5.0
```