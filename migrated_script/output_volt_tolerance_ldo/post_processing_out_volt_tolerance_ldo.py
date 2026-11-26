
import csv
import os
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import ScatterChart, Series, Reference


def post_process(context, logger):

    # Common output directory
    results_dir = Path(
        os.environ.get(
            "AXARA_RESULTS_DIR",
            r"C:\Axa\Results"
        )
    )

    plots_dir = results_dir / "plots"

    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    INPUT_FILE = results_dir / "out_volt_tolerance_raw.csv"

    OUTPUT_FILE = results_dir / "out_volt_tolerance_results.xlsx"

    PLOT_FILE = plots_dir / "out_volt_tolerance.png"

    # Get measurement data from sequence context
    measurements = context.get("measurement_data")

    if not measurements:
        logger.error("No measurement data found in sequence context.")
        raise ValueError("No measurement data found in sequence context.")

    logger.info("Starting post-processing.")

    # --------------------------------------------------
    # SAVE RAW MEASUREMENT DATA TO CSV
    # --------------------------------------------------

    raw_headers = [
        "Target_Vout",
        "Input_Vin",
        "Measured_Vout"
    ]

    with open(INPUT_FILE, "w", newline="") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=raw_headers
        )

        writer.writeheader()
        writer.writerows(measurements)

    logger.info(f"Raw measurement data saved: {INPUT_FILE}")

    # --------------------------------------------------
    # CALCULATE SUMMARY
    # --------------------------------------------------

    summary = []

    for row in measurements:

        target = float(row["Target_Vout"])

        input_voltage = float(row["Input_Vin"])

        measured = float(row["Measured_Vout"])

        # Absolute output voltage error
        voltage_error = measured - target

        # Absolute error in mV
        voltage_error_mv = voltage_error * 1000

        # Output voltage accuracy error in percentage
        accuracy_error_percent = (
            voltage_error / target
        ) * 100

        summary.append({

            "Target_Vout": target,

            "Input_Vin": input_voltage,

            "Measured_Vout": measured,

            "Voltage_Error": voltage_error,

            "Voltage_Error_mV": voltage_error_mv,

            "Accuracy_Error_Percent": accuracy_error_percent

        })

    # --------------------------------------------------
    # CREATE EXCEL WORKBOOK
    # --------------------------------------------------

    wb = Workbook()

    # RAW DATA SHEET
    ws_raw = wb.active
    ws_raw.title = "Raw Data"

    raw_excel_headers = [
        "Target Vout (V)",
        "Input Vin (V)",
        "Measured Vout (V)"
    ]

    ws_raw.append(raw_excel_headers)

    for cell in ws_raw[1]:

        cell.font = Font(
            bold=True,
            color="FFFFFF"
        )

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

    # SUMMARY SHEET
    ws_summary = wb.create_sheet("Summary")

    summary_headers = [

        "Target Vout (V)",

        "Input Vin (V)",

        "Measured Vout (V)",

        "Voltage Error (V)",

        "Voltage Error (mV)",

        "Accuracy Error (%)"

    ]

    ws_summary.append(summary_headers)

    for cell in ws_summary[1]:

        cell.font = Font(
            bold=True,
            color="FFFFFF"
        )

        cell.fill = PatternFill(
            start_color="305496",
            end_color="305496",
            fill_type="solid"
        )

    for row in summary:

        ws_summary.append([

            row["Target_Vout"],

            row["Input_Vin"],

            row["Measured_Vout"],

            row["Voltage_Error"],

            row["Voltage_Error_mV"],

            row["Accuracy_Error_Percent"]

        ])

    # --------------------------------------------------
    # CREATE EXCEL SCATTER CHART
    # --------------------------------------------------

    chart = ScatterChart()

    chart.title = "LDO Output Voltage Tolerance"

    chart.style = 13

    chart.x_axis.title = "Target Output Voltage (V)"

    chart.y_axis.title = "Measured Output Voltage (V)"

    chart.height = 10
    chart.width = 18

    # Target voltage on X axis
    x_values = Reference(
        ws_summary,
        min_col=1,
        min_row=2,
        max_row=len(summary) + 1
    )

    # Measured voltage on Y axis
    y_values = Reference(
        ws_summary,
        min_col=3,
        min_row=2,
        max_row=len(summary) + 1
    )

    measured_series = Series(
        y_values,
        x_values,
        title="Measured Vout"
    )

    measured_series.graphicalProperties.line.solidFill = "4472C4"
    measured_series.graphicalProperties.line.width = 25000

    chart.series.append(measured_series)

    # Ideal output voltage reference line
    ideal_series = Series(
        x_values,
        x_values,
        title="Ideal Vout"
    )

    ideal_series.graphicalProperties.line.solidFill = "FF0000"
    ideal_series.graphicalProperties.line.width = 20000

    chart.series.append(ideal_series)

    ws_summary.add_chart(chart, "H2")

    # --------------------------------------------------
    # FORMAT EXCEL SHEETS
    # --------------------------------------------------

    for ws in [ws_raw, ws_summary]:

        ws.freeze_panes = "A2"

        ws.auto_filter.ref = ws.dimensions

        for column in ws.columns:

            max_length = max(

                len(str(cell.value))
                if cell.value is not None else 0

                for cell in column

            )

            ws.column_dimensions[
                column[0].column_letter
            ].width = max_length + 3

        for row in ws.iter_rows(min_row=2):

            for cell in row:

                cell.alignment = Alignment(
                    horizontal="center"
                )

    # Save Excel workbook
    wb.save(OUTPUT_FILE)

    logger.info(f"Excel results saved: {OUTPUT_FILE}")

    # --------------------------------------------------
    # CREATE PNG PLOT
    # --------------------------------------------------

    target_vout = [
        row["Target_Vout"]
        for row in summary
    ]

    measured_vout = [
        row["Measured_Vout"]
        for row in summary
    ]

    plt.figure(figsize=(9, 6))

    # Measured output voltage
    plt.plot(
        target_vout,
        measured_vout,
        marker="o",
        linewidth=2,
        markersize=8,
        label="Measured Vout"
    )

    # Ideal output voltage
    plt.plot(
        target_vout,
        target_vout,
        linestyle="--",
        linewidth=2,
        color="red",
        label="Ideal Vout"
    )

    plt.title("LDO Output Voltage Tolerance")

    plt.xlabel("Target Output Voltage (V)")

    plt.ylabel("Measured Output Voltage (V)")

    plt.grid(
        True,
        linestyle="--",
        alpha=0.6
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        PLOT_FILE,
        dpi=300
    )

    plt.close()

    logger.info(f"Plot saved: {PLOT_FILE}")

    # --------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------

    logger.info(
        "========== OUTPUT VOLTAGE TOLERANCE RESULTS =========="
    )

    for row in summary:

        logger.info(

            f"Target Vout: {row['Target_Vout']:.3f} V | "

            f"Measured Vout: {row['Measured_Vout']:.6f} V | "

            f"Voltage Error: {row['Voltage_Error_mV']:.3f} mV | "

            f"Accuracy Error: {row['Accuracy_Error_Percent']:.4f} %"

        )

    logger.info("Post-processing completed successfully.")
