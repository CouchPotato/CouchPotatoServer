require 'fileutils'

task :default => [:clean]

task :clean do
  [".", "tests"].each do |cd|
    puts "Cleaning directory #{cd}"
    Dir.new(cd).each do |t|
      if t =~ /.*\.pyc$/
        puts "Removing #{File.join(cd, t)}"
        File.delete(File.join(cd, t))
      end
    end
  end
end

desc "Upversion files"
task :upversion do
  puts "Upversioning"

  Dir.glob("*.py").each do |filename|
    f = File.new(filename, File::RDWR)
    contents = f.read()

    contents.gsub!(/__version__ = ".+?"/){|m|
      cur_version = m.scan(/\d+\.\d+/)[0].to_f
      new_version = cur_version + 0.1

      puts "Current version: #{cur_version}"
      puts "New version: #{new_version}"

      new_line = "__version__ = \"#{new_version}\""

      puts "Old line: #{m}"
      puts "New line: #{new_line}"

      m = new_line
    }

    puts contents[0]

    f.truncate(0) # empty the existing file
    f.seek(0)
    f.write(contents.to_s) # write modified file
    f.close()
  end
end

desc "Upload current version to PyPi"
task :topypi => :test do
  cur_file = File.open("tvdb_api.py").read()
  tvdb_api_version = cur_file.scan(/__version__ = "(.*)"/)
  tvdb_api_version = tvdb_api_version[0][0].to_f

  puts "Build sdist and send tvdb_api v#{tvdb_api_version} to PyPi?"
  if $stdin.gets.chomp == "y"
    puts "Sending source-dist (sdist) to PyPi"

    if system("python setup.py sdist register upload")
      puts "tvdb_api uploaded!"
    end

  else
    puts "Cancelled"
  end
end

desc "Profile by running unittests"
task :profile do
  cd "tests"
  puts "Profiling.."
  `python -m cProfile -o prof_runtest.prof runtests.py`
  puts "Converting prof to dot"
  `python gprof2dot.py -o prof_runtest.dot -f pstats prof_runtest.prof`
  puts "Generating graph"
  `~/Applications/dev/graphviz.app/Contents/macOS/dot -Tpng -o profile.png prof_runtest.dot -Gbgcolor=black`
  puts "Cleanup"
  rm "prof_runtest.dot"
  rm "prof_runtest.prof"
end

task :test do
  puts "Nosetest'ing"
  if not system("nosetests -v --with-doctest")
    raise "Test failed!"
  end

  puts "Doctesting *.py (excluding setup.py)"
  Dir.glob("*.py").select{|e| ! e.match(/setup.py/)}.each do |filename|
    if filename =~ /^setup\.py/
      skip
    end
    puts "Doctesting #{filename}"
    if not system("python", "-m", "doctest", filename)
      raise "Failed doctest"
    end
  end

  puts "Doctesting readme.md"
  if not system("python", "-m", "doctest", "readme.md")
    raise "Doctest"
  end
end
