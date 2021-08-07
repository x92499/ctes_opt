# Centeral TES Optimization Formulation
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 16, 2021
# Revised May 3, 2021
# Revised July 1, 2021

#--------------------------------
# Model File
#--------------------------------
# integrated.mod

## Parameters--------------------
# Set defining values
param D >= 0;  # number of demand periods
param I >= 1;  # number of CTES types (1=UTSS, 2=Central)
param N >= 1;  # number of RTUs or plant loops
param S{1..N} >= 1;  # number of segments in chiller curve linearization
param T >= 1;  # number of timesteps
param Td_ct{1..D} >= 0;  # number of ts in each demand period
param Td_v{d in 1..D, 1..Td_ct[d]} >= 0;  # values which populate indexed set Td
param TYf_ct{1..N} >= 0;  # number of ts when full storage is possible
param TYf_v{n in 1..N, 1..TYf_ct[n]} >= 0;  # values which populate indexed set TYf
param TYp_ct{1..N} >= 0;  # number of ts when partial-storage possible
param TYp_v{n in 1..N, 1..TYp_ct[n]} >= 0;  # values which populate indexed set TYp
param Tr_ct >= 0;  # number of ts when DR events are occuring
param Tr_v{1..Tr_ct} >= 0;  # values which populate indexed set Tr

# Sets
set Td{1..D} default {};  # set of ts for each demand period
set TYf{1..N} default {};  # set for full storage possible ts
set TYp{1..N} default {};  # set for partial storage possible ts
set Tr default {};  # set for demand response timesteps

# Building  simulation Parameters
param l{1..N, 1..T} >= 0;  # cooling load met by RTU or chiller [kWth]
param pN{1..N, 1..T} >= 0;  # baseline RTU or chiller power (ts avg) [kWe]
param p{1..T} >= 0;  # baseline power demand for all buildings (ts avg) [kWe]

# Thermal storage parameters
param etaI{1..N, 1..T} >= 0, default 0.9975;  # timestep loss rate (5% per day)
param epsilon{1..N} >= 0, default 0.95;  # discharge effectiveness [-]
param lambdaX{1..N, 1..T};  # charging energy slopes [kWe/kWth]
param lambdaY{n in 1..N, 1..S[n], 1..T};  # partial storage discharge curve slopes [kWe/kWth]
param lbar{n in 1..N, 1..S[n], 1..T} >= 0;  # limits for each partial storge curve segment [kWth]
param qNX{1..N, 1..T} >= 0;  # max rate of charge by chiller [kWth]
param qIX{1..I} >= 0;  # max rate of charging for CTES [kWth]
param qIY{1..N, 1..T} >= 0;  # max rate of discharging for CTES [kWth]
param qbar{1..I} >= 0;  # nominal (usable) capacity of the CTES [kWth]

# Cost parameters
param c_d{1..D};  # cost of electric power in demand period [$/kW(max)]
param c_e{1..T};  # cost of electric energy at each timestep [$/kWh]
param c_r{Tr};  # cost of electric energy during demand response timesteps
param k{1..I} >= 0;  # capacity cost of storage by type and plant [$/kWh_t]

# Miscellaneous parameters
param delta > 0, <= 1;  # timestep [hr]
param yrs{1..I} >= 0, default 20;  # expected lifespan of TES [years]
param zbar{1..I, 1..N} >= 0, integer;  # maximum number of CTES I at plant N

## Variables---------------------
# Integer variables
var alpha{n in 1..N, t in TYf[n]} binary; # 1 iff. full storage mode
var Z{i in 1..I, n in 1..N} >= 0, <= zbar[i,n], integer;	# Number of CTES

