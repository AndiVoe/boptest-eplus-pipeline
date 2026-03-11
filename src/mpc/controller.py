try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
import numpy as np

def optimize_trajectory_multizone_numpy(
    T_init_list: list, 
    T_out_forecast: np.ndarray, 
    Q_sol_forecast_list: list, 
    Q_int_forecast_list: list, 
    params_list: list,
    dt_seconds: float = 900.0,
    epochs: int = 100
) -> (list, list):
    """
    NumPy fallback for multi-zone optimization.
    Simply loops over zones and calls a single-zone optimizer for each.
    """
    n_zones = len(T_init_list)
    q_opts = []
    t_opts = []
    
    for i in range(n_zones):
        q, t = optimize_trajectory_numpy(
            T_init_list[i], T_out_forecast, Q_sol_forecast_list[i],
            Q_int_forecast_list[i], params_list[i], dt_seconds, epochs
        )
        q_opts.append(q)
        t_opts.append(t)
    
    return np.array(q_opts), np.array(t_opts)

def optimize_trajectory_numpy(
    T_init: float, 
    T_out_f: np.ndarray, 
    Q_sol_f: np.ndarray, 
    Q_int_f: np.ndarray, 
    params: dict,
    dt: float = 900.0,
    epochs: int = 150
) -> (np.ndarray, np.ndarray):
    horizon = len(T_out_f)
    R_env = params['R_env']
    R_vent = params.get('R_vent', 1e9) # Default to no ventilation if missing
    C_air = params['C_air']
    inv_R_eq = (1.0 / R_env) + (1.0 / R_vent)
    
    q_hvac = np.zeros(horizon)
    lr = 500.0
    alpha_energy = 1e-4
    beta_comfort = 100.0
    T_min = 21.0
    T_max = 24.0
    
    for _ in range(epochs):
        t_z = np.zeros(horizon)
        curr_t = T_init
        for i in range(horizon):
            q_tot = q_hvac[i] + Q_sol_f[i] + Q_int_f[i]
            dt_dt = ((T_out_f[i] - curr_t) * inv_R_eq + q_tot) / C_air
            curr_t = curr_t + dt_dt * dt
            t_z[i] = curr_t
            
        for i in range(horizon):
            grad_comfort = 0
            if t_z[i] < T_min:
                grad_comfort = -2 * (T_min - t_z[i]) * (dt / C_air)
            elif t_z[i] > T_max:
                grad_comfort = 2 * (t_z[i] - T_max) * (dt / C_air)
            grad_energy = 2 * q_hvac[i] * alpha_energy
            q_hvac[i] -= lr * (beta_comfort * grad_comfort + grad_energy)
            q_hvac[i] = np.clip(q_hvac[i], -15000, 15000)
            
    return q_hvac, t_z

def optimize_trajectory(
    T_init_list: list, 
    T_out_f: np.ndarray, 
    Q_sol_f_list: list, 
    Q_int_f_list: list, 
    params_list: list,
    dt: float = 900.0,
    epochs: int = 100
) -> (np.ndarray, np.ndarray):
    """
    Main entry point for multi-zone optimization.
    Args:
        T_init_list: List of initial temperatures for N zones.
        T_out_f: Shared outdoor temperature forecast (horizon).
        Q_sol_f_list: List of solar gain forecasts for N zones.
        Q_int_f_list: List of internal gain forecasts for N zones.
        params_list: List of dicts with R_env, R_vent, C_air for N zones.
    Returns:
        q_hvac_opt: (N_zones, horizon)
        t_z_opt: (N_zones, horizon)
    """
    if not HAS_TORCH:
        return optimize_trajectory_multizone_numpy(
            T_init_list, T_out_f, Q_sol_f_list, Q_int_f_list, params_list, dt, epochs
        )

    n_zones = len(T_init_list)
    horizon = len(T_out_f)

    # Vectorized RC Constants
    R_env = torch.tensor([p['R_env'] for p in params_list], dtype=torch.float32)
    R_vent = torch.tensor([p.get('R_vent', 1e9) for p in params_list], dtype=torch.float32)
    C_air = torch.tensor([p['C_air'] for p in params_list], dtype=torch.float32)
    inv_R_eq = (1.0 / R_env) + (1.0 / R_vent)

    class MultiZoneMPC(nn.Module):
        def __init__(self, n_zones, horizon):
            super().__init__()
            # Shape: (n_zones, horizon)
            self.w_hvac = nn.Parameter(torch.zeros(n_zones, horizon))
            self.Q_limit = 15000.0 

        def forward(self, T_init, T_out, Q_sol, Q_int):
            # Scale weights to power
            Q_hvac = torch.tanh(self.w_hvac) * self.Q_limit
            
            T_z = []
            T_curr = T_init # (n_zones,)
            for t in range(horizon):
                # Vectorized physics update for all zones simultaneously
                Q_tot = Q_hvac[:, t] + Q_sol[:, t] + Q_int[:, t]
                dT_dt = ((T_out[t] - T_curr) * inv_R_eq + Q_tot) / C_air
                T_next = T_curr + dT_dt * dt
                T_z.append(T_next)
                T_curr = T_next
            return torch.stack(T_z, dim=1), Q_hvac

    model = MultiZoneMPC(n_zones, horizon)
    
    # Inputs to Tensors
    T_init_t = torch.tensor(T_init_list, dtype=torch.float32)
    T_out_t = torch.tensor(T_out_f, dtype=torch.float32)
    Q_sol_t = torch.tensor(Q_sol_f_list, dtype=torch.float32)
    Q_int_t = torch.tensor(Q_int_f_list, dtype=torch.float32)
    
    optimizer = optim.Adam(model.parameters(), lr=0.1)
    
    for _ in range(epochs):
        optimizer.zero_grad()
        T_pred, Q_hvac = model(T_init_t, T_out_t, Q_sol_t, Q_int_t)
        
        # Aggregate Loss across zones and time
        cost_energy = torch.mean(Q_hvac ** 2)
        penalty_cold = torch.nn.functional.relu(21.0 - T_pred)
        penalty_hot = torch.nn.functional.relu(T_pred - 24.0)
        cost_comfort = torch.mean(penalty_cold ** 2 + penalty_hot ** 2)
        
        loss = 1e-4 * cost_energy + 100.0 * cost_comfort
        loss.backward()
        optimizer.step()
        
    with torch.no_grad():
        T_pred, Q_hvac = model(T_init_t, T_out_t, Q_sol_t, Q_int_t)
        return Q_hvac.numpy(), T_pred.numpy()

