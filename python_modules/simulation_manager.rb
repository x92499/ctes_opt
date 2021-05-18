## simulation_manager.rb
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 17, 2021
# Completed:

## The purpose of this script is to execute buiding energy simulations via
# OpenStudio in order to process the .eso output files for use in the
# CTES optimization workflow.

require 'sh'

# Display OpenStudio Version
version = Sh::Cmd.new("openstudio").arg("openstudio_version")
system(version.to_s)

# Find .osm files
seeds = Dir.entries("resources/OS Models for Campus Buildings/**/*")
seeds.each do |s|
  puts(s)
end
