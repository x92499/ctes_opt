# insert your copyright here

# see the URL below for information on how to write OpenStudio measures
# http://nrel.github.io/OpenStudio-user-documentation/reference/measure_writing_guide/

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

    # assign the user inputs to variables
    ## TBD

    # iterate through the chillers and capture chiller & curve data
    chillers = model.getChillerElectricEIRs
    chillers.each do |c|
      # get chiller specs
      name = c.name
      # cap = NEED TO GET AFTER AUTOSIZING! (convert to REPORTING measure)
      cop_ref = c.referenceCOP
      elwt_ref = c.referenceLeavingChilledWaterTemperature
      cewt_ref = c.referenceEnteringCondenserFluidTemperature
      plr_min = c.minimumPartLoadRatio
      condenser = c.condenserType
      con_fan = c.condenserFanPowerRatio

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
      eir_ft_limits = [eir_fPLR.minimumValueofx, eir_fPLR.maximumValueofx,
                       eir_fPLR.minimumCurveOutput, eir_fPLR.maximumCurveOutput]
      puts(eir_ft, eir_fPLR, cap_ft)
    end


    # report initial condition of model
    runner.registerInitialCondition("The building started with #{model.getSpaces.size} spaces.")

    # report final condition of model
    runner.registerFinalCondition("The building finished with #{model.getSpaces.size} spaces.")

    return true
  end
end

# register the measure to be used by the application
ExposeChillers.new.registerWithApplication
