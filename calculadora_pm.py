"""
Calculadora Counts <-> Grados - Antena Batwing 3.8m (RC2000A)
================================================================

Modelos ajustados con datos reales del 25/04/2026 vs. efemerides JPL Horizons
(39 puntos dentro del rango de cobertura JPL).

AZIMUTH (muy preciso, sin histeresis significativa):
  cnt -> deg :  AZ_unwrap = A_az_f * cnt_AZ + B_az_f
  deg -> cnt :  cnt_AZ    = A_az_i * AZ_unwrap + B_az_i
  (AZ_unwrap puede ser negativo = AZ-360 para el lado oeste.
   AZ real 0-360 = AZ_unwrap modulo 360)

ELEVACION - existe histeresis mecanica real (~25-40 counts) entre subida
y bajada del actuador. Un mismo angulo EL corresponde a distintos counts
segun la direccion de aproximacion. Por eso:

  cnt -> deg :  EL = A_el_f * cnt_EL + B_el_f   (lineal, RMSE 0.14 grados)

  deg -> cnt :  se usa cnt_AZ (muy preciso) como parametro y se evalua
                un polinomio de grado 4: cnt_EL = poly4(cnt_AZ)
                Esto reduce el error de ~38 a ~22 counts (RMSE), porque
                usa la posicion real en la trayectoria solar de ese dia
                para resolver la ambiguedad subida/bajada.
                Valido para puntos sobre la trayectoria solar del
                25/04/2026 en el sitio calibrado. Fuera de eso, queda
                el fallback lineal directo EL->cnt (marcado impreciso).

Para correr:
    python calculadora_pm.py

Para convertir a .exe (Windows):
    pip install pyinstaller
    pyinstaller --onefile --windowed --name CalculadoraBatwing calculadora_pm.py
    (el .exe queda en la carpeta dist/)
"""

import tkinter as tk
from tkinter import ttk, messagebox

# --- MODELO AZIMUTH (lineal, ambas direcciones ajustadas directamente) ------

A_AZ_F = 0.04192258      # cnt -> deg
B_AZ_F = -95.9417

A_AZ_I = 23.853168        # deg -> cnt
B_AZ_I = 2288.5451

# --- MODELO ELEVACION (cnt->deg lineal; deg->cnt via AZ, poly grado 4) ------

A_EL_F = 0.00361259       # cnt -> deg
B_EL_F = 17.6215

# Fallback directo deg->cnt (impreciso por histeresis, RMSE ~38 cnt)
A_EL_I_FALLBACK = 276.208802
B_EL_I_FALLBACK = -4854.6800

# cnt_EL = poly4(cnt_AZ)  -- coeficientes [a4, a3, a2, a1, a0]
# (RMSE ~22 cnt, LOOCV ~26 cnt -- mejor metodo para deg->cnt)
POLY_EL_FROM_AZ = [
    -4.34362356e-10,
     3.98046692e-06,
    -1.62909857e-02,
     3.27967709e+01,
    -1.88266182e+04,
]

# --- CONVERSIONES ------------------------------------------------------------

def az_counts_to_deg(cnt_az: float) -> float:
    """Counts AZ -> grados azimuth real (0-360)."""
    az_unwrap = A_AZ_F * cnt_az + B_AZ_F
    return az_unwrap % 360.0

def az_deg_to_counts(az_deg: float) -> float:
    """Grados azimuth (0-360 o -180..180) -> counts AZ. (RMSE ~2 cnt)"""
    az = az_deg % 360.0
    if az > 180.0:
        az -= 360.0  # representacion -180..180 (igual que az_unwrap)
    return A_AZ_I * az + B_AZ_I

def el_counts_to_deg(cnt_el: float) -> float:
    """Counts EL -> grados elevacion. (RMSE ~0.14 grados)"""
    return A_EL_F * cnt_el + B_EL_F

def el_deg_to_counts_via_az(az_deg: float) -> float:
    """
    Grados azimuth -> counts EL, usando la trayectoria solar del 25/04/2026
    (cnt_EL = poly4(cnt_AZ)). RMSE ~22 cnt. Requiere que el punto (AZ,EL)
    corresponda a la posicion solar real de ese dia.
    """
    cnt_az = az_deg_to_counts(az_deg)
    return float(sum(c * cnt_az**i for i, c in enumerate(reversed(POLY_EL_FROM_AZ))))

