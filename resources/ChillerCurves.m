% Chiller Curve Analysis
% Karl Heine, 20201109
% The purpose of this script is to evaluate the chiller efficiency as a
% function of only the evaporator outlet temperature
% References: OpenStudio Standards for Chiller Curve Coefficients,
% EnergyPlus Engineering Reference Section 14.3.9

% *IF* a linear curve provides an acceptable fit, this will be used within
% a python pre-processing script for a central ice optimization workflow.

% Curve Name Reference List:
% 1: "90.1-2010 AirCooled WithCondenser Chiller 0 278tons 1.3kW/ton

%% Setup
clf; clc;
clear all;
close all;

% Flow Properties
m = 47;       % kg/s
cp = 4179.6;    % J/kg-K
T_in = 8.2;     % C, T_evap_in
Qref = 1139092;  % W (thermal)
COP_nom = 2.80;    % kWth/kWe
plr_min = 0.25;     % Minimum Chiller Part Load

% Temperatures
Te = linspace(6.67, T_in);      % C, T_evap_in
Tc = 32.2;                        % C, T_cond_in, drybulb

%% Main Program

% CAP(T)
% x = T_evap_out; y = T_cond_in;
coeffs = [1.0433825, 0.0407073, 0.0004506, -0.0041514, -8.86e-005, -0.0003467];
cap_fT = biQuad(coeffs, Te, Tc);

% EIR(T)
% x = T_evap_out; y = T_cond_in;
coeffs = [0.5961915, -0.0099496, 0.0007888, 0.0004506, 0.0004875, -0.0007623];
eir_fT = biQuad(coeffs, Te, Tc);

% PLR(Te)
plr = PLR(m, cp, Te, T_in, Qref, cap_fT);

% EIR(PLR)
% x = Part Load Ratio (0-1);
% plr = linspace(0,1,50);
coeffs = [0.141, 0.655, 0.203];
eir_plr = Quad(coeffs, plr);

% COP(EIR(T), EIR(PLR))
cop = COP_nom./eir_plr./eir_fT;

% Cooling Rate
rate = m.*cp.*(T_in - Te);

% Cycling Ratio
cyc_ratio = min(plr/plr_min, 1.0);

% Chiller power
P = cop.*m.*cp.*(T_in - Te).*cyc_ratio./(1000);

%% Perform Linear Regression

limit = 99;
[p, S] = polyfit(Te(1:limit), cop(1:limit), 1);

% Get R^2
R2 = 1 - (S.normr/norm(cop - mean(cop)))^2
Te(limit)
plr(limit)

%% Create Figures

% figure()
% plot(Te, plr, 'DisplayName', 'PLR');
% hold on;
% legend("show");

figure()
plot(Te, cap_fT, 'DisplayName', 'CAP(T)');
hold on;
legend("show");

figure()
plot(Te, eir_fT, 'DisplayName', 'EIR(T)');
hold on;
legend("show");

figure()
plot(Te, eir_plr, 'DisplayName', 'EIR(PLR)');
hold on;
legend("show");

figure()
plot(Te, cop);
xlabel("Evaporator Outlet Temperature");
ylabel("COP");
hold on;
plot(Te(1:limit), polyval(p, Te(1:limit)));
txt1 = sprintf("COP ~ %g Te + %g", p(1), p(2));
txt2 = sprintf("R^2 = %g", R2);
text(10,2.5,txt1)
text(10,2.3,txt2)

figure()
plot(Te, P);

% figure()
% plot(Te, rate);

%% Functions (Performance Curves)

function [result] = biQuad(c, x, y)
    result = c(1) + c(2).*x + c(3).*x.^2 + c(4).*y + c(5).*y.^2 + c(6).*x.*y;
end

function [result] = Quad(c, x)
    result = c(1) + c(2).*x + c(3).*x.^2;
end

function [result] = PLR(m, cp, Te, T_in, Qref, cap)
    result = (m.*cp.*(T_in - Te)) ./ (Qref.*cap);
end