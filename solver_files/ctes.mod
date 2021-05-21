# Centeral TES Optimization Formulation
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 16, 2021
# Revised May 3, 2021

#--------------------------------
# Model File
#--------------------------------
# ctes.mod

## Parameters--------------------
# Set defining values
param B >= 1;  # number of buildings
param D >= 0;  # number of demand periods
param I >= 1;  # number of CTES types
param N >= 1;  # number of plant loops
param S >= 1;  # number of segments in chiller curve linearization
param T >= 1;  # number of timesteps
param Tdr_ct >= 0;  # number of ts when DR events are occuring
param TY_ct{1..N} >= 0;  # number of ts when cooling load exists
param TYpart_ct{1..N} >= 0;  # number of ts when partial-storage possible
param TX_ct{1..N} >= 0;  # number of ts when charging possible
param Tp_ct{1..D} >= 0;  # number of ts in each demand period
param Tdr_v{1..Tdr_ct} >= 0;  # values which populate indexed set Tdr
param TY_v{n in 1..N, 1..TY_ct[n]} >= 0;  # values which populate indexed set TY
param TYpart_v{n in 1..N, 1..TYpart_ct[n]} >= 0;  # values which populate indexed set TYpart_v
param TX_v{n in 1..N, 1..TX_ct[n]} >= 0;  # values which populate indexed set TX
param Tp_v{d in 1..D, 1..Tp_ct[d]} >= 0;  # values which populate indexed set Tp

# Sets (indexed)
set Tdr default {};  # set for demand response timesteps
set TY{1..N} default {};  # set for discharge possible ts
set TYpart{1..N} default {};  # set for partial storage possible ts
set TX{1..N} default {};  # set for charging possible ts
set Tp{1..D} default {};  # set of ts for each demand period

# General constants
param delta > 0, <= 1;  # timestep [hr]

# Building and chiller parameters
param p{1..T} >= 0;  # baseline power demand for all buildings (ts avg) [kWe]
param pN{1..N, 1..T} >= 0;  # baseline chiller power (ts avg) [kWe]
param l{1..N, 1..T} >= 0;  # cooling load met by chiller [kWth]
param lambdaY{1..N, 1..S, 1..T};  # partial storage discharge curve slopes [kWe/kWth]
param lambdaX{1..N, 1..T};  # charging energy slopes [kWe/kWth]
param qNX{1..N, 1..T} >= 0;  # max rate of charge by chiller [kWth]
param y_bar{1..N, 1..S, 1..T} >= 0;  # limits for each partial storge curve segment [kWth]

# CTES parameters
param etaQ := .9978;  # hourly loss rate (CALC IN PREPROCCESSOR or SET in fixed_params)
param qIX >= 0;  # max rate of charging for CTES [kWth]
param qIY{1..N, 1..T} >= 0;  # max rate of discharging for CTES [kWth]
param q >= 0;  # nominal (usable) capacity of the CTES [kWth]

# Cost parameters
param c_e{1..T};  # cost of electric energy at each timestep [$/kWh]
param c_p{1..D};  # cost of electric power in demand period [$/kW(max)]
param k >= 0, default 4538;  # annualized capital cost of storage [$/unit/year]

# Misc parameters
param m{1..N} >= 0, integer, default 20;  # maximum number of CTES at plant N

## Variables---------------------
# Integer variables
var Z{n in 1..N} >= 0, <= m[n], integer;	# Number of CTES
var alpha{n in 1..N, t in 1..T} binary; # 1 iff. full storage mode

# Continuous variables
var X{1..N, 1..T} >= 0;  # charging load added [kW_th]
var Y{1..N, 1..T} >= 0;	# discharging load reduced [kW_th]
var Yfull{1..N, 1..T} >= 0;	# discharging load reduced via full storage [kW_th]
var Ypart{1..N, 1..S, 1..T} >= 0;	# discharging load reduced via partial storage [kW_th]
var Q{1..N, 1..T} >= 0;  # TES energy inventory [kWh_th]
var P{1..T} >= 0;  # power demand (all buildings) [kW_e]
var PX{1..N, 1..T} >= 0;  # power increase from charging [kW_e]
var PY{1..N, 1..T} >= 0;  # power decrease from discharging [kW_e]
var PYfull{1..N, 1..T} >= 0;  # power decrease from partial storage [kW_e]
var PYpart{1..N, 1..T} >= 0;  # power decrease from full storage [kW_e]
var P_hat{1..D} >= 0;	# max power demand [kW_e (max)]

