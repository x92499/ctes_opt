# Chiller Power Calculation Script
# Karl Heine, November 16, 2020
# Purpose: This is the "main" script that calculates chiller power based on a set of inputs
# Curve scripts are called to perform specific curve calculations and must be required here
# References: OpenStudio Standards Chiller Curves, EnergyPlus Engineering Reference Ch. 14.3.9

## Import
import sys
import numpy as np
import plotly.graph_objects as go
from curves import BiQuad, Quad

## Variable Definitions
# cap_fT = chiller capacity as a function of temperatures
# cop_ref = nominal chiller COP
# cp = specific heat capacity of water/working fluid
# eir_fP = chiller energy input ratio as a function of part load ratio
# eir_fT = chiller energy input ratio as a function of temperatures
# Load = chiller thermal load (m_dot*cp*(Te_in-Te_out))
# m_dot = mass flow rate of water through the evaporator
# P = chiller electric power (total)
# P_e = chiller electric power (evaporator side)
# P_c = chiller electric power (condensor side)
# plr = chiller part load ratio
# plr_min = minimum part load ratio
# Q_av = chiller capacity available
# Q_ref = nominal chiller capacity
# Te_i = Temp of water entering evaporator
# Te_o = Temp of water leaving the evaporator
# Te_o_min = Temp of water leaving evaporator at the minimum PLR
# Tl_s = Temp of loop (setpoint)
# Tc_i = Temp of water entering condensor
# Tc_o = Temp of water leaving the condensor
# Tdb = Temp of outside air (drybulb)
# Twb = Temp of outside air (wetbulb)
# Y = load shed (calc from Te_o)

## Set Inputs
m_dot = 48.3        #kg/s
cp = 4179.6         #J/kg-K
Q_ref = 1139092     #W_th
cop_ref = 2.80      #W_th/W_e
plr_min = 0.15      #[-]
Tl_s = 6.6667         #C
Pc_fan = 0          #W_fan/W_chiller

Tdb = 37.4            #C
Te_i = 11.4         #C
Te_o = np.linspace(Tl_s, Te_i, 200)
P_current = 365000  #kW_e
Q_current = 955000  #kW_th

## Get cap_fT
#coeffs = [1.0433825, 0.0407073, 0.0004506, -0.0041514, -8.86e-005, -0.0003467]      #AirCooled_Chiller_2004_PathA_CAPFT
#coeffs = [0.985959, 0.049487, -0.000298, -0.003737, -4.5e-05, -0.000502]            #ChlrAirScrewQRatio_fTchwsToadbSI
coeffs = [1.05229229, 0.033560892, 0.000215, -0.005180832, -4.42e-05, -0.000215]    #ScrollChlrAirCoolCap-fCHW&OAT
cap_fT = []
for v in Te_o:
    val = BiQuad(coeffs, v, Tdb)
    cap_fT.append(val)

## Get eir_fT
#coeffs = [0.5961915, -0.0099496, 0.0007888, 0.0004506, 0.0004875, -0.0007623]       #AirCooled_Chiller_2004_PathA_EIRFT
#coeffs = [0.570624, 0.011954, -0.000522, -3.2e-05, 0.000421, -0.000606]              #ChlrAirScrewEIRRatio_fTchwsToadbSI
coeffs =[0.58333562, -0.004036194, 0.000468, -0.000224478, 0.000481, -0.000682]     #ScrollChlrAirCoolEIR-fCHW&OAT
eir_fT = []
for v in Te_o:
    val = BiQuad(coeffs, v, Tdb)
    eir_fT.append(val)

## Get plr
plr = []
Load = []
Q_av = []
min_plr_idx = 0
for i in range(len(Te_o)):
    Load.append(m_dot * cp * (Te_i - Te_o[i]))
    Q_av.append(Q_ref * cap_fT[i])
    plr.append(Load[i] / Q_av[i])

    if min_plr_idx == 0 and plr[i] < plr_min:
        Te_o_min = Te_o[i-1]
        min_plr_idx = i-1

## Get eir_fP
#coeffs = [0.141, 0.655, 0.203]                      #AirCooled_Chiller_AllCapacities_2004_2010_EIRFPLR
#coeffs = [0.036487, 0.734743, 0.219947]             #ChlrAirScrewEIRRatio_fQRatio
coeffs = [0.03366649, 0.53152555, 0.43480802]       #ScrollChlrAirCoolEIR-fPLR
eir_fP = []
for v in plr:
    val = Quad(coeffs, v)
    eir_fP.append(val)

