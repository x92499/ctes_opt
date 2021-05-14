# Performance Curve Plots
# xarl Heine, 20190605

# This script plots the performance curve data taxen from the default curves within OpenStudio for the Ice Storage object.
# Ref. object: OS:ThermalStorage:Ice:Detailed
# EnergyPlus Engineering Reference: Ch 16.1.2
# EnergyPlus Input-Output Reference: Ch 1.56.11 (Curves)

import sys
import pandas as pd
import numpy as np
import plotly
import plotly.graph_objs as go
from plotly import tools

# Set charge/discharge curve coefficients

## Detailed Model
# Curve Type: Quadratic Linear - values from the OpenStudio object defaults
c = [0,			# constant
	 0.09,		# x
	 -0.15,		# x^2
	 0.612,		# y
	 -0.324,	# x*y
	 -0.216]	# x^2*y

Treturn = (58 - 32)/1.8		#F to C
Tloop = (42 - 32)/1.8		#F to C
Tfreeze = (32 - 32)/1.8		#F to C
DeltaT = 6/1.8				#F to C
DeltaT_Nominal = 18/1.8		#F to C
Cap = 400*12660670.23144	#Ton-hours to J
dt = 3600					#s

LMTD_star_actual = []
LMTD_star_model = []

# Actual System with Ice Priority
Tin = Treturn
Tout = Tin - DeltaT
LMTD_star_actual = (DeltaT/np.log((Tin - Tfreeze)/(Tout - Tfreeze)) / DeltaT_Nominal)

# As Modeled in OpenStudio Measure
Tout = Tloop
Tin = Tloop + DeltaT
LMTD_star_model = (DeltaT/np.log((Tin - Tfreeze)/(Tout - Tfreeze)) / DeltaT_Nominal)

Pd = np.linspace(0,1,100)

q_actual = []
q_model = []
q_star_actual = []
q_star_model = []
q_actual_trace = []
q_model_trace = []
q_star_actual_trace = []
q_star_model_trace = []

# Calculate q* and q
for j in range(len(Pd)):
	x = Pd[j]
	y = LMTD_star_actual
	q_star_actual.append(c[0] + c[1]*x + c[2]*(x**2) + c[3]*y + c[4]*y*x + c[5]*y*(x**2))

	y = LMTD_star_model
	q_star_model.append(c[0] + c[1]*x + c[2]*(x**2) + c[3]*y + c[4]*y*x + c[5]*y*(x**2))

q_actual = np.array(q_star_actual)*Cap/dt
q_model = np.array(q_star_model)*Cap/dt

q_star_actual_trace.append(go.Scatter(x = Pd, y = q_star_actual, name = 'Actual', hoverlabel = dict(namelength = -1), line = dict(dash = 'dot')))
q_star_model_trace.append(go.Scatter(x = Pd, y = q_star_model, name = 'Model', hoverlabel = dict(namelength = -1)))
q_actual_trace.append(go.Scatter(x = Pd, y = q_actual, name = 'Actual', hoverlabel = dict(namelength = -1), line = dict(dash = 'dot')))
q_model_trace.append(go.Scatter(x = Pd, y = q_model, name = 'Model', hoverlabel = dict(namelength = -1)))

## Create Figures
fig = tools.make_subplots(rows = 2, cols = 1,
						  subplot_titles = ('q*', 'Max Heat Transfer Rate with Q = ' + str(round(Cap/1e9, 2)) + ' GJ and dt = ' + str(dt)))

for i in range(len(q_star_actual_trace)):
	fig.append_trace(q_star_actual_trace[i],1,1)
	fig.append_trace(q_star_model_trace[i],1,1)
	fig.append_trace(q_actual_trace[i],2,1)
	fig.append_trace(q_model_trace[i],2,1)

fig['layout'].update(title = 'Ice Discharge Curves - Return Water at ' + str(round(Treturn, 2)) +
 					 'C, Loop Temp at ' + str(round(Tloop, 2)), hovermode = 'closest', showlegend = False)
fig['layout']['xaxis1'].update(title='Fraction Discharged [-]')
fig['layout']['yaxis1'].update(title='q* [-]')
fig['layout']['xaxis2'].update(title='Fraction Discharged [-]')
fig['layout']['yaxis2'].update(title='Heat Transfer Rate [W]')

plotly.offline.plot(fig, filename = 'ice_curves.html')
