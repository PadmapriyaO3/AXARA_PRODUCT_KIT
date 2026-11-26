
import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import ScatterChart, Series, Reference

INPUT_FILE = "results/line_regulation_buck_raw.csv"
OUTPUT_FILE = "results/line_regulation_buck_results.xlsx"
PLOT_FILE = "results/plots/line_regulation_buck.png"

os.makedirs("results/plots", exist_ok=True)

measurements = []

with open(INPUT_FILE, "r", newline="") as file:

    reader = csv.DictReader(file)

    for row in reader:

        measurements.append({
            "Target_Vout": float(row["Target_Vout"]),
            "Input_Vin": float(row["Input_Vin"]),
            "Measured_Vout": float(row["Measured_Vout"])
        })

if not measurements:
    raise ValueError("No measurement data found in CSV file.")

grouped_data = defaultdict(list)

for row in measurements:

    grouped_data[row["Target_Vout"]].append(row)


for target in grouped_data:

    grouped_data[target].sort(
        key=lambda x: x["Input_Vin"]
    )

summary = []

for target, data in sorted(grouped_data.items()):

    vin_min = data[0]["Input_Vin"]
    vin_max = data[-1]["Input_Vin"]

    vout_min = data[0]["Measured_Vout"]
    vout_max = data[-1]["Measured_Vout"]

    delta_vin = vin_max - vin_min
    delta_vout = vout_max - vout_min

    # Output-voltage change per input-voltage change
    line_regulation_v_per_v = (delta_vout / delta_vin)*100

    summary.append({
        "Target_Vout": target,
        "Vin_Min": vin_min,
        "Vin_Max": vin_max,
        "Vout_Min": vout_min,
        "Vout_Max": vout_max,
        "Delta_Vout": delta_vout,
        "Line_Regulation_V_Per_V_%": line_regulation_v_per_v
    })

wb = Workbook()

# Raw data sheet
ws_raw = wb.active
ws_raw.title = "Raw Data"

headers = [
    "Target Vout (V)",
    "Input Vin (V)",
    "Measured Vout (V)"
]

ws_raw.append(headers)

for cell in ws_raw[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(
        start_color="305496",
        end_color="305496",
        fill_type="solid"
    )

for row in measurements:

    ws_raw.append([
        row["Target_Vout"],
        row["Input_Vin"],
        row["Measured_Vout"]
    ])


# Summary sheet
ws_summary = wb.create_sheet("Summary")

summary_headers = [
    "Target Vout (V)",
    "Vin Min (V)",
    "Vin Max (V)",
    "Vout Min (V)",
    "Vout Max (V)",
    "Delta Vout (V)",
    "Delta Vout / Delta Vin (%)"
]

ws_summary.append(summary_headers)

for cell in ws_summary[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(
        start_color="305496",
        end_color="305496",
        fill_type="solid"
    )

for row in summary:

    ws_summary.append([
        row["Target_Vout"],
        row["Vin_Min"],
        row["Vin_Max"],
        row["Vout_Min"],
        row["Vout_Max"],
        row["Delta_Vout"],
        row["Line_Regulation_V_Per_V_%"]
    ])

# CREATE EXCEL CHART

chart = ScatterChart()

chart.title = "Buck Converter Line Regulation"
chart.style = 13
chart.x_axis.title = "Input Voltage (V)"
chart.y_axis.title = "Measured Output Voltage (V)"
chart.height = 10
chart.width = 18

for target in sorted(grouped_data):

    target_rows = [
        i for i, row in enumerate(measurements, start=2)
        if row["Target_Vout"] == target
    ]

    if not target_rows:
        continue

    x_values = Reference(
        ws_raw,
        min_col=2,
        min_row=target_rows[0],
        max_row=target_rows[-1]
    )

    y_values = Reference(
        ws_raw,
        min_col=3,
        min_row=target_rows[0],
        max_row=target_rows[-1]
    )

    series = Series(
        y_values,
        x_values,
        title=f"Target Vout = {target} V"
    )

    series.graphicalProperties.line.solidFill = "4472C4"
    series.graphicalProperties.line.width = 25000

    chart.series.append(series)

ws_summary.add_chart(chart, "K2")

# FORMAT EXCEL SHEETS

for ws in [ws_raw, ws_summary]:

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for column in ws.columns:

        max_length = max(
            len(str(cell.value)) if cell.value is not None else 0
            for cell in column
        )

        ws.column_dimensions[
            column[0].column_letter
        ].width = max_length + 3

    for row in ws.iter_rows(min_row=2):

        for cell in row:
            cell.alignment = Alignment(horizontal="center")


wb.save(OUTPUT_FILE)

plt.figure(figsize=(10, 6))

for target, data in sorted(grouped_data.items()):

    vin = [row["Input_Vin"] for row in data]

    vout = [
        row["Measured_Vout"]
        for row in data
    ]

    plt.plot(
        vin,
        vout,
        marker="o",
        linewidth=2,
        label=f"Target Vout = {target} V"
    )

plt.title("Buck Converter Line Regulation")
plt.xlabel("Input Voltage (V)")
plt.ylabel("Measured Output Voltage (V)")

plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()

plt.savefig(PLOT_FILE, dpi=300)
plt.show()

print("\n========== LINE REGULATION RESULTS ==========\n")

for row in summary:

    print(
        f"Target Vout: {row['Target_Vout']:.3f} V | "
        f"Line Regulation: {row['Line_Regulation_V_Per_V_%']:.4f} % | "
    )

print("\nExcel file saved:", OUTPUT_FILE)
print("Plot saved:", PLOT_FILE)
print("\n -processing completed successfully.")
