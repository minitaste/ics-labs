from influxdb_client import InfluxDBClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import threading
import time
import os
import signal


URL = "http://localhost:8086"
TOKEN = "Cx4O9S5lwjQpAoHyhGnJf7oer12WClou_YLTE3zcBIoGamO29wZEgOoaVjf6RZtuhYfHldnr8g08rURD7TGu6A=="
ORG = "iks"
BUCKET = "lab4_bucket"

client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
query_api = client.query_api()


# ── Anomaly generators ────────────────────────────────────────────────────────

def spike_cpu(duration=30):
    """Saturate all CPU cores for `duration` seconds using Python threads."""
    print(f"[anomaly] CPU spike starting ({duration}s)...")
    stop = threading.Event()

    def burn():
        while not stop.is_set():
            pass  # busy-loop

    workers = [threading.Thread(target=burn, daemon=True)
               for _ in range(os.cpu_count())]
    for w in workers:
        w.start()
    time.sleep(duration)
    stop.set()
    for w in workers:
        w.join()
    print("[anomaly] CPU spike done")


def spike_memory(size_mb=512, duration=30):
    """Allocate `size_mb` MB of RAM for `duration` seconds."""
    print(f"[anomaly] Memory spike starting ({size_mb} MB for {duration}s)...")
    blob = bytearray(size_mb * 1024 * 1024)
    time.sleep(duration)
    del blob
    print("[anomaly] Memory spike done")


def spike_network(iterations=10):
    """Download data repeatedly to spike bytes_recv on the network interface."""
    print(f"[anomaly] Network spike starting ({iterations} iterations)...")
    for i in range(iterations):
        try:
            subprocess.run(
                ["curl", "-s", "-o", "/dev/null",
                 "https://speed.cloudflare.com/__down?bytes=50000000"],
                check=True
            )
            print(f"[anomaly] Network iteration {i+1}/{iterations}")
        except subprocess.CalledProcessError as e:
            print(f"[anomaly] Network spike error: {e}")
    print("[anomaly] Network spike done")


def run_anomaly(kind: str):
    """
    Trigger an anomaly in a background thread so the script stays responsive.
    kind: 'cpu' | 'memory' | 'network' | 'all'
    """
    targets = {
        "cpu":     lambda: spike_cpu(duration=30),
        "memory":  lambda: spike_memory(size_mb=512, duration=30),
        "network": lambda: spike_network(iterations=10),
    }

    chosen = targets if kind == "all" else {kind: targets[kind]}

    threads = []
    for name, fn in chosen.items():
        t = threading.Thread(target=fn, name=name, daemon=True)
        t.start()
        threads.append(t)

    print(f"\n[anomaly] Waiting for spike(s) to finish...")
    for t in threads:
        t.join()

    # Give Telegraf time to collect and flush the metrics
    flush_wait = 25
    print(f"[anomaly] Waiting {flush_wait}s for Telegraf to flush metrics...")
    time.sleep(flush_wait)
    print("[anomaly] Done — running analysis now\n")


# ── InfluxDB helpers ──────────────────────────────────────────────────────────

def load_metric(query):
    result = query_api.query_data_frame(query)

    if isinstance(result, list):
        if len(result) == 0:
            print("No data returned")
            return None
        result = pd.concat(result, ignore_index=True)

    if result.empty:
        print("No data returned")
        return None

    df = result[["_time", "_value"]].copy()
    df.columns = ["time", "value"]
    df = df.sort_values("time").reset_index(drop=True)

    return df


def detect_anomalies(df, sigma=3):
    mean = df["value"].mean()
    std = df["value"].std()

    upper = mean + sigma * std
    lower = mean - sigma * std

    df = df.copy()
    df["anomaly"] = (df["value"] > upper) | (df["value"] < lower)

    return df, upper, lower


def plot_metric(df, upper, lower, title, filename):
    plt.figure(figsize=(12, 5))

    plt.plot(df["time"], df["value"], label="Value", linewidth=1)

    anomalies = df[df["anomaly"]]
    if not anomalies.empty:
        plt.scatter(anomalies["time"], anomalies["value"],
                    color="red", zorder=5, label=f"Anomaly ({len(anomalies)})")

    plt.axhline(upper, color="orange", linestyle="--",
                label=f"Upper (3σ): {upper:.2f}")
    plt.axhline(lower, color="orange", linestyle="--",
                label=f"Lower (3σ): {lower:.2f}")

    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"[plot] Saved → {filename}")


# ── Queries ───────────────────────────────────────────────────────────────────

def analyze():
    cpu = load_metric(f'''
from(bucket: "{BUCKET}")
  |> range(start: -12h)
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["_field"] == "usage_system")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
''')
    if cpu is not None:
        cpu, up, low = detect_anomalies(cpu)
        plot_metric(cpu, up, low, "CPU System Usage % — Anomaly Detection")

    mem = load_metric(f'''
from(bucket: "{BUCKET}")
  |> range(start: -12h)
  |> filter(fn: (r) => r._measurement == "mem")
  |> filter(fn: (r) => r._field == "used_percent")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
''')
    if mem is not None:
        mem, up, low = detect_anomalies(mem)
        plot_metric(mem, up, low, "Memory Used % — Anomaly Detection")

    net = load_metric(f'''
from(bucket: "{BUCKET}")
  |> range(start: -12h)
  |> filter(fn: (r) => r["_measurement"] == "net")
  |> filter(fn: (r) => r["_field"] == "bytes_recv")
  |> filter(fn: (r) => r["interface"] == "eth0")
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
''')
    if net is not None:
        net, up, low = detect_anomalies(net)
        plot_metric(net, up, low, "Network Receive Rate (bytes/s) — Anomaly Detection")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Change to "cpu", "memory", "network", or "all"
    run_anomaly("all")
    analyze()
