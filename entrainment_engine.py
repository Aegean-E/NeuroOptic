"""
NeuroOptic - Generalized Visual Entrainment Engine (Gamma-Optimized)

A precision frequency-configurable visual oscillator designed for research
applications. Implements hardware-aware rendering, monotonic phase accumulation,
and strict safety limits based on monitor refresh rates.
"""

import sys
import time
import math
import platform
import random
import csv
import os
from datetime import datetime
import gc
import logging
import argparse
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple

import glfw
import numpy as np
from OpenGL.GL import *

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [NeuroOptic] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WaveformType(Enum):
    SQUARE = auto()
    SINE = auto()
    AM_CARRIER = auto()
    TRIANGLE = auto()


class ShamType(Enum):
    NONE = auto()
    DETUNE = auto()  # Slight frequency shift (e.g. 40Hz -> 38.5Hz)
    LOW_AMP = auto()  # Low amplitude oscillation
    PHASE_JITTER = auto()  # Random micro phase jitter
    STATIC = auto()  # Non-oscillating light


class StimulationMode(Enum):
    FULL_SCREEN = auto()
    PERIPHERAL_RING = auto()
    HEMIFIELD_LEFT = auto()
    HEMIFIELD_RIGHT = auto()
    SPLIT_HEMIFIELD = auto() # Left/Right independent
    QUADRANT_TL = auto()  # Top-Left
    QUADRANT_TR = auto()  # Top-Right
    QUADRANT_BL = auto()  # Bottom-Left
    QUADRANT_BR = auto()  # Bottom-Right


@dataclass
class FrequencyBand:
    name: str
    min_hz: float
    max_hz: float


class FrequencyManager:
    """
    Manages frequency bands and validates targets against hardware limits.
    """
    BANDS = [
        FrequencyBand("Delta", 1, 4),
        FrequencyBand("Theta", 4, 8),
        FrequencyBand("Alpha", 8, 12),
        FrequencyBand("Beta", 13, 30),
        FrequencyBand("Gamma", 30, 80),
        FrequencyBand("High Gamma", 80, 120),
    ]

    @staticmethod
    def get_band_name(frequency: float) -> str:
        for band in FrequencyManager.BANDS:
            if band.min_hz <= frequency <= band.max_hz:
                return band.name
        return "Custom"

    @staticmethod
    def validate_frequency(target_freq: float, refresh_rate: int, waveform: WaveformType) -> Tuple[float, WaveformType]:
        """
        Calculates safe frequency ceiling (Nyquist limit) and validates.
        Returns the (target_freq, waveform) tuple. Switches waveform if compatibility rules require it.
        """
        # Nyquist limit: We need at least 2 frames to represent a full cycle (On/Off or Peak/Trough)
        safe_ceiling = refresh_rate / 2.0

        if target_freq > safe_ceiling:
            raise ValueError(
                f"Target frequency {target_freq} Hz exceeds safe representable limit "
                f"({safe_ceiling} Hz) for the current monitor refresh rate ({refresh_rate} Hz).\n"
                f"Please lower the frequency or use a higher refresh rate monitor (e.g., 144Hz, 240Hz)."
            )

        if target_freq <= 0:
            raise ValueError("Frequency must be positive.")

        # Case 2: Non-integer frames per cycle
        # "If non-integer -> Allow sine wave only. Warn if square wave requested."
        if waveform == WaveformType.SQUARE:
            # Symmetry Check: We need integer frames per HALF cycle for 50% duty cycle
            frames_per_half_cycle = refresh_rate / (2.0 * target_freq)
            if abs(frames_per_half_cycle - round(frames_per_half_cycle)) > 0.01:
                logger.warning(
                    f"⚠ COMPATIBILITY WARNING: {target_freq} Hz cannot be precisely represented by a Square wave "
                    f"on this display ({refresh_rate} Hz).\n"
                    f"   Frames/Half-Cycle: {frames_per_half_cycle:.2f} (Non-Integer).\n"
                    f"   Result: Duty Cycle Distortion (Not 50%).\n"
                    f"   Action: Switching to SINE wave to maintain signal integrity."
                )
                return target_freq, WaveformType.SINE

            # Risk Warning for Photosensitive Range (10-30Hz)
            if 10 <= target_freq <= 30:
                logger.warning(
                    f"⚠ SAFETY WARNING: {target_freq} Hz Square Wave is in the high-risk photosensitive window (10-30 Hz).")

        # Case 1: Integer or Sine/AM -> Safe
        return target_freq, waveform


