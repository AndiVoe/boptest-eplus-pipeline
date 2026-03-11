try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
import numpy as np

def optimize_trajectory_numpy(
    T_init_celsius: float, 
    T_out_forecast_celsius: np.ndarray, 
    Q_sol_forecast_watts: np.ndarray, 
    Q_int_forecast_watts: np.ndarray, 
    calibrated_params: dict,
    dt_seconds: float = 900.0,
    epochs: int = 150
) -> (np.ndarray, np.ndarray):
    """
    A pure NumPy implementation of the MPC optimization for 3R1C.
    Uses simple gradient descent to optimize the heating power trajectory.
    """
    horizon = len(T_out_forecast_celsius)
    R_env = calibrated_params['R_env']
    R_vent = calibrated_params['R_vent']
    C_air = calibrated_params['C_air']
    inv_R_eq = (1.0 / R_env) + (1.0 / R_vent)
    
    # Q_hvac trajectory initialization (all zeros)
    # Positive = Heating, Negative = Cooling
    q_hvac = np.zeros(horizon)
    lr = 500.0 # High LR for power in Watts
    
    alpha_energy = 1e-4
    beta_comfort = 100.0
    T_min = 21.0
    T_max = 24.0
    
    best_q = q_hvac.copy()
    best_t = np.zeros(horizon)
    
    for _ in range(epochs):
        # Forward pass (Euler)
        t_z = np.zeros(horizon)
        curr_t = T_init_celsius
        for i in range(horizon):
            q_tot = q_hvac[i] + Q_sol_forecast_watts[i] + Q_int_forecast_watts[i]
            dt_dt = ((T_out_forecast_celsius[i] - curr_t) * inv_R_eq + q_tot) / C_air
            curr_t = curr_t + dt_dt * dt_seconds
            t_z[i] = curr_t
            
        # Optimization: Numerical gradients
        for i in range(horizon):
            grad_comfort = 0
            if t_z[i] < T_min:
                grad_comfort = -2 * (T_min - t_z[i]) * (dt_seconds / C_air)
            elif t_z[i] > T_max:
                grad_comfort = 2 * (t_z[i] - T_max) * (dt_seconds / C_air)
                
            grad_energy = 2 * q_hvac[i] * alpha_energy
            
            q_hvac[i] -= lr * (beta_comfort * grad_comfort + grad_energy)
            # Clip between -10kW (cooling) and +10kW (heating)
            q_hvac[i] = np.clip(q_hvac[i], -10000, 10000)
            
        best_q = q_hvac
        best_t = t_z
        
    return best_q, best_t

def optimize_trajectory(
    T_init_celsius: float, 
    T_out_forecast_celsius: np.ndarray, 
    Q_sol_forecast_watts: np.ndarray, 
    Q_int_forecast_watts: np.ndarray, 
    calibrated_params: dict,
    dt_seconds: float = 900.0,
    epochs: int = 150
) -> (np.ndarray, np.ndarray):
    
    if not HAS_TORCH:
        return optimize_trajectory_numpy(
            T_init_celsius, T_out_forecast_celsius, Q_sol_forecast_watts, 
            Q_int_forecast_watts, calibrated_params, dt_seconds, epochs
        )

    # ... (Rest of the PyTorch implementation remains as a high-perf fallback)
    class DifferentiableMPC(nn.Module):
        def __init__(self, R_env: float, R_vent: float, C_air: float, dt_seconds: float, horizon_steps: int):
            super().__init__()
            self.R_env = R_env
            self.R_vent = R_vent
            self.C_air = C_air
            self.dt = dt_seconds
            self.horizon = horizon_steps
            self.Q_min = 0.0      
            self.Q_max = 10000.0  
            self.w_hvac = nn.Parameter(torch.zeros(self.horizon))

        def get_q_hvac(self) -> torch.Tensor:
            return self.Q_min + torch.sigmoid(self.w_hvac) * (self.Q_max - self.Q_min)

        def forward(self, T_init: torch.Tensor, T_out_forecast: torch.Tensor, Q_sol_forecast: torch.Tensor, Q_int_forecast: torch.Tensor):
            Q_hvac_seq = self.get_q_hvac()
            inv_R_eq = (1.0 / self.R_env) + (1.0 / self.R_vent)
            T_z = []
            T_current = T_init
            for t in range(self.horizon):
                Q_tot = Q_hvac_seq[t] + Q_sol_forecast[t] + Q_int_forecast[t]
                dT_dt = ((T_out_forecast[t] - T_current) * inv_R_eq + Q_tot) / self.C_air
                T_next = T_current + dT_dt * self.dt
                T_z.append(T_next)
                T_current = T_next
            return torch.stack(T_z), Q_hvac_seq

    horizon = len(T_out_forecast_celsius)
    mpc = DifferentiableMPC(calibrated_params['R_env'], calibrated_params['R_vent'], 
                            calibrated_params['C_air'], dt_seconds, horizon)
    
    T_init = torch.tensor(T_init_celsius, dtype=torch.float32)
    T_out = torch.tensor(T_out_forecast_celsius, dtype=torch.float32)
    Q_sol = torch.tensor(Q_sol_forecast_watts, dtype=torch.float32)
    Q_int = torch.tensor(Q_int_forecast_watts, dtype=torch.float32)
    
    optimizer = optim.Adam(mpc.parameters(), lr=0.5)
    
    for _ in range(epochs):
        optimizer.zero_grad()
        T_pred, Q_hvac = mpc(T_init, T_out, Q_sol, Q_int)
        cost_energy = torch.mean(Q_hvac ** 2)
        penalty_cold = torch.nn.functional.relu(20.0 - T_pred)
        penalty_hot = torch.nn.functional.relu(T_pred - 24.0)
        cost_comfort = torch.mean(penalty_cold ** 2 + penalty_hot ** 2)
        loss = 1e-4 * cost_energy + 100.0 * cost_comfort
        loss.backward()
        optimizer.step()
        
    with torch.no_grad():
        optimal_q_hvac = mpc.get_q_hvac().numpy()
        T_pred, _ = mpc(T_init, T_out, Q_sol, Q_int)
        optimal_t_pred = T_pred.numpy()
        
    return optimal_q_hvac, optimal_t_pred

