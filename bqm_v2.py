from tracemalloc import start
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import re
from datetime import datetime

# ---------------- CONFIG ----------------

INPUT_DIR = "data"
OUTPUT_DIR = "bqm_images"

FILENAME_REGEX = r"bqm-result-(\d{4}-\d{2}-\d{2})\.csv"

PACKET_LOSS_OUTAGE_THRESHOLD = 20.0   # %
LATENCY_SPIKE_THRESHOLD_MS = 200     # ms
USE_LOG_SCALE = False

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------------------


def extract_date(filename):
    match = re.match(FILENAME_REGEX, filename)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d")


def process_file(path, date):
    df = pd.read_csv(path)

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

    # ---------------- LATENCY FILLS ----------------

    ax1.fill_between(
        df["Timestamp"],
        df["Min Latency (ns)"],
        df["Ave Latency (ns)"],
        color="green",
        alpha=0.15,
        label="Min → Avg"
    )

    ax1.fill_between(
        df["Timestamp"],
        df["Ave Latency (ns)"],
        df["Max Latency (ns)"],
        color="blue",
        alpha=0.15,
        label="Avg → Max"
    )

    # ---------------- LATENCY LINES ----------------

    ax1.plot(
        df["Timestamp"],
        df["Min Latency (ns)"],
        color="green",
        linewidth=1.2,
        label="Min Latency"
    )

    ax1.plot(
        df["Timestamp"],
        df["Ave Latency (ns)"],
        color="blue",
        linewidth=1.4,
        label="Avg Latency"
    )

    ax1.plot(
        df["Timestamp"],
        df["Max Latency (ns)"],
        color="gold",
        linewidth=1.2,
        label="Max Latency"
    )

    # Highlight extreme latency spikes
    spike_mask = df["Max Latency (ns)"] > LATENCY_SPIKE_THRESHOLD_MS
    ax1.scatter(
        df.loc[spike_mask, "Timestamp"],
        df.loc[spike_mask, "Max Latency (ns)"],
        color="red",
        s=10,
        zorder=5,
        label="Latency Spike"
    )

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Latency (ms)")

    ax1.set_xlim(
        df["Timestamp"].dt.normalize().iloc[0],
        df["Timestamp"].dt.normalize().iloc[0] + pd.Timedelta(days=1)
    )
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax1.xaxis.set_minor_locator(mdates.MinuteLocator(interval=10))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")

    ax1.grid(True, which="both", linestyle="--", alpha=0.4)

    if USE_LOG_SCALE:
        ax1.set_yscale("log")

    # ---------------- PACKET LOSS ----------------

    ax2 = ax1.twinx()

    ax2.fill_between(
        df["Timestamp"],
        df["Packet Loss %"],
        color="red",
        alpha=0.30,
        step="pre",
        label="Packet Loss (%)"
    )

    ax2.set_ylim(100, 0)
    ax2.set_ylabel("Packet Loss (%)")

    # Shade outage periods
    outage = df["Packet Loss %"] >= PACKET_LOSS_OUTAGE_THRESHOLD
    ax2.fill_between(
        df["Timestamp"],
        100,
        0,
        where=outage,
        color="darkred",
        alpha=0.12,
        step="pre",
        label="Outage"
    )

    # ---------------- TITLE & LEGEND ----------------

    fig.suptitle(
        f"BQM Latency & Packet Loss — {date.strftime('%Y-%m-%d')}",
        fontsize=16
    )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=9
    )

    # ---------------- SAVE ----------------

    output = os.path.join(
        OUTPUT_DIR,
        f"bqm_{date.strftime('%Y-%m-%d')}.png"
    )

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()

    print(f"Saved {output}")


def main():
    for filename in sorted(os.listdir(INPUT_DIR)):
        date = extract_date(filename)
        if not date:
            continue

        try:
            process_file(os.path.join(INPUT_DIR, filename), date)
        except Exception as e:
            print(f"Failed {filename}: {e}")


if __name__ == "__main__":
    main()

