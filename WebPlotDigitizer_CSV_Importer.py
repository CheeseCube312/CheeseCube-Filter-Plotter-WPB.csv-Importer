import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import os

def safe_float(val):
    """
    Convert a value to float, replacing commas with dots.
    Returns np.nan if conversion fails.
    """
    try:
        return float(str(val).replace(',', '.').strip())
    except Exception:
        return np.nan


def process_csv_file():
    # Initialize and hide main window
    root = tk.Tk()
    root.withdraw()

    # Ask user for CSV file
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
        filter_name   = simpledialog.askstring("Filter Name",   "Enter Filter Name:")
        manufacturer  = simpledialog.askstring("Manufacturer", "Enter Manufacturer:")
        hex_color     = simpledialog.askstring("Hex Color",    "Enter Hex Color (e.g., #FF0000):")

        # Normalize and validate metadata
        if hex_color:
            hex_color = hex_color.strip()
            if not hex_color.startswith('#'):
                hex_color = '#' + hex_color
        if not all([filter_number, filter_name, manufacturer, hex_color]):
            messagebox.showerror("Missing Info", "All metadata fields must be filled.")
            return

        # Read CSV with semicolon separator, no header
        raw_data = pd.read_csv(file_path, sep=';', header=None, engine='python')
        if raw_data.shape[1] < 2:
            messagebox.showerror("Parse Error", "Could not read two columns from the CSV. Check format.")
            return

        # Convert all entries safely to floats
        raw_data = raw_data.apply(lambda col: col.map(safe_float))
        wavelengths = raw_data.iloc[:, 0].dropna().values
        transmissions = raw_data.iloc[:, 1].dropna().values

        if wavelengths.size == 0 or transmissions.size == 0:
            messagebox.showerror("Empty Data", "Wavelength or transmission columns are empty.")
            return

        # Ensure data sorted by wavelength
        sort_idx = np.argsort(wavelengths)
        wavelengths = wavelengths[sort_idx]
        transmissions = transmissions[sort_idx]

        # Base wavelength bounds rounded to 5nm
        base_min = int(np.ceil(wavelengths.min() / 5.0)) * 5
        base_max = int(np.floor(wavelengths.max() / 5.0)) * 5

        # Ask user if they want upper flat extrapolation
        extrap_upper = messagebox.askyesno(
            "Extrapolation (High)",
            "Extrapolate missing values up to 1100nm using flat extension?"
        )
        # Ask user if they want lower flat extrapolation
        extrap_lower = messagebox.askyesno(
            "Extrapolation (Low)",
            "Extrapolate missing values down to 300nm using flat extension?"
        )

        # Determine final range
        min_wl = 300 if extrap_lower else base_min
        max_wl = 1100 if extrap_upper else min(1100, base_max)
        if min_wl > max_wl:
            messagebox.showerror("Range Error", "Data range is outside allowable bounds.")
            return

        # Create new wavelength array
        new_wavelengths = np.arange(min_wl, max_wl + 1, 5)

        # Create interpolator with NaN fill
        interpolator = interp1d(
            wavelengths,
            transmissions,
            kind='linear',
            bounds_error=False,
            fill_value=np.nan
        )
        interpolated = interpolator(new_wavelengths)

        # Manual flat extrapolation if requested
        if extrap_lower:
            below_mask = new_wavelengths < wavelengths.min()
            interpolated[below_mask] = transmissions[0]
        if extrap_upper:
            above_mask = new_wavelengths > wavelengths.max()
            interpolated[above_mask] = transmissions[-1]

        # Round and clamp negatives to zero
        interpolated = np.clip(np.round(interpolated, 3), 0.0, None)

        # Build output DataFrame
        output_df = pd.DataFrame([interpolated], columns=new_wavelengths)
        output_df.insert(0, 'Filter Number', filter_number)
        output_df.insert(1, 'Filter Name', filter_name)
        output_df.insert(2, 'Manufacturer', manufacturer)
        output_df.insert(3, 'Hex Color', hex_color)

        # Construct sanitized base filename
        base = f"{manufacturer}_{filter_number}_{filter_name}"
        sanitized = ''.join(c for c in base if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')

        # Build extrapolation suffix
        suffix_parts = []
        if extrap_lower:
            suffix_parts.append('300')
        if extrap_upper:
            suffix_parts.append('1100')
        if suffix_parts:
            suffix = 'extrapolated_' + '_'.join(suffix_parts)
            out_name = f"{sanitized}_{suffix}.tsv"
        else:
            out_name = f"{sanitized}.tsv"

        out_path = os.path.join(os.path.dirname(file_path), out_name)

        # Save TSV
        output_df.to_csv(out_path, sep='\t', index=False)

        messagebox.showinfo("Success", f"Interpolated TSV saved to:\n{out_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Something went wrong:\n{str(e)}")

if __name__ == "__main__":
    process_csv_file()
