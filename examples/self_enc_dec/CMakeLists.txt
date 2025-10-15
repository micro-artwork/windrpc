cmake_minimum_required(VERSION 3.20.0)

project(self_enc_dec C)

include(FetchContent)
FetchContent_Declare(Nanopb
        GIT_REPOSITORY https://github.com/nanopb/nanopb
        OVERRIDE_FIND_PACKAGE)
FetchContent_MakeAvailable(Nanopb)

find_package(Nanopb REQUIRED)
include_directories(${NANOPB_INCLUDE_DIRS})
include(${FETCHCONTENT_BASE_DIR}/nanopb-src/extra/FindNanopb.cmake)

nanopb_generate_cpp(TARGET protos RELPATH protos
                                        protos/bitnari/windrpc/service/common.proto
                                        protos/bitnari/windrpc/service/led.proto
                                        protos/bitnari/windrpc/service/power.proto
                                        protos/bitnari/windrpc/types/types.proto
                                        protos/bitnari/windrpc/core/windrpc.proto
                                        )
# include_directories(rpc)
include_directories(server)
# Create your executable.
add_executable(app main.c 
                server/windrpc.c
                )

target_link_libraries(app protos)
