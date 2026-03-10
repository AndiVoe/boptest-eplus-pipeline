#!/usr/bin/env python3
"""
MS3.3: PyTorch RC Calibration Engine (Engine B)
Implements an explicit Euler forward-pass simulator for a 3R1C RC thermal network using Differentiable Physics.
Uses torch.optim.Adam to backpropagate through the ODE steps to calibrate parameters.
"""
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from pathlib import Path
from src.rc_model.data_loader import load_calibration_data

class TorchRCModel3R1C(nn.Module):
    def __init__(self, dt_seconds: float, bounds: dict):
        super().__init__()
        self.dt = dt_seconds
        
        # Physical parameter bounds
        self.bounds = bounds
        
        # We optimize log(R) and log(C) to natively enforce strict positivity,
        # or use sigmoid scaling to bound them strictly between min and max.
        # Let's use sigmoid scaling to bound parameters: param = min + sigmoid(w) * (max - min)
        
        # Initialize raw weights for the optimizer
        self.w_R_env = nn.Parameter(torch.tensor(0.0))
        self.w_R_int = nn.Parameter(torch.tensor(0.0))
        self.w_R_vent = nn.Parameter(torch.tensor(0.0))
        self.w_C_air = nn.Parameter(torch.tensor(0.0))

    def _get_scaled_param(self, w: torch.Tensor, name: str) -> torch.Tensor:
        b_min, b_max = self.bounds[name]
        return b_min + torch.sigmoid(w) * (b_max - b_min)

    def get_physical_parameters(self):
        """Returns the physical values of the bounded parameters."""
        R_env = self._get_scaled_param(self.w_R_env, 'R_env')
        R_int = self._get_scaled_param(self.w_R_int, 'R_int')
        R_vent = self._get_scaled_param(self.w_R_vent, 'R_vent')
        C_air = self._get_scaled_param(self.w_C_air, 'C_air')
        return R_env, R_int, R_vent, C_air

    def forward(self, T_init: torch.Tensor, inputs: torch.Tensor) -> torch.Tensor:
        """
        Differentiable Explicit Euler solver.
        inputs shape: (Seq_len, 4) -> [T_out, Q_hvac, Q_sol, Q_int]
        """
        R_env, _, R_vent, C_air = self.get_physical_parameters()
        
        N = inputs.shape[0]
        T_z = [T_init]
        
        # Differentiable equivalent resistance
        inv_R_eq = (1.0 / R_env) + (1.0 / R_vent)
        
        T_current = T_init
        
        # Autograd rolls out the sequence
        for t in range(N - 1):
            T_out_t = inputs[t, 0]
            Q_hvac_t = inputs[t, 1]
            Q_sol_t = inputs[t, 2]
            Q_int_t = inputs[t, 3]

            Q_tot = Q_hvac_t + Q_sol_t + Q_int_t
            dT_dt = ((T_out_t - T_current) * inv_R_eq + Q_tot) / C_air
            
            T_next = T_current + dT_dt * self.dt
            T_z.append(T_next)
            T_current = T_next
            
        return torch.stack(T_z)

def calibrate_torch(data: pd.DataFrame, template_path: Path):
    """Runs Adam optimizer through the differentiable physics engine."""
    print("--- Engine B: PyTorch Adam Calibration ---")
    
    with open(template_path, 'r') as f:
        template = json.load(f)
    
    zone_id = list(template['zones'].keys())[0]
    zone_params = template['zones'][zone_id]['parameters']
    
    bounds = {
        'R_env': zone_params['R_env']['bounds'],
        'R_int': zone_params['R_int']['bounds'],
        'R_vent': zone_params['R_vent']['bounds'],
        'C_air': zone_params['C_air']['bounds']
    }
    
    dt = data['seconds_from_start'].diff().mode()[0]
    inputs_np = data[['T_out', 'Q_hvac', 'Q_sol', 'Q_int']].values
    targets_np = data['T_z'].values
    
    # Convert to PyTorch tensors
    inputs = torch.tensor(inputs_np, dtype=torch.float32)
    targets = torch.tensor(targets_np, dtype=torch.float32)
    T_init = targets[0].clone()
    
    model = TorchRCModel3R1C(dt_seconds=dt, bounds=bounds)
    optimizer = optim.Adam(model.parameters(), lr=0.1)
    loss_fn = nn.MSELoss()
    
    import time
    start_time = time.time()
    
    epochs = 1000
    final_loss = 0.0
    
    for epoch in range(epochs):
        optimizer.zero_grad()
        
        # Forward pass (unrolls the ODE)
        T_pred = model(T_init, inputs)
        
        # Compute loss
        loss = loss_fn(T_pred, targets)
        
        # Backpropagate through time
        loss.backward()
        optimizer.step()
        
        final_loss = loss.item()
        
    train_time = time.time() - start_time
    
    print(f"Calibration finished in {train_time:.3f} seconds.")
    print(f"Final MSE: {final_loss:.4f}")
    
    # Extract learned physical parameters
    with torch.no_grad():
        R_env, R_int, R_vent, C_air = model.get_physical_parameters()
    
    print(f"Calibrated R_env:  {R_env.item():.4f} K/W (Bounds: {bounds['R_env']})")
    print(f"Calibrated R_int:  {R_int.item():.4f} K/W (Bounds: {bounds['R_int']})")
    print(f"Calibrated R_vent: {R_vent.item():.4f} K/W (Bounds: {bounds['R_vent']})")
    print(f"Calibrated C_air:  {C_air.item():.0f} J/K (Bounds: {bounds['C_air']})")
    
    # Return as standard float list
    return [R_env.item(), R_int.item(), R_vent.item(), C_air.item()], final_loss, train_time

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    csv_file = project_root / "data" / "results" / "boptest_baseline_bestest_air.csv"
    template_file = project_root / "data" / "models" / "rc_3r1c_template.json"
    
    df = load_calibration_data(csv_file)
    calibrate_torch(df, template_file)
