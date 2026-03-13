import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_pareto():
    csv_file = "data/results/sensitivity_results.csv"
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        return

    df = pd.read_csv(csv_file)
    
    plt.figure(figsize=(10, 6))
    
    # Sort for line drawing
    df = df.sort_values('energy_kWh')
    
    plt.plot(df['energy_kWh'], df['discomfort_Kh'], 'o--', color='navy', label='MPC Pareto Frontier')
    
    # Annotate weights
    for idx, row in df.iterrows():
        plt.annotate(f"β={row['beta']}", (row['energy_kWh'], row['discomfort_Kh']), 
                     textcoords="offset points", xytext=(0,10), ha='center')

    plt.title("Controller Sensitivity: Energy vs. Thermal Comfort (Pareto Frontier)", fontsize=14)
    plt.xlabel("Total Energy Consumption [kWh]", fontsize=12)
    plt.ylabel("Thermal Discomfort [Kh]", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Aesthetic enhancements
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig("plots/pareto_frontier.png")
    print("✨ Pareto plot saved to 'plots/pareto_frontier.png'")

if __name__ == "__main__":
    plot_pareto()
