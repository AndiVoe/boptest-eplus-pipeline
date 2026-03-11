import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def train_id_model(csv_path="multizone_id_data.csv", dt=3600.0, epochs=200):
    df = pd.read_csv(csv_path)
    zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
    n_zones = len(zones)
    
    # Prepare Tensors (normalize temperatures to delta-T for stability)
    T_obs = torch.tensor(df[[f'T_{z}' for z in zones]].values, dtype=torch.float32) - 273.15
    T_out = torch.tensor(df['T_out'].values, dtype=torch.float32) - 273.15
    Q_sol = torch.tensor(df['Q_sol'].values, dtype=torch.float32) # Global horizontal
    
    # Define Learnable Parameters
    # We initialize with reasonable priors
    R_env = nn.Parameter(torch.ones(n_zones) * 0.1)
    C_air = nn.Parameter(torch.ones(n_zones) * 1e7)
    
    # Coupling Matrix (Symmetric)
    # We only learn upper triangle to ensure symmetry
    n_couplings = int(n_zones * (n_zones - 1) / 2)
    G_ij_flat = nn.Parameter(torch.full((n_couplings,), 0.1)) # Admittance G = 1/R
    
    optimizer = optim.Adam([R_env, C_air, G_ij_flat], lr=0.01)
    
    def get_L_ij(G_flat):
        G = torch.zeros(n_zones, n_zones)
        idx = 0
        for i in range(n_zones):
            for j in range(i + 1, n_zones):
                G[i, j] = G[j, i] = torch.abs(G_flat[idx]) # Admittance must be positive
                idx += 1
        row_sums = torch.sum(G, dim=1)
        return torch.diag(row_sums) - G

    print("Starting Multi-zone System ID...")
    for epoch in range(epochs):
        optimizer.zero_grad()
        
        # Simulation forward pass
        T_pred = []
        T_curr = T_obs[0]
        L_ij = get_L_ij(G_ij_flat)
        
        for t in range(len(T_obs) - 1):
            # Heat Balance: C dT/dt = (T_out - T)/R_env + Q_sol + Q_coupling
            Q_ext = (T_out[t] - T_curr) / torch.abs(R_env)
            Q_couple = -torch.mv(L_ij, T_curr)
            Q_sol_scaled = Q_sol[t] * 1.0 # Simple scaling for now
            
            dT_dt = (Q_ext + Q_sol_scaled + Q_couple) / torch.abs(C_air)
            T_next = T_curr + dT_dt * dt
            T_pred.append(T_next)
            T_curr = T_next
            
        T_pred_tensor = torch.stack(T_pred)
        loss = torch.mean((T_pred_tensor - T_obs[1:])**2)
        
        loss.backward()
        optimizer.step()
        
        if epoch % 20 == 0:
            print(f"Epoch {epoch}: Loss = {loss.item():.4f}")

    # Results extraction
    print("\nIdentified Parameters:")
    for i, z in enumerate(zones):
        print(f"Zone {z}: R_env={torch.abs(R_env[i]).item():.4f}, C_air={torch.abs(C_air[i]).item():.1e}")
    
    print("\nIdentified Coupling Matrix (G_ij):")
    L_ij = get_L_ij(G_ij_flat)
    print(L_ij.detach().numpy())

    # Save parameters to JSON
    import json
    results = {
        'zones': zones,
        'R_env': [torch.abs(R_env[i]).item() for i in range(n_zones)],
        'C_air': [torch.abs(C_air[i]).item() for i in range(n_zones)],
        'G_ij': L_ij.detach().numpy().tolist()
    }
    with open("identified_params.json", "w") as f:
        json.dump(results, f)
    print("Parameters saved to identified_params.json")

    # Plot Trajectory Comparison for the first 48h
    plt.figure(figsize=(12, 6))
    plt.plot(T_obs[:48, 4].numpy(), 'k--', label='Core Observed')
    plt.plot(torch.stack(T_pred)[:48, 4].detach().numpy(), 'r-', label='Core Predicted')
    plt.legend()
    plt.title("System ID: Zonal Temperature Matching (48h slice)")
    plt.savefig("system_id_convergence.png")
    print("Convergence plot saved as system_id_convergence.png")

if __name__ == "__main__":
    train_id_model()
