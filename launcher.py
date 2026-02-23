import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

# Set Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NeuroOpticLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("NeuroOptic Controller")
        self.root.geometry("500x720")
        # self.root.resizable(False, False)

        # --- Header ---
        header = ctk.CTkLabel(root, text="Visual Entrainment Engine", font=("Segoe UI", 22, "bold"))
        header.pack(pady=(20, 10))

        # --- Main Container ---
        main_frame = ctk.CTkFrame(root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Frequency Section ---
        freq_frame = self.create_group_frame(main_frame, "Frequency Configuration")

        ctk.CTkLabel(freq_frame, text="Preset Band:").grid(row=1, column=0, sticky="w", pady=10, padx=10)
        self.preset_var = ctk.StringVar(value="Custom")
        self.preset_combo = ctk.CTkComboBox(freq_frame, variable=self.preset_var, state="readonly",
                                            values=['Custom', 'Delta (2Hz)', 'Alpha (10Hz)', 'Beta (20Hz)', 'Gamma (40Hz)', 'High Gamma (80Hz)'],
                                            command=self.on_preset_change)
        self.preset_combo.grid(row=1, column=1, sticky="e", padx=10)

        ctk.CTkLabel(freq_frame, text="Target Frequency (Hz):").grid(row=2, column=0, sticky="w", pady=10, padx=10)
        self.freq_var = tk.DoubleVar(value=40.0)
        self.freq_entry = ctk.CTkEntry(freq_frame, textvariable=self.freq_var)
        self.freq_entry.grid(row=2, column=1, sticky="e", padx=10)

        ctk.CTkLabel(freq_frame, text="Waveform:").grid(row=3, column=0, sticky="w", pady=10, padx=10)
        self.waveform_var = ctk.StringVar(value="sine")
        self.waveform_combo = ctk.CTkComboBox(freq_frame, variable=self.waveform_var, state="readonly",
                                              values=['sine', 'square', 'am', 'triangle'])
        self.waveform_combo.grid(row=3, column=1, sticky="e", padx=10)

        # --- Visual Mode Section ---
        vis_frame = self.create_group_frame(main_frame, "Visual Stimulation Mode")

        ctk.CTkLabel(vis_frame, text="Mode:").grid(row=1, column=0, sticky="w", pady=10, padx=10)
        self.mode_var = ctk.StringVar(value="full")
        self.mode_combo = ctk.CTkComboBox(vis_frame, variable=self.mode_var, state="readonly",
                                          values=['full', 'ring', 'left', 'right', 'split', 'quad_tl', 'quad_tr', 'quad_bl', 'quad_br'])
        self.mode_combo.grid(row=1, column=1, sticky="e", padx=10)

        # --- Session Control ---
        session_frame = self.create_group_frame(main_frame, "Session Control")

        ctk.CTkLabel(session_frame, text="Duration (sec, 0=Inf):").grid(row=1, column=0, sticky="w", pady=10, padx=10)
        self.duration_var = tk.DoubleVar(value=0.0)
        ctk.CTkEntry(session_frame, textvariable=self.duration_var).grid(row=1, column=1, sticky="e", padx=10)

        ctk.CTkLabel(session_frame, text="Ramp Up (sec):").grid(row=2, column=0, sticky="w", pady=10, padx=10)
        self.ramp_var = tk.DoubleVar(value=0.0)
        ctk.CTkEntry(session_frame, textvariable=self.ramp_var).grid(row=2, column=1, sticky="e", padx=10)

        # --- Research / Sham ---
        sham_frame = self.create_group_frame(main_frame, "Research / Sham Control")

        ctk.CTkLabel(sham_frame, text="Sham Condition:").grid(row=1, column=0, sticky="w", pady=10, padx=10)
        self.sham_var = ctk.StringVar(value="none")
        self.sham_combo = ctk.CTkComboBox(sham_frame, variable=self.sham_var, state="readonly",
                                          values=['none', 'detune', 'low_amp', 'jitter', 'static'])
        self.sham_combo.grid(row=1, column=1, sticky="e", padx=10)

        # --- Display & Phase ---
        display_frame = self.create_group_frame(main_frame, "Display & Phase")

        ctk.CTkLabel(display_frame, text="Gamma:").grid(row=1, column=0, sticky="w", pady=10, padx=5)
        self.gamma_var = tk.DoubleVar(value=1.0)
        ctk.CTkEntry(display_frame, textvariable=self.gamma_var, width=80).grid(row=1, column=1, sticky="w", padx=5)

        ctk.CTkLabel(display_frame, text="Bright:").grid(row=1, column=2, sticky="w", pady=10, padx=5)
        self.brightness_var = tk.DoubleVar(value=1.0)
        ctk.CTkEntry(display_frame, textvariable=self.brightness_var, width=80).grid(row=1, column=3, sticky="w", padx=5)

        ctk.CTkLabel(display_frame, text="Phase (°):").grid(row=2, column=0, sticky="w", pady=10, padx=5)
        self.phase_var = tk.DoubleVar(value=0.0)
        ctk.CTkEntry(display_frame, textvariable=self.phase_var, width=80).grid(row=2, column=1, sticky="w", padx=5)

        ctk.CTkLabel(display_frame, text="R-Freq:").grid(row=2, column=2, sticky="w", pady=10, padx=5)
        self.right_freq_var = tk.DoubleVar(value=0.0)
        ctk.CTkEntry(display_frame, textvariable=self.right_freq_var, width=80).grid(row=2, column=3, sticky="w", padx=5)

        ctk.CTkLabel(display_frame, text="R-Phase:").grid(row=3, column=2, sticky="w", pady=10, padx=5)
        self.right_phase_var = tk.DoubleVar(value=0.0)
        ctk.CTkEntry(display_frame, textvariable=self.right_phase_var, width=80).grid(row=3, column=3, sticky="w", padx=5)

        # --- Launch Button ---
        self.launch_btn = ctk.CTkButton(main_frame, text="LAUNCH ENGINE", command=self.launch_engine, font=("Segoe UI", 12, "bold"), height=40)
        self.launch_btn.pack(fill="x", pady=20)

        ctk.CTkLabel(main_frame, text="Press ESC in the engine window to exit.", font=("Segoe UI", 10, "italic")).pack()

    def create_group_frame(self, parent, title):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)
        title_lbl = ctk.CTkLabel(frame, text=title, font=("Segoe UI", 13, "bold"))
        title_lbl.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 0))
        return frame

    def on_preset_change(self, choice):
        selection = choice
        if "Delta" in selection:
            self.freq_var.set(2.0)
        elif "Alpha" in selection:
            self.freq_var.set(10.0)
        elif "Beta" in selection:
            self.freq_var.set(20.0)
        elif "Gamma" in selection:
            self.freq_var.set(40.0)
        elif "High Gamma" in selection:
            self.freq_var.set(80.0)

    def launch_engine(self):
        # Construct arguments
        script_path = os.path.join(os.path.dirname(__file__), 'entrainment_engine.py')

        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Could not find engine script at:\n{script_path}")
            return

        cmd = [
            sys.executable,
            script_path,
            '--freq', str(self.freq_var.get()),
            '--waveform', self.waveform_var.get(),
            '--mode', self.mode_var.get(),
            '--duration', str(self.duration_var.get()),
            '--ramp', str(self.ramp_var.get()),
            '--sham', self.sham_var.get(),
            '--gamma', str(self.gamma_var.get()),
            '--brightness', str(self.brightness_var.get()),
            '--phase', str(self.phase_var.get()),
            '--phase-right', str(self.right_phase_var.get())
        ]

        # Only pass right freq if it's set (non-zero), otherwise engine defaults to main freq
        if self.right_freq_var.get() > 0:
            cmd.extend(['--freq-right', str(self.right_freq_var.get())])

        try:
            # Launch as a separate subprocess
            # We do not wait for it to finish, so the GUI remains responsive
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Launch Error", str(e))


if __name__ == "__main__":
    root = ctk.CTk()
    app = NeuroOpticLauncher(root)
    root.mainloop()