class Oscillator:
    """
    Master Oscillator Engine.
    Core equation: phase(t) = (2π × f × t + φ) mod 2π
    """

    def __init__(self, frequency: float, waveform: WaveformType, phase_offset: float = 0.0, rng: random.Random = None):
        self.frequency = frequency
        self.waveform = waveform
        self.phase_base = phase_offset  # Base phase offset (radians)
        self.t_ref = 0.0  # Reference time for frequency changes
        self.carrier_freq = 0.0  # Only for AM_CARRIER
        self.carrier_phase_base = 0.0
        self.phase_jitter = 0.0
        self.rng = rng if rng else random.Random()

    def set_phase_jitter(self, amount: float):
        self.phase_jitter = amount

    def set_carrier_frequency(self, freq: float):
        self.carrier_freq = freq

    def set_frequency(self, new_freq: float, current_t: float):
        """
        Updates frequency in real-time without phase discontinuity.
        """
        dt = current_t - self.t_ref

        # Snapshot current phases to become new bases
        self.phase_base = (2 * math.pi * self.frequency * dt + self.phase_base) % (2 * math.pi)
        self.carrier_phase_base = (2 * math.pi * self.carrier_freq * dt + self.carrier_phase_base) % (2 * math.pi)

        self.frequency = new_freq
        self.t_ref = current_t

    def update_phase(self, delta_rad: float):
        """
        Injects a phase shift (e.g., for closed-loop error correction).
        """
        self.phase_base = (self.phase_base + delta_rad) % (2 * math.pi)

    def get_luminance(self, t: float) -> float:
        """
        Calculates luminance (0.0 to 1.0) at monotonic time t.
        """
        # Time relative to last frequency change
        dt = t - self.t_ref

        # Core Phase Calculation
        jitter = 0.0
        if self.phase_jitter > 0:
            jitter = self.rng.uniform(-self.phase_jitter, self.phase_jitter)

        # phase = 2π * f * dt + φ_base
        phase = (2 * math.pi * self.frequency * dt + self.phase_base + jitter) % (2 * math.pi)

        if self.waveform == WaveformType.SQUARE:
            # Binary on/off flicker
            # sin(phase) >= 0 is ON (1.0), else OFF (0.0)
            return 1.0 if math.sin(phase) >= 0 else 0.0

        elif self.waveform == WaveformType.SINE:
            # Smooth oscillation
            # Map [-1, 1] sine wave to [0, 1] luminance
            return 0.5 + 0.5 * math.sin(phase)

        elif self.waveform == WaveformType.AM_CARRIER:
            # Amplitude Modulated Carrier
            # Carrier signal (high freq) modulated by target frequency
            carrier_phase = (2 * math.pi * self.carrier_freq * dt + self.carrier_phase_base) % (2 * math.pi)
            carrier_val = 0.5 + 0.5 * math.sin(carrier_phase)

            modulator_val = 0.5 + 0.5 * math.sin(phase)
            return carrier_val * modulator_val

        elif self.waveform == WaveformType.TRIANGLE:
            # Triangle Wave (Future-Expandable)
            # Map phase [0, 2pi] to [0, 1] luminance linearly
            p = phase / (2 * math.pi)
            return 1.0 - abs(2.0 * p - 1.0)

        return 0.0


