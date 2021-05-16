# insert your copyright here

# see the URL below for information on how to write OpenStudio measures
# http://nrel.github.io/OpenStudio-user-documentation/reference/measure_writing_guide/
require 'csv'

# start the measure
class ExposeChillers < OpenStudio::Measure::ModelMeasure
  # human readable name
  def name
    # Measure name should be the title case of the class name.
    return 'Expose Chillers'
  end

  # human readable description
  def description
    return 'This measure idenifies all chillers in the model and exports all related data.'
  end

  # human readable description of modeling approach
  def modeler_description
    return 'The measure performs the following functions: (1) IDs all chillers, (2) Locates their performance curves and outputs the data, (3) Adds reporting variables for chiller-related data.'
  end

  # define the arguments that the user will input
  def arguments(model)
    args = OpenStudio::Measure::OSArgumentVector.new

    return args
  end

  # define what happens when the measure is run
  def run(model, runner, user_arguments)
    super(model, runner, user_arguments)

    # use the built-in error checking
    if !runner.validateUserArguments(arguments(model), user_arguments)
      return false
    end

    # report initial condition of model
    runner.registerInitialCondition("Started.")

    # assign the user inputs to variables
    ## TBD

    # iterate through the chillers and capture chiller & curve data
    chillers = model.getChillerElectricEIRs
    idx = 0
    chiller_names = Array.new()
    chillers.each do |c|
      # get chiller specs
      chiller_names += [c.name.to_s]
      cop_ref = c.referenceCOP
      elwt_ref = c.referenceLeavingChilledWaterTemperature
      cewt_ref = c.referenceEnteringCondenserFluidTemperature
      plr_min = c.minimumPartLoadRatio
      condenser = c.condenserType
      cond_fan = c.condenserFanPowerRatio

      # get CAPfT curve (BiQuadratic)
      cap_ft = c.coolingCapacityFunctionOfTemperature
      cap_ft_coeffs = [cap_ft.coefficient1Constant,
                       cap_ft.coefficient2x,
                       cap_ft.coefficient3xPOW2,
                       cap_ft.coefficient4y,
                       cap_ft.coefficient5yPOW2,
                       cap_ft.coefficient6xTIMESY]
      cap_ft_limits = [cap_ft.minimumValueofx, cap_ft.maximumValueofx,
                       cap_ft.minimumValueofy, cap_ft.maximumValueofy,
                       cap_ft.minimumCurveOutput, cap_ft.maximumCurveOutput]

      # get EIRfT curve (BiQuadratic)
      eir_ft = c.electricInputToCoolingOutputRatioFunctionOfTemperature
      eir_ft_coeffs = [eir_ft.coefficient1Constant,
                       eir_ft.coefficient2x,
                       eir_ft.coefficient3xPOW2,
                       eir_ft.coefficient4y,
                       eir_ft.coefficient5yPOW2,
                       eir_ft.coefficient6xTIMESY]
      eir_ft_limits = [eir_ft.minimumValueofx, eir_ft.maximumValueofx,
                       eir_ft.minimumValueofy, eir_ft.maximumValueofy,
                       eir_ft.minimumCurveOutput, eir_ft.maximumCurveOutput]

      # get EIRfPLR curve (Quadratic)
      eir_fPLR = c.electricInputToCoolingOutputRatioFunctionOfPLR
      eir_fPLR_coeffs = [eir_fPLR.coefficient1Constant,
                         eir_fPLR.coefficient2x,
                         eir_fPLR.coefficient3xPOW2]
      eir_fPLR_limits = [eir_fPLR.minimumValueofx, eir_fPLR.maximumValueofx,
                       eir_fPLR.minimumCurveOutput, eir_fPLR.maximumCurveOutput]

      # get chiller capacity via EMS built-in variable, create as output variable
      n = OpenStudio::Model::EnergyManagementSystemInternalVariable.new(model, "Chiller Nominal Capacity")
      n.setName("Chiller#{idx}_Nominal_Capacity")
      n.setInternalDataIndexKeyName(c.name.to_s)

      n = OpenStudio::Model::EnergyManagementSystemOutputVariable.new(model, "Chiller#{idx}_Nominal_Capacity")
      n.setName("Chiller#{idx} Nominal Capacity")
      n.setUnits("W")

      # write available data to file
      file = CSV.open("chiller#{idx}.dat", 'w') do |wrt|
        wrt << [c.name.to_s]
        wrt << [cop_ref, plr_min, elwt_ref, cewt_ref]
        wrt << [condenser, cond_fan]
        wrt << cap_ft_coeffs
        wrt << cap_ft_limits
        wrt << eir_ft_coeffs
        wrt << eir_ft_limits
        wrt << eir_fPLR_coeffs
        wrt << eir_fPLR_limits
        wrt << []
        wrt << [
        "Key:
        Chiller Name
        Reference COP, Minimum Part Load Ratio, Design Evaporator Leaving Fluid Temp, Design Condenser Entering Fluid Temp
        Condenser Type, Condenser Fan Power Ratio
        Capacity as a Function of Temperature Coefficients (BiQuadratic)
        Capacity as a Function of Temperature Limits (x min/max, y min/max, output min/max)
        EIR as a Function of Temperature Coefficients (BiQuadratic)
        EIR as a Function of Temperature Limits (x min/max, y min/max, output mix/max)
        EIR as a Function fo PLR Coefficiets (Quadratic)
        EIR as a Function of PLR Limits (x min/ max, output min/max)"]
      end

      # add output variables
      vars = ["Chiller Electricity Rate",
              "Chiller Evaporator Cooling Rate",
              "Chiller Evaporator Inlet Temperature",
              "Chiller Evaporator Mass Flow Rate",
              "Chiller Part Load Ratio",
              "Chiller Nominal Capacity",
              "Disctrict Cooling Chilled Water Rate",
              "District Cooling Mass Flow Rate"]

      vars.each do |v|
        n = OpenStudio::Model::OutputVariable.new(v, model)
        n.setKeyValue(chiller_names[idx])
        n.setReportingFrequency("Timestep")
      end

      # add EMS output dictionary reporting for internal variables
      n = model.getOutputEnergyManagementSystem
      n.setActuatorAvailabilityDictionaryReporting("Verbose")
      n.setInternalVariableAvailabilityDictionaryReporting("Verbose")
      n.setEMSRuntimeLanguageDebugOutputLevel("None")
      puts(n)

      # add output variable from EMS
      n = OpenStudio::Model::OutputVariable.new("Chiller#{idx} Nominal Capacity", model)
      n.setName("Chiller#{idx} Nominal Capacity")
      n.setReportingFrequency("Timestep")

      idx += 1

    end

    if chiller_names.size > 0
      File.open("chiller_index.dat", "w") do |line|
        for c in chiller_names
          line.write("#{chiller_names.index(c)}, #{c}")
        end
      end
    end

    # report final condition of model
    runner.registerFinalCondition("Finished.")

    return true
  end
end

# register the measure to be used by the application
ExposeChillers.new.registerWithApplication