## Objective---------------------
minimize annual_cost: (sum{t in 1..T} c_e[t] * delta * P[t]) + (sum{d in 1..D} c_p[d] * P_hat[d]) +  (sum{n in 1..N} k * Z[n]);

## Constraints-------------------
# init, only allow discharge during March 15-October 31. Need to move to fixed_params
s.t. initialize {n in 1..N}: Q[n,1] = 0;
s.t. offseason1 {n in 1..N, t in 1..1776}: Yfull[n,t] <= 0;
s.t. offseason2 {n in 1..N, s in 1..S, t in 1..1776}: Ypart[n,s,t] <= 0;
s.t. offseason3 {n in 1..N, t in 7296..8760}: Yfull[n,t] <= 0;
s.t. offseason4 {n in 1..N, s in 1..S, t in 7296..8760}: Ypart[n,s,t] <= 0;

# charging
s.t. charge_limit_ctes {n in 1..N, t in 1..T}: X[n,t] <= qIX * Z[n];
s.t. charge_limit_plant {n in 1..N, t in 1..T}: X[n,t] <= (if t in TX[n] then ((1-alpha[n,t]) * qNX[n,t]) else 0);
s.t. charge_limit_soc {n in 1..N, t in 1..T}: Q[n,t] <= q * Z[n];

# discharging - full storage
s.t. discharge_full_load {n in 1..N, t in 1..T}: Yfull[n,t] = (if t in TY[n] then (alpha[n,t] * l[n,t]) else 0);
s.t. discharge_full_soc {n in 1..N, t in 1..T}: Yfull[n,t] * delta <= Q[n,t];
s.t. discharge_full_rate {n in 1..N, t in 1..T}: Yfull[n,t] <= qIY[n,t] * Z[n];

# discharging - partial storage
s.t. discharge_part_segs {n in 1..N, s in 1..S, t in 1..T}: Ypart[n,s,t] <= (if t in TYpart[n] then ((1-alpha[n,t]) * y_bar[n,s,t]) else 0);
s.t. discharge_part_soc {n in 1..N, t in 1..T}: sum{s in 1..S} Ypart[n,s,t] * delta <= Q[n,t];
s.t. discharge_part_rate {n in 1..N, t in 1..T}: sum{s in 1..S} Ypart[n,s,t] <= qIY[n,t] * Z[n];

# inventory balance (kWth avail at end of timestep)
s.t. tank_inventory {n in 1..N, t in 1..T: t>1}: Q[n,t] = (etaQ * Q[n,t-1]) + (delta * (X[n,t] - Yfull[n,t] - sum{s in 1..S} Ypart[n,s,t]));

# energy conversion
s.t. profile_part {n in 1..N, t in 1..T}: PYpart[n,t] <=(sum{s in 1..S} lambdaY[n,s,t] * Ypart[n,s,t]);
s.t. profile_full {n in 1..N, t in 1..T}: PYfull[n,t] <= alpha[n,t] * pN[n,t];
s.t. profile_charge {n in 1..N, t in 1..T}: PX[n,t] >= lambdaX[n,t] * X[n,t];
s.t. profile {t in 1..T}: P[t] >= p[t] + sum{n in 1..N} (PX[n,t] - PYpart[n,t] - PYfull[n,t]);
s.t. peak_demand {d in 1..D, t in Tp[d]}: P_hat[d] >= P[t];

# prevent full storage operation except during DR events
s.t. no_full {n in 1..N, t in 1..T: t not in Tdr}: alpha[n,t] <= 0;
