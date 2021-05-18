# Ice Performance Calculation Script
# Karl Heine, 11/2020
# This function calculates the maximum ice discharge rate
# Ref. E+ Engineering Reference, section 15.1.2, (p. 791 in v. 9.1.0)

## Import
import sys
import numpy as np
import plotly.graph_objects as go
from curves import QuadLin

## Variable Definitions
# DTlm = Log-mean temperature difference
# DTlm_nom = Nominal log-mean temperature difference
# P
# q_d = Maximum heat tranfer rate for discharging (load)
# q_star = Normalized heat transfer rate limit into/out of ice tank
# Q_nom = Nominal capacity of the ice tank (energy units, NOT power)
# soc = State of charge (0-1)
# Te_o = Temp of water leaving the evaporator
# Tf = Freezing temp of storage medium
# Ti_i = Temp of water entering (in) the ice tank heat exchanger
# Ti_o = Temp of water leaving (out) the ice tank heat exchanger
# Tl_s = Temp of loop (setpoint)
# ts = timestep from regression data (3600s)


## Set Inputs
m_dot = 48.2        #kg/s
cp = 4179.6         #J/kg-K
DTlm_nom = 10       #C
Q_nom = 10000        #kWh(thermal)
soc = np.linspace(0,1,100)  #[-]
Tf = 0              #C
Tl_s = 6.667        #C
ts = 3600           #s


Tdb = 35            #C
Te_i = 11.05        #C
Ti_o = Tl_s         #C - Must equal loop setpoint temperature
Ti_i = np.linspace(Te_i, Ti_o+0.5, 100)     #C
#Ti_i = 11.05

## Max Ice Rate of DISCHARGE

# Get DTlm
DTlm = (Ti_i - Ti_o) / np.log((Ti_i - Tf) / (Ti_o - Tf)) / DTlm_nom

# Get q_star
coeffs = [0, 0.09, -0.15, 0.612, -0.324, -0.216]
q_star = []

# Evaluate over full temperature range
for dt in DTlm:
    q_star.append(QuadLin(coeffs, soc, dt))

q_d = [v * Q_nom / ts for v in q_star]


fig = go.Figure()
fig.add_trace(go.Scatter(y=q_d))
fig.show()
sys.exit()

def ice_performance (soc, return_temp, supply_temp, ice_cap, flag):

    # Import req'd packages
    import numpy as np

    # Ice Storage Curve Parameters
    coeffs = [0, 0.09, -0.15, 0.612, -0.324, -0.216]         # Same Coefficients for both charge and discharge in OS default
    x_rng = [0, 1]          # Range on SOC Variable Inputs
    y_rng = [0, 9.9]        # Range on DTlm* Variable Inputs
    freeze_temp = 0         # Freezing temperature of the ice storage [C]
    DTlm_nom = 10           # Nominal delta T, must equal 10C based on E+ Engineering Reference Guide

    # Set Charge or Discharge values based on flag
    if flag == 0:           # Discharging
        x = (1 - soc)
    elif flag == 1:			# Charging - Incomplete!
        x = soc

    if (return_temp - freeze_temp) / (supply_temp - freeze_temp) >= 0:
        DTlm = (return_temp - supply_temp) / np.log((return_temp - freeze_temp) / (supply_temp - freeze_temp))
    else:
        DTlm = 0

    y = DTlm / DTlm_nom     # Non-dimensionalized DTlm value

    # Check limits on input variable values
    # x is either percent charged or percent discharged
    if x < x_rng[0]:
        x = x_rng[0]
    elif x > x_rng[1]:
        x = x_rng[1]

    # y is non-dimensionalized log mean temperature difference across ice heat exchanger
    if y < y_rng[0]:
        y = y_rng[0]
    elif y > y_rng[1]:
        y = y_rng[1]

    # Max rate of discharge from ice - neglect charging for now.
    q_star = (c[0] + (c[1] * x) + (c[2] * (x**2))) + ((c[3] + (c[4] * x) + (c[5] * (x**2))) * y)
    q = q_star * ice_cap / 1    # Divisor is timestep of performance curve [hr], assumed to be 1 hr.

    return q;
