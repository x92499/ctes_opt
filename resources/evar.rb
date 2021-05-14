# This scipt copies values for a single E+ .eso variable and puts it into a .csv

require 'csv'

def eso_variable_parser
  # Output list of available variable indices and names
  list_of_vars = Hash.new()
  f_in = File.foreach("eplusout.eso") do |line|
    ln = line.split(",")
    if ln.size == 3
      list_of_vars[:"#{ln[0]}"] = ln[2]
    else
      list_of_vars[:"#{ln[0]}"] = "#{ln[2]}, #{ln[3]}"
    end
    if line.include?("End of Data Dictionary")
      break
    end
  end

  # Get user selection for variable of interet
  list_of_vars.each do |k, v|
    puts("Key: #{k}, Variable: #{v}")
  end
  puts("")
  puts("Enter key for variable of interest from list above:")
  key = $stdin.gets.chomp
  puts("")
  puts("Does the variable need to be summed or averaged? Enter 's' or 'a':")
  type = $stdin.gets.chomp

  # Tell user what will be done
  var_name = list_of_vars[:"#{key}"].chomp
  file_name = "#{var_name.delete("[/\s:!\%,/]")}.csv"
  puts("'#{var_name}' will be written to file '#{file_name}' at hourly timesteps")

  # Get the variabble values
  var = Array.new()
  runperiod = false
  f_in = File.foreach("eplusout.eso") do |line|
    ln = line.split(",")
    if ln[1] == "RUN PERIOD 1"
      runperiod = true
    end

    if runperiod
      if ln[0] == key && ln.size == 2
        var << ln[1].to_f
      end
    end
  end

  # Process variable
  var_hourly = Array.new(8760, 0)
  ts = var.size/8760
  puts("The timestep for the selected variable is: #{ts} per hour.")
  if type == 's'
    puts("Variable values will be summed to obtain hourly data.")
    var.size.times do |i|
      var_hourly[(i/ts).floor] += var[i]
    end
  elsif type == "a"
    puts("Variable values will be averaged to obtain hourly data.")
    var.size.times do |i|
      var_hourly[(i/ts).floor] += var[i] / ts
    end
  end

  #Write to file
  CSV.open(file_name, "w") do |csv|
    var_hourly.each do |v|
      csv << [v]
    end
  end
end

# Execute script
begin
  eso_variable_parser()
rescue Exception => e
  File.open("error.log") do |f|
    f.puts(e.inspect)
    f.puts(e.backtrace)
  end
end