class EntrainmentEngine:
    def __init__(
            self,
            target_freq: float,
            waveform: WaveformType,
            mode: StimulationMode = StimulationMode.FULL_SCREEN,
            ramp_duration: float = 0.0,
            session_duration: float = 0.0,
            sham_type: ShamType = ShamType.NONE,
            sham_seed: Optional[int] = None,
            gamma: float = 1.0,
            brightness: float = 1.0,
            phase_offset: float = 0.0,
            right_freq: Optional[float] = None,
            right_phase_offset: float = 0.0
    ):
        self.target_freq = target_freq
        self.waveform = waveform
        self.waveform_left = waveform
        self.waveform_right = waveform
        self.mode = mode
        self.ramp_duration = ramp_duration
        self.session_duration = session_duration
        self.gamma = gamma
        self.max_brightness = brightness
        self.phase_offset_rad = math.radians(phase_offset)
        
        # Dual Hemifield Logic
        self.right_freq = right_freq if right_freq is not None else target_freq
        self.right_phase_rad = math.radians(right_phase_offset)
        
        self.sham_type = sham_type

        # 11️⃣ Deterministic Randomness Scope
        if sham_seed is None:
            sham_seed = random.randint(0, 100000)
        self.sham_seed = sham_seed
        self.rng = random.Random(self.sham_seed)

        if self.sham_type != ShamType.NONE:
            logger.warning(f"⚠ SHAM MODE ACTIVE: {self.sham_type.name} | Seed: {self.sham_seed}")
            if self.sham_type == ShamType.DETUNE:
                # Detune by +/- 5-10%
                detune_factor = self.rng.choice([0.90, 0.95, 1.05, 1.10])
                self.target_freq *= detune_factor
                self.right_freq *= detune_factor # Detune both
                logger.info(f"Sham: Frequency detuned to {self.target_freq:.2f} Hz")

            elif self.sham_type == ShamType.STATIC:
                self.target_freq = 0.0
                logger.info("Sham: Frequency set to 0 Hz (Static)")

        self.window = None
        self.monitor_refresh_rate = 60  # Default fallback
        self.oscillator_left: Optional[Oscillator] = None
        self.oscillator_right: Optional[Oscillator] = None
        self.gpu_info = {}
        self.running = False

        self.phase_jitter_amount = 0.0
        if self.sham_type == ShamType.PHASE_JITTER:
            self.phase_jitter_amount = 0.5  # Significant jitter

        self.frame_data = []  # Stores (timestamp, delta, luminance) for audit
        self.dropped_frame_log = []  # Defer logging to avoid I/O latency during render loop

    def initialize_hardware(self):
        """
        Initializes GLFW, detects monitor specs, and sets up the window.
        """
        if not glfw.init():
            logger.error("Failed to initialize GLFW")
            sys.exit(1)

        # Get Primary Monitor and Video Mode
        monitor = glfw.get_primary_monitor()
        mode = glfw.get_video_mode(monitor)
        self.monitor_refresh_rate = mode.refresh_rate

        logger.info(f"Hardware Detected: {mode.size.width}x{mode.size.height} @ {self.monitor_refresh_rate} Hz")

        # Validate Frequencies against Hardware
        try:
            # Validate Left (Main)
            self.target_freq, self.waveform_left = FrequencyManager.validate_frequency(self.target_freq,
                                                                                  self.monitor_refresh_rate,
                                                                                  self.waveform)
            # Validate Right
            self.right_freq, self.waveform_right = FrequencyManager.validate_frequency(self.right_freq,
                                                                                  self.monitor_refresh_rate,
                                                                                  self.waveform)

            # Create Oscillator AFTER validation to ensure settings (like jitter) aren't overwritten
            self.oscillator_left = Oscillator(self.target_freq, self.waveform_left, phase_offset=self.phase_offset_rad, rng=self.rng)
            self.oscillator_right = Oscillator(self.right_freq, self.waveform_right, phase_offset=self.right_phase_rad, rng=self.rng)

            # Apply Sham / Advanced Settings
            if self.phase_jitter_amount > 0:
                self.oscillator_left.set_phase_jitter(self.phase_jitter_amount)
                self.oscillator_right.set_phase_jitter(self.phase_jitter_amount)

            band = FrequencyManager.get_band_name(self.target_freq)
            logger.info(f"Target Frequency: {self.target_freq} Hz ({band}) - SAFE")
        except ValueError as e:
            logger.critical(str(e))
            glfw.terminate()
            sys.exit(1)

        # If AM Carrier, set carrier to max safe frequency (Nyquist)
        if self.waveform == WaveformType.AM_CARRIER:
            carrier = self.monitor_refresh_rate / 2.0
            self.oscillator_left.set_carrier_frequency(carrier)
            self.oscillator_right.set_carrier_frequency(carrier)
            logger.info(f"AM Carrier Frequency set to: {carrier} Hz")

        # Create Window (Fullscreen recommended for immersion, windowed for dev)
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)

        # Create a fullscreen window on the primary monitor
        self.window = glfw.create_window(mode.size.width, mode.size.height, "NeuroOptic Engine", monitor, None)

        if not self.window:
            logger.error("Failed to create GLFW window")
            glfw.terminate()
            sys.exit(1)

        glfw.make_context_current(self.window)

        # Enable VSync - Crucial for timing accuracy
        glfw.swap_interval(1)

        # Center and show (if windowed, but we are fullscreen)
        glfw.show_window(self.window)

        # OpenGL Setup
        glClearColor(0.0, 0.0, 0.0, 1.0)

        # 3️⃣ Hardware Abstraction Layer - Metadata Collection
        # We query OpenGL after context is current
        renderer = glGetString(GL_RENDERER).decode('utf-8')
        version = glGetString(GL_VERSION).decode('utf-8')
        
        self.gpu_info['renderer'] = renderer
        self.gpu_info['version'] = version

        # Color depth
        depth = mode.bits.red + mode.bits.green + mode.bits.blue

        logger.info("=== Hardware Abstraction Layer ===")
        logger.info(f"GPU: {renderer}")
        logger.info(f"Driver: {version}")
        logger.info(f"Display: {mode.size.width}x{mode.size.height} @ {self.monitor_refresh_rate} Hz")
        logger.info(f"Color Depth: {depth}-bit (R{mode.bits.red}G{mode.bits.green}B{mode.bits.blue})")
        logger.info(f"VSync: Enabled (Double Buffered)")
        logger.info("==================================")

    def _draw_circle(self, radius: float, segments: int = 100):
        """Helper to draw a circle (used for Ring mask)."""
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0.0, 0.0)  # Center
        for i in range(segments + 1):
            theta = 2.0 * math.pi * float(i) / float(segments)
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            glVertex2f(x, y)
        glEnd()

    def set_frequency(self, freq: float):
        # Updates main (left) oscillator
        if self.oscillator_left:
            self.oscillator_left.set_frequency(freq, glfw.get_time())

    def update_phase(self, delta_deg: float):
        if self.oscillator_left:
            self.oscillator_left.update_phase(math.radians(delta_deg))

    def render_stimulus(self, lum_left: float, lum_right: float):
        """Renders the visual stimulus based on the selected mode."""
        
        if self.mode == StimulationMode.FULL_SCREEN:
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(-1.0, -1.0, 1.0, 1.0)

        elif self.mode == StimulationMode.SPLIT_HEMIFIELD:
            # 10️⃣ Independent Dual-Hemifield
            # Left Side
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(-1.0, -1.0, 0.0, 1.0)
            # Right Side
            glColor3f(lum_right, lum_right, lum_right)
            glRectf(0.0, -1.0, 1.0, 1.0)

        elif self.mode == StimulationMode.PERIPHERAL_RING:
            glColor3f(lum_left, lum_left, lum_left)
            # 1. Draw full oscillating background
            glRectf(-1.0, -1.0, 1.0, 1.0)
            # 2. Draw static black central mask (Radius 0.3 NDC)
            glColor3f(0.0, 0.0, 0.0)
            self._draw_circle(0.3)

        elif self.mode == StimulationMode.HEMIFIELD_LEFT:
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(-1.0, -1.0, 0.0, 1.0)  # Left half

        elif self.mode == StimulationMode.HEMIFIELD_RIGHT:
            # Use lum_left (main) unless we want to force right oscillator? 
            # Standard behavior is main freq on selected field.
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(0.0, -1.0, 1.0, 1.0)  # Right half

        elif self.mode == StimulationMode.QUADRANT_TL:
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(-1.0, 0.0, 0.0, 1.0)  # Top-Left

        elif self.mode == StimulationMode.QUADRANT_TR:
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(0.0, 0.0, 1.0, 1.0)  # Top-Right

        elif self.mode == StimulationMode.QUADRANT_BL:
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(-1.0, -1.0, 0.0, 0.0)  # Bottom-Left

        elif self.mode == StimulationMode.QUADRANT_BR:
            glColor3f(lum_left, lum_left, lum_left)
            glRectf(0.0, -1.0, 1.0, 0.0)  # Bottom-Right

    def run(self):
        """
        Main Rendering Loop.
        """
        self.running = True

        # Timing variables for drift control and logging
        start_time = glfw.get_time()
        frame_count = 0
        last_log_time = start_time

        expected_frame_time = 1.0 / self.monitor_refresh_rate
        last_frame_time = start_time

        logger.info("Engine Started. Press ESC to exit.")
        logger.info(f"Recording session data... (Expected IFI: {expected_frame_time * 1000:.2f} ms)")

        # OPTIMIZATION: Disable GC during render loop to prevent micro-stutters
        gc.disable()

        while not glfw.window_should_close(self.window) and self.running:
            # 1. Monotonic Clock Sampling
            current_time = glfw.get_time()
            delta_time = current_time - last_frame_time
            elapsed_time = current_time - start_time

            # Session Duration Check
            if self.session_duration > 0 and elapsed_time > self.session_duration:
                logger.info("Session duration reached. Stopping.")
                self.running = False

            # 2. Frame Drop Detection
            # If delta is significantly larger than expected (allowing 10% jitter), log it.
            if delta_time > (expected_frame_time * 1.1):
                # OPTIMIZATION: Store drop data now, log later. Printing here causes more drops.
                self.dropped_frame_log.append((len(self.frame_data), delta_time))

            last_frame_time = current_time

            # 3. Ramp-Up & Amplitude Calculation
            amplitude_scalar = 1.0
            if self.ramp_duration > 0 and elapsed_time < self.ramp_duration:
                amplitude_scalar = elapsed_time / self.ramp_duration

            # Sham: Low Amplitude
            if self.sham_type == ShamType.LOW_AMP:
                amplitude_scalar *= 0.15  # Cap at 15% brightness

            # 4. Oscillator Update & Luminance Calculation
            # We pass the SESSION time (elapsed_time) to the oscillator.
            # This ensures Phase 0 always aligns with Session Start (t=0), regardless of startup delay.
            raw_lum_left = self.oscillator_left.get_luminance(elapsed_time)
            raw_lum_right = self.oscillator_right.get_luminance(elapsed_time)

            # Apply amplitude envelope (Ramp/Sham)
            lum_left = raw_lum_left * amplitude_scalar
            lum_right = raw_lum_right * amplitude_scalar

            # 6️⃣ Brightness Ceiling (Scaling)
            lum_left *= self.max_brightness
            lum_right *= self.max_brightness

            # 5️⃣ Gamma Correction (Inverse)
            # L_out = L_in ^ gamma  =>  L_in = L_out ^ (1/gamma)
            if self.gamma != 1.0:
                if lum_left > 0: lum_left = lum_left ** (1.0 / self.gamma)
                if lum_right > 0: lum_right = lum_right ** (1.0 / self.gamma)

            # Record Metric (Skip first frame initialization delta)
            # OPTIMIZATION: Append once with calculated luminance to avoid double tuple allocation
            # We log Left luminance as primary reference
            if frame_count > 0:
                self.frame_data.append((current_time, delta_time, lum_left))

            # 4. Render
            # Clear background to black
            glClearColor(0.0, 0.0, 0.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT)
            
            self.render_stimulus(lum_left, lum_right)

            # 5. VSync Swap
            glfw.swap_buffers(self.window)
            glfw.poll_events()

            # Input handling
            if glfw.get_key(self.window, glfw.KEY_ESCAPE) == glfw.PRESS:
                self.running = False

            # Logging stats every second
            frame_count += 1
            if current_time - last_log_time >= 1.0:
                fps = frame_count / (current_time - last_log_time)
                # logger.debug(f"FPS: {fps:.2f} | Luminance: {luminance:.2f}")
                frame_count = 0
                last_log_time = current_time

        gc.enable()  # Re-enable GC for analysis
        self.analyze_session()
        self.cleanup()

    def analyze_session(self):
        """
        Computes session metrics and saves a publishable CSV report.
        """
        if not self.frame_data:
            logger.warning("No frame data recorded.")
            return

        # Convert to numpy for stats
        timestamps = np.array([x[0] for x in self.frame_data])
        deltas = np.array([x[1] for x in self.frame_data])
        luminances = np.array([x[2] for x in self.frame_data])

        # 1. Compute Metrics
        mean_ifi = np.mean(deltas) * 1000.0  # ms
        std_ifi = np.std(deltas) * 1000.0  # ms

        expected_ifi = (1.0 / self.monitor_refresh_rate)
        # Frame drop defined as deviation > 10% of expected interval
        drop_threshold = expected_ifi * 1.1
        dropped_frames = np.sum(deltas > drop_threshold)
        drop_pct = (dropped_frames / len(deltas)) * 100.0

        effective_fps = 1.0 / np.mean(deltas)

        # 2. Compute Actual Delivered Frequency (Zero-Crossing Analysis)
        # Remove DC offset to center signal around 0
        dc_offset = np.mean(luminances)
        ac_signal = luminances - dc_offset

        # Find zero crossings (where sign changes)
        crossings = np.diff(np.signbit(ac_signal))
        crossing_indices = np.where(crossings)[0]

        measured_freq = 0.0
        freq_std = 0.0

        if len(crossing_indices) > 1:
            t_start = timestamps[crossing_indices[0]]
            t_end = timestamps[crossing_indices[-1]]
            duration = t_end - t_start

            # Cycles = (Number of crossings) / 2
            if duration > 0:
                # Correction: N crossings define N-1 intervals
                measured_freq = ((len(crossing_indices) - 1) / 2.0) / duration

            # Calculate cycle-to-cycle consistency (Std Dev)
            # TODO: Detailed cycle-by-cycle analysis could be added here

        logger.info("=== Session Integrity Report ===")
        logger.info(f"Total Frames: {len(deltas)}")
        logger.info(f"Mean Frame Interval: {mean_ifi:.3f} ms (σ = {std_ifi:.3f} ms)")
        logger.info(f"Effective Refresh Rate: {effective_fps:.2f} Hz")
        logger.info(f"Frame Drops: {dropped_frames} ({drop_pct:.2f}%)")
        logger.info(f"Target Frequency: {self.target_freq:.2f} Hz")
        logger.info(f"Measured Delivered Frequency: {measured_freq:.3f} Hz (Actual)")

        if self.dropped_frame_log:
            logger.warning(f"Performance Alert: {len(self.dropped_frame_log)} frames dropped during session.")
            # Log first 5 drops details to avoid spamming console
            for i, (idx, dt) in enumerate(self.dropped_frame_log[:5]):
                logger.warning(f"  - Drop at frame {idx}: {dt * 1000:.2f}ms")
            if len(self.dropped_frame_log) > 5:
                logger.warning(f"  - ... and {len(self.dropped_frame_log) - 5} more.")
        logger.info("================================")

        # 2. Save CSV
        os.makedirs("session_data", exist_ok=True)
        filename = f"session_data/neurooptic_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # 12️⃣ Log More Metadata (Header Block)
                writer.writerow(["# === Session Metadata ==="])
                writer.writerow(["# OS", f"{platform.system()} {platform.release()}"])
                writer.writerow(["# Python", sys.version.split()[0]])
                writer.writerow(["# GPU", self.gpu_info.get('renderer', 'Unknown')])
                writer.writerow(["# Driver", self.gpu_info.get('version', 'Unknown')])
                writer.writerow(["# Refresh Rate", f"{self.monitor_refresh_rate} Hz"])
                writer.writerow(["# VSync", "Enabled"])
                writer.writerow(["# Mode", self.mode.name])
                writer.writerow(["# Waveform (Left)", self.waveform_left.name])
                writer.writerow(["# Frequency (Left)", f"{self.target_freq} Hz"])
                writer.writerow(["# Phase (Left)", f"{math.degrees(self.phase_offset_rad):.1f} deg"])
                if self.mode == StimulationMode.SPLIT_HEMIFIELD:
                    writer.writerow(["# Waveform (Right)", self.waveform_right.name])
                    writer.writerow(["# Frequency (Right)", f"{self.right_freq} Hz"])
                    writer.writerow(["# Phase (Right)", f"{math.degrees(self.right_phase_rad):.1f} deg"])
                writer.writerow(["# Ramp Duration", f"{self.ramp_duration} s"])
                writer.writerow(["# Session Duration", f"{self.session_duration} s"])
                writer.writerow(["# Gamma", self.gamma])
                writer.writerow(["# Brightness Cap", self.max_brightness])
                writer.writerow(["# Sham Type", self.sham_type.name])
                writer.writerow(["# Sham Seed", self.sham_seed])
                writer.writerow(["# ========================"])
                
                # Header
                writer.writerow(["Frame_ID", "Timestamp_Monotonic", "Delta_Time_Sec", "Luminance_NDC", "Target_Freq_Hz",
                                 "Sham_Mode"])
                # Data
                for i, (ts, dt, lum) in enumerate(self.frame_data):
                    writer.writerow([i, f"{ts:.6f}", f"{dt:.6f}", f"{lum:.4f}", self.target_freq, self.sham_type.name])

            logger.info(f"Session data saved to: {os.path.abspath(filename)}")
        except IOError as e:
            logger.error(f"Failed to save session data: {e}")

    def cleanup(self):
        logger.info("Shutting down engine...")
        if self.window:
            # Restore cursor or gamma if needed (not implemented here)
            glfw.destroy_window(self.window)
        glfw.terminate()


