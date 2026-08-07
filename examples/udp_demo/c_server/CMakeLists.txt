cmake_minimum_required(VERSION 3.20.0)
project(windrpc_udp_server C)

set(CMAKE_C_STANDARD 99)

include(FetchContent)
FetchContent_Declare(Nanopb
    GIT_REPOSITORY https://github.com/nanopb/nanopb
    OVERRIDE_FIND_PACKAGE
)
FetchContent_MakeAvailable(Nanopb)

find_package(Nanopb REQUIRED)
include_directories(${NANOPB_INCLUDE_DIRS})
include_directories(${FETCHCONTENT_BASE_DIR}/nanopb-src)
include(${FETCHCONTENT_BASE_DIR}/nanopb-src/extra/FindNanopb.cmake)

set(GEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/generated)
include_directories(${GEN_DIR})
include_directories(${CMAKE_CURRENT_BINARY_DIR})

file(GLOB PKG_DIRS RELATIVE ${GEN_DIR} ${GEN_DIR}/*)
foreach(DIR ${PKG_DIRS})
    if(IS_DIRECTORY ${GEN_DIR}/${DIR})
        include_directories(${GEN_DIR}/${DIR})
        include_directories(${CMAKE_CURRENT_BINARY_DIR}/${DIR})
    endif()
endforeach()

file(GLOB_RECURSE PROTO_FILES "${GEN_DIR}/*.proto")
nanopb_generate_cpp(TARGET server_protos RELPATH ${GEN_DIR} ${PROTO_FILES})

# Get generated C files except the skeleton callbacks file (which is user-written in windrpc_callbacks.c)
file(GLOB WINDRPC_C_SRCS ${GEN_DIR}/*.c)
list(FILTER WINDRPC_C_SRCS EXCLUDE REGEX "windrpc_callbacks\\.c$")

add_executable(udp_server
    main.c
    windrpc_callbacks.c
    ${WINDRPC_C_SRCS}
)

target_link_libraries(udp_server server_protos)

if (WIN32)
    target_link_libraries(udp_server ws2_32)
endif()