## Get chiller power - evaporator component
Pe = []
for i in range(len(Te_o)):
    Pe.append(Q_av[i] / cop_ref * eir_fT[i] * eir_fP[i])

## Get chiller power - condensor component
Pc = [Q_ref * Pc_fan for i in range(len(Te_o))]

## Get total chiller power (modified to be a change in chiller power as load is shed)
P = (Pe[0] + Pc[0]) - [Pe[i] + Pc[i] for i in range(len(Te_o))]

## Get load shed from Te_o
Y = m_dot * cp * (Te_i - Te_o)
Y = Y[::-1]

# Generate Reference lines
P_copref = [i / cop_ref for i in Y]
P_limit = [P_current for i in Y]
P_linear = [P_current / Q_current * i for i in Y]

# Generate performance below min PLR:
Y_belowminplr = []
P_belowminplr = []
P_minplr = 0
Y_minplr = 0
m_plr = 0
i_minplr = 0
flag_plr = False
for i in range(len(Y)):
    if plr[i] < plr_min:
        if flag_plr:
            Y_belowminplr.append(Y[i])
            P_belowminplr.append((m_plr * (Y[i] - Y_minplr)) + P_minplr)
        else:
            P_minplr = P[i]
            Y_minplr = Y[i]
            m_plr = (P_current - P_minplr) / (Q_current - Y_minplr)
            i_minplr = i
            flag_plr = True

# Get linear regression over region above min plr
segs = 4
seg_sz = len(Te_o[:i_minplr])//segs
fit = []
P_fit = []

for i in range(segs):
    print(i*seg_sz, (i+1)*seg_sz+1, Y[(i+1)*seg_sz+1] - Y[i*seg_sz])
    fit.append(np.poly1d(np.polyfit(Y[i*seg_sz:(i+1)*seg_sz+1], P[i*seg_sz:(i+1)*seg_sz+1], 1)))
    P_fit.append(fit[i](Y[i*seg_sz:(i+1)*seg_sz+1]) + (P[i*seg_sz] - fit[i](Y[i*seg_sz])))
    print(fit[i])

# Get Max Error:
err = 0
err_rel = 0
for i in range(segs):
    err = [j - k for j, k in zip(P[i*seg_sz:(i+1)*seg_sz+1], P_fit[i])]
    err_rel = [(j - k) / j for j, k in zip(P[i*seg_sz:(i+1)*seg_sz+1], P_fit[i]) if j > 0]

err = round(max(err) / 1000, 3)
err_rel = round(max(err_rel) * 100, 2)
print(err, err_rel)

# # Create Figure
# fig = go.Figure()
# fig.add_trace(go.Scatter(x=Y, y=P_limit, name="Chiller Power at Current Conditions (Baseline)",
#                     mode="markers", marker_symbol=141, marker_size=2, marker_color="red"))
# fig.add_trace(go.Scatter(x=Y[:i_minplr+1], y=P[:i_minplr+1], name="Chiller Model Above Min PLR",
#                     mode="lines", line_color="black"))
# fig.add_trace(go.Scatter(x=Y, y=P_copref, name="Nominal COP Approximation"))
# fig.add_trace(go.Scatter(x=Y, y=P_linear, name="Linear Approximation"))
# fig.add_trace(go.Scatter(x=Y_belowminplr, y=P_belowminplr, name="Chiller Model Below Min PLR",
#                     mode="markers", marker_symbol=0, marker_size=2, marker_color="black"))
# for i in range(segs):
#     fig.add_trace(go.Scatter(x=Y[i*seg_sz:(i+1)*seg_sz+1], y=P_fit[i], name="Linear Approx. Segment {}".format(i+1)))
# fig.update_layout(title="Power Shed f(Load Shed)",
#                 plot_bgcolor="white")
# fig.update_xaxes(title="Thermal Load Reduction (Shed) [W_th]",
#                 showgrid=False, zeroline=True, zerolinecolor="black", zerolinewidth=1)
# fig.update_yaxes(title="Electrical Load Reduction (Shed) [W_e]",
#                 showgrid=False, zeroline=True, zerolinecolor="black", zerolinewidth=1)
# fig.show()
