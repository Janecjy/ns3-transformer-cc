# ##############################################################################
# Required CMake version            #
# ##############################################################################
cmake_minimum_required(VERSION 3.10..3.10)

# Use ccache if available
mark_as_advanced(CCACHE_FOUND)
find_program(CCACHE_FOUND ccache)
if(CCACHE_FOUND)
  set_property(GLOBAL PROPERTY RULE_LAUNCH_COMPILE ccache)
  set_property(GLOBAL PROPERTY RULE_LAUNCH_LINK ccache)
  message(STATUS "CCache is enabled")

  # Configure ccache for pch headers
  execute_process(
    COMMAND ${CCACHE_FOUND}
            --set-config=sloppiness=pch_defines,time_macros,include_file_mtime
  )
endif()

# ##############################################################################
# Project name                        #
# ##############################################################################
project(NS3 CXX C)

file(STRINGS VERSION NS3_VER)

# common options
option(NS3_ASSERT "Enable assert on failure" OFF)
option(NS3_DES_METRICS "Enable DES Metrics event collection" OFF)
option(NS3_EXAMPLES "Enable examples to be built" OFF)
option(NS3_LOG "Enable logging to be built" OFF)
option(NS3_TESTS "Enable tests to be built" OFF)

# fd-net-device options
option(NS3_EMU "Build with emulation support" ON)
option(NS3_PLANETLAB "Build with Planetlab support" OFF)
option(NS3_TAP "Build with Tap support" ON)

# maintenance and documentation
option(NS3_CLANG_FORMAT "Enforce cody style with clang-format" OFF)
option(NS3_CLANG_TIDY "Use clang-tidy static analysis" OFF)
option(NS3_CLANG_TIMETRACE
       "Collect compilation statistics to analyze the build process" OFF
)
option(NS3_COVERAGE "Enable code coverage measurements and report generation"
       OFF
)
option(NS3_COVERAGE_ZERO_COUNTERS
       "Zero lcov counters before running. Requires NS3_COVERAGE=ON" OFF
)
option(NS3_DOCS "Generate documentation" OFF)
option(NS3_INCLUDE_WHAT_YOU_USE
       "Use IWYU to determine unnecessary headers included" OFF
)
option(NS3_LINK_WHAT_YOU_USE
       "Use LWYU to determine unnecessary linked libraries" OFF
)
option(NS3_SANITIZE "Build with address, leak and undefined sanitizers" OFF)
option(NS3_SANITIZE_MEMORY "Build with memory sanitizer" OFF)
option(NS3_SCAN_PYTHON_BINDINGS "Scan python bindings" OFF)

# 3rd-party libraries/programs
option(NS3_NETANIM "Build netanim" OFF)

# other options
option(NS3_ENABLE_BUILD_VERSION "Embed version info into libraries" OFF)
option(NS3_GNUPLOT "Build with Gnuplot support" OFF)
option(NS3_GSL "Build with GSL support" ON)
option(NS3_GTK3 "Build with GTK3 support" ON)
option(NS3_LINK_TIME_OPTIMIZATION "Build with link-time optimization" OFF)
option(NS3_MONOLIB
       "Build a single shared ns-3 library and link it against executables" OFF
)
option(NS3_MPI "Build with MPI support" ON)
option(NS3_NATIVE_OPTIMIZATIONS "Build with -march=native -mtune=native" OFF)
option(NS3_NSC "Build with NSC support" OFF) # currently not supported
set(NS3_OUTPUT_DIRECTORY "" CACHE STRING "Directory to store built artifacts")
option(NS3_PRECOMPILE_HEADERS
       "Precompile module headers to speed up compilation" ON
)
option(NS3_PTHREAD "Build with pthread support" ON)
option(NS3_PYTHON_BINDINGS "Build ns-3 python bindings" OFF)
option(NS3_REALTIME "Build with realtime support" ON)
option(NS3_SQLITE "Build with SQLite support" ON)
option(NS3_STATIC "Build a static ns-3 library and link it against executables"
       OFF
)
option(NS3_VISUALIZER "Build visualizer module" OFF)
option(NS3_WARNINGS "Enable compiler warnings" ON)
option(NS3_WARNINGS_AS_ERRORS
       "Treat warnings as errors. Requires NS3_WARNINGS=ON" ON
)

# Options that either select which modules will get built or disable modules
set(NS3_ENABLED_MODULES ""
    CACHE STRING "List of modules to enable (e.g. core;network;internet)"
)
set(NS3_DISABLED_MODULES ""
    CACHE STRING "List of modules to disable (e.g. lte;wimax;wave)"
)

# Include macros used below
include(buildsupport/macros_and_definitions.cmake)

# Scan module libraries
subdirlist(libs_to_build ${CMAKE_SOURCE_DIR}/src)

# Scan contribution libraries
subdirlist(contrib_libs_to_build ${CMAKE_SOURCE_DIR}/contrib)

# Before filtering, we need to load settings from .ns3rc
parse_ns3rc(ns3rc_enabled_modules ns3rc_examples_enabled ns3rc_tests_enabled)

# After scanning modules, we can filter enabled and disabled ones
filter_enabled_and_disabled_modules(
  libs_to_build contrib_libs_to_build NS3_ENABLED_MODULES NS3_DISABLED_MODULES
  ns3rc_enabled_modules
)

# ##############################################################################
# Process options                     #
# ##############################################################################
process_options()

# ##############################################################################
# Add subdirectories                  #
# ##############################################################################
# Build NS3 library core
add_subdirectory(src)

# Build NS library examples
add_subdirectory(examples)

# Build scratch/simulation scripts
add_subdirectory(scratch)

# Build test utils
add_subdirectory(utils)

# Workaround for missing waf files used by test.py
generate_c4che_cachepy()
generate_buildstatus()
generate_fakewaflock()
write_fakewaf_config()

# Export package targets when installing
ns3_cmake_package()