def parse_arguments():
    parser = argparse.ArgumentParser(description="NeuroOptic Visual Entrainment Engine")

    parser.add_argument(
        '--freq',
        type=float,
        default=40.0,
        help='Target frequency in Hz (Default: 40.0)'
    )

    parser.add_argument(
        '--waveform',
        type=str,
        choices=['sine', 'square', 'am', 'triangle'],
        default='sine',
        help='Waveform type: sine (default), square, am, or triangle'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'ring', 'left', 'right', 'split', 'quad_tl', 'quad_tr', 'quad_bl', 'quad_br'],
        default='full',
        help='Stimulation mode: full (default), ring (peripheral), left (hemifield), right (hemifield)'
    )

    parser.add_argument(
        '--preset',
        type=str,
        choices=['delta', 'alpha', 'beta', 'gamma', 'high_gamma'],
        help='Use a predefined frequency band preset (Overrides --freq)'
    )

    parser.add_argument(
        '--ramp',
        type=float,
        default=0.0,
        help='Ramp-up duration in seconds (Default: 0.0)'
    )

    parser.add_argument(
        '--duration',
        type=float,
        default=0.0,
        help='Session duration in seconds (0.0 = Infinite)'
    )

    parser.add_argument(
        '--sham',
        type=str,
        choices=['none', 'detune', 'low_amp', 'jitter', 'static'],
        default='none',
        help='Activate sham mode for research control conditions'
    )

    parser.add_argument(
        '--gamma',
        type=float,
        default=1.0,
        help='Display gamma correction value (e.g., 2.2). Default 1.0 (Linear/None).'
    )

    parser.add_argument(
        '--brightness',
        type=float,
        default=1.0,
        help='Global brightness cap (0.0 - 1.0). Scales output.'
    )

    parser.add_argument(
        '--phase',
        type=float,
        default=0.0,
        help='Initial phase offset in degrees (0-360).'
    )

    parser.add_argument(
        '--freq-right',
        type=float,
        help='Target frequency for Right Hemifield (Split mode only). Defaults to --freq if unset.'
    )

    parser.add_argument(
        '--phase-right',
        type=float,
        default=0.0,
        help='Phase offset for Right Hemifield in degrees (0-360).'
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    # Map string arg to Enum
    wf_map = {
        'sine': WaveformType.SINE,
        'square': WaveformType.SQUARE,
        'am': WaveformType.AM_CARRIER,
        'triangle': WaveformType.TRIANGLE
    }

    mode_map = {
        'full': StimulationMode.FULL_SCREEN,
        'ring': StimulationMode.PERIPHERAL_RING,
        'left': StimulationMode.HEMIFIELD_LEFT,
        'right': StimulationMode.HEMIFIELD_RIGHT,
        'split': StimulationMode.SPLIT_HEMIFIELD,
        'quad_tl': StimulationMode.QUADRANT_TL,
        'quad_tr': StimulationMode.QUADRANT_TR,
        'quad_bl': StimulationMode.QUADRANT_BL,
        'quad_br': StimulationMode.QUADRANT_BR
    }

    sham_map = {
        'none': ShamType.NONE,
        'detune': ShamType.DETUNE,
        'low_amp': ShamType.LOW_AMP,
        'jitter': ShamType.PHASE_JITTER,
        'static': ShamType.STATIC
    }

    # Preset Logic
    target_freq = args.freq
    if args.preset:
        presets = {
            'delta': 2.0,
            'alpha': 10.0,
            'beta': 20.0,
            'gamma': 40.0,
            'high_gamma': 80.0
        }
        target_freq = presets[args.preset]
        print(f"Loaded Preset: {args.preset.upper()} ({target_freq} Hz)")

    # Handle Quadrant args if user passed generic 'quad' (optional expansion) or specific
    mode = mode_map.get(args.mode, StimulationMode.FULL_SCREEN)

    engine = EntrainmentEngine(
        target_freq=target_freq,
        waveform=wf_map[args.waveform],
        mode=mode,
        ramp_duration=args.ramp,
        session_duration=args.duration,
        sham_type=sham_map[args.sham],
        gamma=args.gamma,
        brightness=args.brightness,
        phase_offset=args.phase,
        right_freq=args.freq_right,
        right_phase_offset=args.phase_right
    )

    engine.initialize_hardware()
    engine.run()