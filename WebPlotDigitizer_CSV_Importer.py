import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import os

def process_csv_file():
    # GUI for file selection
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv")]
    )

    if not file_path:
        messagebox.showinfo("Cancelled", "No file selected.")
        return

    try:
        # Prompt for metadata
        filter_number = simpledialog.askstring("Filter Number", "Enter Filter Number:")
        filter_name = simpledialog.askstring("Filter Name", "Enter Filter Name:")
        hex_color = simpledialog.askstring("Hex Color", "Enter Hex Color (e.g., #FF0000):")

        if not all([filter_number, filter_name, hex_color]):
            messagebox.showerror("Missing Info", "All metadata fields must be filled.")
            return

        # Read CSV with semicolon separator, comma as decimal
        raw_data = pd.read_csv(file_path, sep=';', header=None, engine='python')
        if raw_data.shape[1] < 2:
            messagebox.showerror("Parse Error", "Could not read two columns from the CSV. Check format.")
            return

        # Convert strings with commas as decimals
        raw_data = raw_data.applymap(lambda x: float(str(x).replace(',', '.').strip()))
        wavelengths = raw_data.iloc[:, 0].values
        transmissions = raw_data.iloc[:, 1].values

        if len(wavelengths) == 0 or len(transmissions) == 0:
            messagebox.showerror("Empty Data", "Wavelength or transmission columns are empty.")
            return

        # Determine the 5nm step range, clamped to <= 1100nm
        min_wl = int(np.ceil(np.min(wavelengths) / 5.0)) * 5
        max_wl = min(1100, int(np.floor(np.max(wavelengths) / 5.0)) * 5)
        new_wavelengths = np.arange(min_wl, max_wl + 1, 5)

        # Interpolate and clamp
        interpolator = interp1d(wavelengths, transmissions, kind='linear', bounds_error=False)
        interpolated = interpolator(new_wavelengths)
        interpolated = np.clip(np.round(interpolated, 3), 0.0, None)

        # Build and save TSV
        output_df = pd.DataFrame(data=[interpolated], columns=new_wavelengths)
        output_df.insert(0, 'Filter Number', filter_number)
        output_df.insert(1, 'Filter Name', filter_name)
        output_df.insert(2, 'Hex Color', hex_color)

        out_path = os.path.splitext(file_path)[0] + "_interpolated.tsv"
        output_df.to_csv(out_path, sep='\t', index=False)

        messagebox.showinfo("Success", f"Interpolated TSV saved to:\n{out_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Something went wrong:\n{str(e)}")

if __name__ == "__main__":
    process_csv_file()
