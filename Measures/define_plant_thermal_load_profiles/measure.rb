# insert your copyright here

# see the URL below for information on how to write OpenStudio measures
# http://nrel.github.io/OpenStudio-user-documentation/reference/measure_writing_guide/

# start the measure
class DefinePlantThermalLoadProfiles < OpenStudio::Measure::ModelMeasure
  # human readable name
  def name
    # Measure name should be the title case of the class name.
    return 'Define Plant Thermal Load Profiles'
  end

  # human readable description
  def description
    return 'This measure assigns load and flow information to a selected plant loop load profile.'
  end

  # human readable description of modeling approach
  def modeler_description
    return 'This measure assigns load and flow information to a selected plant loop load profile.'
  end

  # define the arguments that the user will input
  def arguments(model)
    args = OpenStudio::Measure::OSArgumentVector.new

    # select the plant loop load profile, if there is one
    load_profiles = model.getLoadProfilePlants
    choices = Array.new
    load_profiles.each do |lp|
      choices += [lp.name.to_s]
    end

    # create choice argument
    load_profile = OpenStudio::Measure::OSArgument.makeChoiceArgument("load_profile", choices, true)
    load_profile.setDisplayName("Select Load Profile: Plant")
    load_profile.setDefaultValue(choices[0])
    args << load_profile

    # create string argument for load schedule name
    load_sched = OpenStudio::Measure::OSArgument.makeStringArgument("load_sched", true)
    load_sched.setDisplayName("Enter name of plant load profile schedule:")
    load_sched.setDefaultValue("CP6 Load")
    args << load_sched

    # create string argument for flow fraction schedule name
    flow_sched = OpenStudio::Measure::OSArgument.makeStringArgument("flow_sched", true)
    flow_sched.setDisplayName("Enter name of plant flow fraction schedule:")
    flow_sched.setDefaultValue("CP6 Flow")
    args << flow_sched

    # create double arguement for peak flow rate in m/s
    max_flow = OpenStudio::Measure::OSArgument.makeDoubleArgument("max_flow", true)
    max_flow.setDisplayName("Enter max flow rate in m^3/s")
    max_flow.setDefaultValue(0.22618)
    args << max_flow

    return args
  end

  # define what happens when the measure is run
  def run(model, runner, user_arguments)
    super(model, runner, user_arguments)

    # use the built-in error checking
    if !runner.validateUserArguments(arguments(model), user_arguments)
      return false
    end

    # get user-selected load profile plant
    load_profile = runner.getStringArgumentValue("load_profile", user_arguments)
    load_sched = runner.getStringArgumentValue("load_sched", user_arguments)
    flow_sched = runner.getStringArgumentValue("flow_sched", user_arguments)
    max_flow = runner.getDoubleArgumentValue("max_flow", user_arguments)

    # Grab object
    profile = model.getLoadProfilePlantByName(load_profile).get
    load = model.getScheduleIntervalByName(load_sched).get
    flow = model.getScheduleIntervalByName(flow_sched).get

    # Assign values
    profile.setLoadSchedule(load)
    profile.setFlowRateFractionSchedule(flow)
    profile.setPeakFlowRate(max_flow)

    # report final condition of model
    runner.registerFinalCondition("Finished.")

    return true
  end
end

# register the measure to be used by the application
DefinePlantThermalLoadProfiles.new.registerWithApplication
