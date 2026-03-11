import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('mpc_results_multizone_office_simple_air.csv')
# Convert time to hours relative to start
df['hour'] = (df['time'] - df['time'].iloc[0]) / 3600

fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.plot(df['hour'], df['temp_avg'] - 273.15, 'r-', label='Avg Zone Temp (C)')
ax1.set_xlabel('Hours')
ax1.set_ylabel('Temperature (C)', color='r')
ax1.axhline(21, color='k', linestyle='--', alpha=0.3, label='Comfort Min')
ax1.axhline(24, color='k', linestyle='--', alpha=0.3, label='Comfort Max')
ax1.tick_params(axis='y', labelcolor='r')
ax1.legend(loc='upper left')

ax2 = ax1.twinx()
ax2.fill_between(df['hour'], df['p_total'], color='blue', alpha=0.2, label='Total HVAC Power (W)')
ax2.set_ylabel('Power (W)', color='b')
ax2.tick_params(axis='y', labelcolor='b')
ax2.legend(loc='upper right')

plt.title('Multi-zone Office MPC Benchmark (5 Zones - Chicago)')
plt.grid(True, alpha=0.3)
plt.savefig('multizone_office_bench_48h.png', dpi=300)
print("Plot saved as multizone_office_bench_48h.png")
