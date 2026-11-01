cmake_minimum_required(VERSION 3.21)
project(agents-opencode VERSION 3.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
find_package(Qt6 6.5 REQUIRED COMPONENTS Core Widgets)

add_executable(agents-opencode WIN32 MACOSX_BUNDLE
    src/main.cpp src/MainWindow.h src/MainWindow.cpp
    src/Project.h src/Project.cpp resources.qrc)
target_link_libraries(agents-opencode PRIVATE Qt6::Core Qt6::Widgets)
if(APPLE)
    set_target_properties(agents-opencode PROPERTIES
      MACOSX_BUNDLE_BUNDLE_NAME "Agents OpenCode"
      MACOSX_BUNDLE_GUI_IDENTIFIER "dev.agentsopencode.manager")
endif()
install(TARGETS agents-opencode BUNDLE DESTINATION . RUNTIME DESTINATION bin)

include(CTest)
if(BUILD_TESTING)
    find_package(Qt6 6.5 REQUIRED COMPONENTS Test)
    add_executable(agents-opencode-tests tests/ProjectTests.cpp src/Project.cpp src/Project.h resources.qrc)
    target_link_libraries(agents-opencode-tests PRIVATE Qt6::Core Qt6::Test)
    add_test(NAME project-config COMMAND agents-opencode-tests)
endif()
