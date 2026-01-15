import pandas as pd
import matplotlib.pyplot as plt
import io
import os
import re
from datetime import datetime

# ---------------- CONFIGURATION ----------------

INPUT_DIR = "data"
OUTPUT_DIR = "bqm_images"

FILENAME_REGEX = r"bqm-result-(\d{4}-\d{2}-\d{2})\.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------


def extract_date_from_filename(filename):
    match = re.match(FILENAME_REGEX, filename)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d")


def process_file(filepath, date):
    print(f"Processing {os.path.basename(filepath)}")

    df = pd.read_csv(filepath)

    # Parse timestamps
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    # Convert latency ns → ms
    for col in ["Min Latency (ns)", "Ave Latency (ns)", "Max Latency (ns)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 1_000_000

    # Packet loss %
    df["Sent Polls"] = pd.to_numeric(df["Sent Polls"], errors="coerce")
    df["Lost Polls"] = pd.to_numeric(df["Lost Polls"], errors="coerce").fillna(0)
    df["Packet Loss %"] = (df["Lost Polls"] / df["Sent Polls"]) * 100

    df = df.dropna(subset=["Timestamp"])

    plot_day(df, date)


def plot_day(df, date):
    fig, ax1 = plt.subplots(figsize=(16, 8))

    # Latency plots
    ax1.plot(df["Timestamp"], df["Min Latency (ns)"], color="green", label="Min Latency (ms)")
    ax1.plot(df["Timestamp"], df["Ave Latency (ns)"], color="blue", label="Avg Latency (ms)")
    ax1.plot(df["Timestamp"], df["Max Latency (ns)"], color="gold", label="Max Latency (ms)")

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Latency (ms)")
    ax1.grid(True)

    # Packet loss from top
    ax2 = ax1.twinx()
    ax2.fill_between(
        df["Timestamp"],
        df["Packet Loss %"],
        color="red",
        alpha=0.3,
        step="pre",
        label="Packet Loss (%)"
    )

    ax2.set_ylim(100, 0)
    ax2.set_ylabel("Packet Loss (%)")

    # Title & legend
    fig.suptitle(
        f"BQM Latency & Packet Loss — {date.strftime('%Y-%m-%d')}",
        fontsize=16
    )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    output_path = os.path.join(
        OUTPUT_DIR,
        f"bqm_{date.strftime('%Y-%m-%d')}.png"
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"Saved {output_path}")


def main():
    for filename in sorted(os.listdir(INPUT_DIR)):
        date = extract_date_from_filename(filename)
        if not date:
            continue

        filepath = os.path.join(INPUT_DIR, filename)

        try:
            process_file(filepath, date)
        except Exception as e:
            print(f"Failed {filename}: {e}")


if __name__ == "__main__":
    main()
