cmake_minimum_required(VERSION 3.20.0)

project(windrpc_tests C)

# Nanopb 소스 땡겨오기
include(FetchContent)
FetchContent_Declare(Nanopb
        GIT_REPOSITORY https://github.com/nanopb/nanopb
        OVERRIDE_FIND_PACKAGE)
FetchContent_MakeAvailable(Nanopb)

find_package(Nanopb REQUIRED)
include_directories(${NANOPB_INCLUDE_DIRS})
include(${FETCHCONTENT_BASE_DIR}/nanopb-src/extra/FindNanopb.cmake)

# 생성된 코드들의 인클루드 경로 및 Nanopb 동적 생성 설정
if(USE_FLAT_MODE)
    set(GEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/generated_flat)
else()
    set(GEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/generated)
endif()

include_directories(${GEN_DIR})

# 패키지 서브디렉토리를 인클루드 경로로 동적 추가
file(GLOB PKG_DIRS RELATIVE ${GEN_DIR} ${GEN_DIR}/*)
foreach(DIR ${PKG_DIRS})
    if(IS_DIRECTORY ${GEN_DIR}/${DIR})
        include_directories(${GEN_DIR}/${DIR})
    endif()
endforeach()

# GEN_DIR 내부의 모든 .proto 파일 동적 검색
file(GLOB_RECURSE PROTO_FILES "${GEN_DIR}/*.proto")

# Proto 파일들로부터 C 소스코드 생성
nanopb_generate_cpp(TARGET test_protos RELPATH ${GEN_DIR} ${PROTO_FILES})

# 테스트 바이너리 생성 (Double Buffer & In-place Buffer 전용 테스트 각각 생성)
if(USE_FLAT_MODE)
    # 1. Double Buffer 모드 테스트 바이너리
    add_executable(run_tests_double 
            test_c_rpc_flat.c 
            ${GEN_DIR}/windrpc.c
    )
    target_compile_definitions(run_tests_double PRIVATE WINDRPC_USE_INPLACE_BUFFER=0)
    target_link_libraries(run_tests_double test_protos)

    # 2. In-place Buffer 모드 테스트 바이너리
    add_executable(run_tests_inplace 
            test_c_rpc_flat.c 
            ${GEN_DIR}/windrpc.c
    )
    target_compile_definitions(run_tests_inplace PRIVATE WINDRPC_USE_INPLACE_BUFFER=1)
    target_link_libraries(run_tests_inplace test_protos)

    # 하위 호환성 및 기존 별칭 유지
    add_executable(run_tests 
            test_c_rpc_flat.c 
            ${GEN_DIR}/windrpc.c
    )
    target_compile_definitions(run_tests PRIVATE WINDRPC_USE_INPLACE_BUFFER=0)
    target_link_libraries(run_tests test_protos)
else()
    add_executable(run_tests 
            test_c_rpc.c 
            ${GEN_DIR}/windrpc.c
    )
    target_link_libraries(run_tests test_protos)
endif()