# Continuous variables
var LX{1..N, 1..T} >= 0;  # charging load added [kW_th]
var LYf{n in 1..N, TYf[n]} >= 0;	# discharging load reduced via full storage [kW_th]
var LYp{n in 1..N, 1..S[n], TYp[n]} >= 0;	# discharging load reduced via partial storage [kW_th]
var Pd{1..D} >= 0;	# max power demand [kW_e (max)]
var P{1..T} >= 0;  # power demand (all buildings) [kW_e]
var PX{1..N, 1..T} >= 0;  # power increase from charging [kW_e]
var PYf{n in 1..N, TYf[n]} >= 0;  # power decrease from partial storage [kW_e]
var PYp{n in 1..N, TYp[n]} >= 0;  # power decrease from full storage [kW_e]
var Q{1..N, 1..T} >= 0;  # TES energy inventory [kWh_th]

## Objective---------------------
minimize annual_cost: (sum{t in 1..T} 1.31 * c_e[t] * delta * P[t]) + (sum{d in 1..D} c_d[d] * Pd[d]) +  (sum{i in 1..I} (k[i] * qbar[i] / yrs[i] * sum{n in 1..N} Z[i,n]));

## Constraints-------------------
# charging
s.t. charge_limit_ctes {n in 1..N, t in 1..T}: LX[n,t] <= sum{i in 1..I} qIX[i] * Z[i,n];
s.t. charge_limit_plant {n in 1..N, t in 1..T}: LX[n,t] <= qNX[n,t];

# discharging - full storage
s.t. discharge_full_load {n in 1..N, t in TYf[n]}: LYf[n,t] = l[n,t] * alpha[n,t];
s.t. discharge_full_rate {n in 1..N, t in TYf[n]}: LYf[n,t] <= sum{i in 1..I} qIY[n,t] * Z[i,n];

# discharging - partial storage
s.t. discharge_part_load {n in 1..N, s in 1..S[n], t in TYp[n]}: LYp[n,s,t] <= (if t in TYf[n] then ((1-alpha[n,t]) * lbar[n,s,t]) else lbar[n,s,t]);
s.t. discharge_part_rate {n in 1..N, t in TYp[n]}: sum{s in 1..S[n]} LYp[n,s,t] <= sum{i in 1..I} qIY[n,t] * Z[i,n];

# inventory (kWth avail at end of timestep)
s.t. tank_inventory{n in 1..N, t in 1..T: t>1}: Q[n,t] = etaI[n,t] * Q[n,t-1] + delta * (LX[n,t] - (if t in TYp[n] then (sum{s in 1..S[n]} LYp[n,s,t] - (if t in TYf[n] then LYf[n,t] else 0)) else 0));
s.t. max_soc {n in 1..N, t in 1..T}: Q[n,t] <= sum{i in 1..I} qbar[i] * Z[i,n];
s.t. soc_full {n in 1..N, t in TYf[n]: t>1}: delta * LYf[n,t] <= etaI[n,t] * Q[n,t-1];
s.t. soc_part {n in 1..N, t in TYp[n]: t>1}: delta * sum{s in 1..S[n]} LYp[n,s,t] <= etaI[n,t] * Q[n,t-1];
s.t. init_soc {n in 1..N}: Q[n,1] = 0;

# energy conversion
s.t. pwr_part {n in 1..N, t in TYp[n]}: PYp[n,t] <= epsilon[n] * (sum{s in 1..S[n]} lambdaY[n,s,t] * LYp[n,s,t]);
s.t. pwr_full {n in 1..N, t in TYf[n]}: PYf[n,t] <= epsilon[n] * pN[n,t] * alpha[n,t];
s.t. pwr_charge {n in 1..N, t in 1..T}: PX[n,t] >= lambdaX[n,t] * LX[n,t];
s.t. profile {t in 1..T}: P[t] >= p[t] + sum{n in 1..N} (PX[n,t] - (if t in TYp[n] then (PYp[n,t] - (if t in TYf[n] then PYf[n,t] else 0)) else 0));
s.t. peak_demand {d in 1..D, t in Td[d]}: Pd[d] >= P[t];

# prevent full storage operation except during DR events - used for testing to arbitrarily eliminte binary options
s.t. no_full {n in 1..N, t in TYf[n]: t not in Tr}: alpha[n,t] <= 0;

# enforce 200kW reduction for CPP events
# s.t. cpp {t in Tr}: P[t] <= p[t] - 200;
