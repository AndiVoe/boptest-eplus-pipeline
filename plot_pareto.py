import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def plot_pareto():
    csv_file = "data/results/sensitivity_results.csv"
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        return

    df = pd.read_csv(csv_file)
    if df.empty:
        print(f"Error: {csv_file} is empty.")
        return

    required = {'beta', 'energy_kWh', 'discomfort_Kh'}
    missing = required - set(df.columns)
    if missing:
        print(f"Error: missing required columns: {sorted(missing)}")
        return

    # Keep raw energy for diagnostics, but also plot absolute energy for more intuitive
    # Pareto interpretation when sign conventions produce negative values.
    df['energy_abs_kWh'] = df['energy_kWh'].abs()

    plt.figure(figsize=(10, 6))

    # Sort for line drawing
    df = df.sort_values('energy_abs_kWh')

    # Color points by original sign to preserve diagnostic information.
    colors = np.where(df['energy_kWh'] < 0, 'tab:red', 'tab:blue')
    plt.scatter(
        df['energy_abs_kWh'],
        df['discomfort_Kh'],
        c=colors,
        s=70,
        alpha=0.9,
        label='MPC points (color by raw energy sign)',
        zorder=3,
    )
    plt.plot(
        df['energy_abs_kWh'],
        df['discomfort_Kh'],
        '--',
        color='navy',
        alpha=0.7,
        label='Pareto trend (sorted by |energy|)',
        zorder=2,
    )

    # Annotate weights
    for _, row in df.iterrows():
        plt.annotate(
            f"β={row['beta']}\nE={row['energy_kWh']:.1f}",
            (row['energy_abs_kWh'], row['discomfort_Kh']),
            textcoords="offset points",
            xytext=(0, 10),
            ha='center',
            fontsize=8,
        )

    plt.title("Controller Sensitivity: Energy vs. Thermal Comfort (Pareto Frontier)", fontsize=14)
    plt.xlabel("Total Energy Magnitude |E| [kWh]", fontsize=12)
    plt.ylabel("Thermal Discomfort [Kh]", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    subtitle = (
        f"n={len(df)} | raw energy range={df['energy_kWh'].min():.1f}..{df['energy_kWh'].max():.1f} kWh | "
        f"discomfort range={df['discomfort_Kh'].min():.2f}..{df['discomfort_Kh'].max():.2f} Kh"
    )
    plt.gcf().text(0.5, 0.01, subtitle, ha='center', fontsize=9)
    
    # Aesthetic enhancements
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig("plots/pareto_frontier.png")
    print("Pareto plot saved to 'plots/pareto_frontier.png'")

if __name__ == "__main__":
    plot_pareto()
