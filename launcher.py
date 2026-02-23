import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class NeuroOpticLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("NeuroOptic Controller")
        self.root.geometry("450x600")
        self.root.resizable(False, False)

        # Styles
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))

        # --- Header ---
        header = ttk.Label(root, text="Visual Entrainment Engine", font=("Segoe UI", 14, "bold"))
        header.pack(pady=15)

        # --- Main Container ---
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Frequency Section ---
        freq_frame = ttk.LabelFrame(main_frame, text="Frequency Configuration", padding="10")
        freq_frame.pack(fill=tk.X, pady=5)

        ttk.Label(freq_frame, text="Preset Band:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.preset_var = tk.StringVar(value="Custom")
        self.preset_combo = ttk.Combobox(freq_frame, textvariable=self.preset_var, state="readonly")
        self.preset_combo['values'] = ('Custom', 'Delta (2Hz)', 'Alpha (10Hz)', 'Beta (20Hz)', 'Gamma (40Hz)', 'High Gamma (80Hz)')
        self.preset_combo.grid(row=0, column=1, sticky=tk.E, padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_change)

        ttk.Label(freq_frame, text="Target Frequency (Hz):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.freq_var = tk.DoubleVar(value=40.0)
        self.freq_entry = ttk.Entry(freq_frame, textvariable=self.freq_var)
        self.freq_entry.grid(row=1, column=1, sticky=tk.E, padx=5)

        ttk.Label(freq_frame, text="Waveform:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.waveform_var = tk.StringVar(value="sine")
        self.waveform_combo = ttk.Combobox(freq_frame, textvariable=self.waveform_var, state="readonly")
        self.waveform_combo['values'] = ('sine', 'square', 'am', 'triangle')
        self.waveform_combo.grid(row=2, column=1, sticky=tk.E, padx=5)

        # --- Visual Mode Section ---
        vis_frame = ttk.LabelFrame(main_frame, text="Visual Stimulation Mode", padding="10")
        vis_frame.pack(fill=tk.X, pady=10)

        ttk.Label(vis_frame, text="Mode:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.mode_var = tk.StringVar(value="full")
        self.mode_combo = ttk.Combobox(vis_frame, textvariable=self.mode_var, state="readonly")
        self.mode_combo['values'] = (
            'full', 'ring', 
            'left', 'right', 
            'quad_tl', 'quad_tr', 'quad_bl', 'quad_br'
        )
        self.mode_combo.grid(row=0, column=1, sticky=tk.E, padx=5)

        # --- Session Control ---
        session_frame = ttk.LabelFrame(main_frame, text="Session Control", padding="10")
        session_frame.pack(fill=tk.X, pady=5)

        ttk.Label(session_frame, text="Duration (sec, 0=Inf):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.duration_var = tk.DoubleVar(value=0.0)
        ttk.Entry(session_frame, textvariable=self.duration_var).grid(row=0, column=1, sticky=tk.E, padx=5)

        ttk.Label(session_frame, text="Ramp Up (sec):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ramp_var = tk.DoubleVar(value=0.0)
        ttk.Entry(session_frame, textvariable=self.ramp_var).grid(row=1, column=1, sticky=tk.E, padx=5)

        # --- Research / Sham ---
        sham_frame = ttk.LabelFrame(main_frame, text="Research / Sham Control", padding="10")
        sham_frame.pack(fill=tk.X, pady=10)

        ttk.Label(sham_frame, text="Sham Condition:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.sham_var = tk.StringVar(value="none")
        self.sham_combo = ttk.Combobox(sham_frame, textvariable=self.sham_var, state="readonly")
        self.sham_combo['values'] = ('none', 'detune', 'low_amp', 'jitter', 'static')
        self.sham_combo.grid(row=0, column=1, sticky=tk.E, padx=5)

        # --- Display & Phase ---
        display_frame = ttk.LabelFrame(main_frame, text="Display & Phase", padding="10")
        display_frame.pack(fill=tk.X, pady=5)

        ttk.Label(display_frame, text="Gamma (e.g. 2.2):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.gamma_var = tk.DoubleVar(value=1.0)
        ttk.Entry(display_frame, textvariable=self.gamma_var, width=10).grid(row=0, column=1, sticky=tk.E, padx=5)

        ttk.Label(display_frame, text="Brightness (0-1):").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10,0))
        self.brightness_var = tk.DoubleVar(value=1.0)
        ttk.Entry(display_frame, textvariable=self.brightness_var, width=10).grid(row=0, column=3, sticky=tk.E, padx=5)

        ttk.Label(display_frame, text="Phase Offset (°):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.phase_var = tk.DoubleVar(value=0.0)
        ttk.Entry(display_frame, textvariable=self.phase_var, width=10).grid(row=1, column=1, sticky=tk.E, padx=5)

        # --- Launch Button ---
        self.launch_btn = ttk.Button(main_frame, text="LAUNCH ENGINE", command=self.launch_engine)
        self.launch_btn.pack(fill=tk.X, pady=20, ipady=10)

        ttk.Label(main_frame, text="Press ESC in the engine window to exit.", font=("Segoe UI", 8, "italic")).pack()

    def on_preset_change(self, event):
        selection = self.preset_var.get()
        if "Delta" in selection: self.freq_var.set(2.0)
        elif "Alpha" in selection: self.freq_var.set(10.0)
        elif "Beta" in selection: self.freq_var.set(20.0)
        elif "Gamma" in selection: self.freq_var.set(40.0)
        elif "High Gamma" in selection: self.freq_var.set(80.0)

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
            '--phase', str(self.phase_var.get())
        ]

        try:
            # Launch as a separate subprocess
            # We do not wait for it to finish, so the GUI remains responsive
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Launch Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = NeuroOpticLauncher(root)
    root.mainloop()