def el_deg_to_counts_direct(el_deg: float) -> float:
    """
    Grados elevacion -> counts EL, ajuste directo EL->cnt.
    IMPRECISO: RMSE ~38 cnt, maximo ~76 cnt por histeresis mecanica.
    Usar solo si no se dispone de un AZ correspondiente a la trayectoria solar.
    """
    return A_EL_I_FALLBACK * el_deg + B_EL_I_FALLBACK

# ─── INTERFAZ ──────────────────────────────────────────────────────────────

class CalculadoraApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculadora Counts <-> Grados — Batwing 3.8m")
        self.geometry("520x600")
        self.resizable(False, False)
        self.configure(bg="#0f1318")

        self._build_styles()
        self._build_ui()

    # ── Estilos ──
    def _build_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#0f1318"
        panel = "#161c24"
        fg = "#c8d8e0"
        amber = "#e8a020"
        green = "#3ddc84"

        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=panel, foreground=fg, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=amber,
                        font=("Segoe UI", 13, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground="#8899a0",
                        font=("Segoe UI", 9))
        style.configure("Result.TLabel", background=panel, foreground=green,
                        font=("Consolas", 18, "bold"))
        style.configure("TEntry", font=("Consolas", 12), padding=6)
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(16, 8))

        self._colors = dict(bg=bg, panel=panel, fg=fg, amber=amber, green=green)

    # ── UI ──
    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(16, 4))
        ttk.Label(header, text="Calculadora Counts ↔ Grados", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Antena Batwing 3.8m · AZ lineal preciso · EL vía trayectoria solar",
                  style="Sub.TLabel").pack(anchor="w")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=10)

        tab_to_deg = ttk.Frame(notebook, style="TFrame")
        tab_to_cnt = ttk.Frame(notebook, style="TFrame")
        notebook.add(tab_to_deg, text="Counts → Grados")
        notebook.add(tab_to_cnt, text="Grados → Counts")

        self._build_counts_to_deg(tab_to_deg, pad)
        self._build_deg_to_counts(tab_to_cnt, pad)

        # Footer con coeficientes
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=16, pady=(0, 12))
        coef_text = (
            f"AZ cnt→deg: {A_AZ_F:.6f}·cnt+{B_AZ_F:.2f}   "
            f"EL cnt→deg: {A_EL_F:.6f}·cnt+{B_EL_F:.2f}\n"
            f"AZ deg→cnt: {A_AZ_I:.4f}·deg+{B_AZ_I:.1f}   "
            f"EL via AZ: poly4(cnt_AZ)"
        )
        ttk.Label(footer, text=coef_text, style="Sub.TLabel",
                  font=("Consolas", 8), justify="left").pack(anchor="w")

    # ── Tab 1: Counts -> Grados ──
    def _build_counts_to_deg(self, parent, pad):
        panel = ttk.Frame(parent, style="Panel.TFrame")
        panel.pack(fill="both", expand=True, padx=4, pady=4)

        ttk.Label(panel, text="Counts AZ", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w", **pad)
        self.in_cnt_az = ttk.Entry(panel, width=14)
        self.in_cnt_az.grid(row=0, column=1, **pad)
        self.in_cnt_az.insert(0, "2424")

        ttk.Label(panel, text="Counts EL", style="Panel.TLabel").grid(
            row=1, column=0, sticky="w", **pad)
        self.in_cnt_el = ttk.Entry(panel, width=14)
        self.in_cnt_el.grid(row=1, column=1, **pad)
        self.in_cnt_el.insert(0, "6684")

        ttk.Button(panel, text="▶ Calcular grados", command=self._calc_to_deg).grid(
            row=2, column=0, columnspan=2, pady=(10, 16))

        ttk.Separator(panel, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=16)

        ttk.Label(panel, text="AZIMUTH", style="Panel.TLabel").grid(
            row=4, column=0, sticky="w", padx=16, pady=(16, 0))
        self.out_az = ttk.Label(panel, text="—", style="Result.TLabel")
        self.out_az.grid(row=5, column=0, columnspan=2, sticky="w", padx=16)

        ttk.Label(panel, text="ELEVACIÓN", style="Panel.TLabel").grid(
            row=6, column=0, sticky="w", padx=16, pady=(16, 0))
        self.out_el = ttk.Label(panel, text="—", style="Result.TLabel")
        self.out_el.grid(row=7, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 16))

        for i in range(2):
            panel.columnconfigure(i, weight=1)

    def _calc_to_deg(self):
        try:
            cnt_az = float(self.in_cnt_az.get())
            cnt_el = float(self.in_cnt_el.get())
        except ValueError:
            messagebox.showerror("Error", "Ingresá valores numéricos válidos para los counts.")
            return

        az = az_counts_to_deg(cnt_az)
        el = el_counts_to_deg(cnt_el)

        self.out_az.config(text=f"{az:.3f}°")
        self.out_el.config(text=f"{el:.3f}°")

    # -- Tab 2: Grados -> Counts --
    def _build_deg_to_counts(self, parent, pad):
        panel = ttk.Frame(parent, style="Panel.TFrame")
        panel.pack(fill="both", expand=True, padx=4, pady=4)

        ttk.Label(panel, text="Azimuth [0°-360°]", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w", **pad)
        self.in_az = ttk.Entry(panel, width=14)
        self.in_az.grid(row=0, column=1, **pad)
        self.in_az.insert(0, "5.70")

        ttk.Label(panel, text="Elevación [°] (opcional)", style="Panel.TLabel").grid(
            row=1, column=0, sticky="w", **pad)
        self.in_el = ttk.Entry(panel, width=14)
        self.in_el.grid(row=1, column=1, **pad)
        self.in_el.insert(0, "")

        ttk.Button(panel, text="▶ Calcular counts", command=self._calc_to_counts).grid(
            row=2, column=0, columnspan=2, pady=(10, 14))

        ttk.Separator(panel, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=16)

        ttk.Label(panel, text="COUNTS AZ", style="Panel.TLabel").grid(
            row=4, column=0, sticky="w", padx=16, pady=(14, 0))
        self.out_cnt_az = ttk.Label(panel, text="—", style="Result.TLabel")
        self.out_cnt_az.grid(row=5, column=0, columnspan=2, sticky="w", padx=16)

        ttk.Label(panel, text="COUNTS EL  (vía AZ, ±22 cnt típico)", style="Panel.TLabel").grid(
            row=6, column=0, sticky="w", padx=16, pady=(14, 0))
        self.out_cnt_el = ttk.Label(panel, text="—", style="Result.TLabel")
        self.out_cnt_el.grid(row=7, column=0, columnspan=2, sticky="w", padx=16)

        self.out_cnt_el_fallback_lbl = ttk.Label(
            panel, text="COUNTS EL  (directo desde EL°, ±38 cnt — solo si EL no es de hoy)",
            style="Panel.TLabel", font=("Segoe UI", 8))
        self.out_cnt_el_fallback_lbl.grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 0))
        self.out_cnt_el_fallback = ttk.Label(panel, text="—", style="Panel.TLabel",
                                              font=("Consolas", 13, "bold"))
        self.out_cnt_el_fallback.grid(row=9, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12))

        for i in range(2):
            panel.columnconfigure(i, weight=1)

        note = ttk.Label(
            panel,
            text="El método principal (vía AZ) usa la trayectoria solar real\n"
                 "del 25/04/2026 para resolver la histéresis del eje de\n"
                 "elevación (~25-40 cnt entre subida y bajada). Es el más\n"
                 "preciso para apuntar al sol ese día. El campo Elevación\n"
                 "es opcional y solo se usa para el cálculo 'directo'.\n\n"
                 "Rango calibrado: AZ ≈ -40° a 42° (unwrap), EL ≈ 31°-42°.\n"
                 "Fuera de ese rango, ambos métodos extrapolan.",
            style="Sub.TLabel", justify="left", font=("Segoe UI", 8)
        )
        note.grid(row=10, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 12))

    def _calc_to_counts(self):
        try:
            az_deg = float(self.in_az.get())
        except ValueError:
            messagebox.showerror("Error", "Ingresá un valor numérico válido para el azimuth.")
            return

        cnt_az = az_deg_to_counts(az_deg)
        cnt_el_via_az = el_deg_to_counts_via_az(az_deg)

        self.out_cnt_az.config(text=f"{cnt_az:.0f}")
        self.out_cnt_el.config(text=f"{cnt_el_via_az:.0f}")

        el_text = self.in_el.get().strip()
        if el_text:
            try:
                el_deg = float(el_text)
                cnt_el_direct = el_deg_to_counts_direct(el_deg)
                self.out_cnt_el_fallback.config(text=f"{cnt_el_direct:.0f}")
            except ValueError:
                messagebox.showerror("Error", "El valor de Elevación no es numérico.")
                return
        else:
            self.out_cnt_el_fallback.config(text="—")


if __name__ == "__main__":
    app = CalculadoraApp()
    app.mainloop()
