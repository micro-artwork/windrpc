# proto/generator.py
import yaml
import os
import sys
from utils import spec_validator
from utils.loader import LineNumberLoader
from utils.converter import to_pascal_case
from utils.spec import merge_specs
from utils.file import copy, read_lines, write


def _get_template_file_path(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, f'templates/{file_name}')


def _get_service_commands(spec_data):
    cmd_dict = dict()
    services = spec_data.get('services', [])
    for service in services:
        svc_name = service['name']
        cmd_dict[svc_name] = []
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == 'REQUEST_ONLY':
                resp = 'WINDRPC_WITHOUT_RESP'
            else:
                resp = 'WINDRPC_WITH_RESP'
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            cmd_dict[svc_name].append({
                'name': rpc_name,
                'resp': resp
            })
    return cmd_dict


def _get_rpc_types(rpc, service_name, package_name):
    prefix = package_name.replace('/', '_').replace('-', '_').replace('.', '_')
    rpc_type = rpc.get('type', '').upper()
    cmd = rpc.get('command', 'types.Empty')
    res = rpc.get('result', 'types.Empty')

    # Command type
    cmd_raw_pkg = None
    cmd_raw_msg = None
    if cmd in ['types.Empty', 'Empty']:
        cmd_c_type = "void"
        cmd_raw_pkg = "types"
        cmd_raw_msg = "Empty"
    elif '.' in cmd:
        cmd_raw_pkg, cmd_raw_msg = cmd.split('.')
        cmd_c_type = f"rpc_{cmd_raw_pkg}_{cmd_raw_msg}_t"
    elif cmd in ['uint32', 'int32', 'bool', 'uint64', 'int64', 'float', 'double']:
        cmd_c_type = f"{cmd}_t"
    else:
        cmd_raw_pkg = service_name
        cmd_raw_msg = cmd
        cmd_c_type = f"rpc_{service_name}_{cmd}_t"

    # Result type
    is_submsg = True
    res_fields = "NULL"
    res_raw_pkg = None
    res_raw_msg = None

    if rpc_type == 'REQUEST_ONLY' or res in ['types.Empty', 'Empty']:
        res_c_type = "void"
        is_submsg = False
        res_tag = "0"
        if res in ['types.Empty', 'Empty']:
            res_raw_pkg = "types"
            res_raw_msg = "Empty"
            res_fields = f"{prefix}_windrpc_types_Empty_fields"
    elif res in ['uint32', 'int32', 'bool', 'uint64', 'int64', 'float', 'double']:
        res_c_type = f"{res}_t"
        is_submsg = False
        res_tag = f"WINDRPC_SERVICE_RESPONSE_RESULT_TAG({service_name}, {rpc['name']})"
    elif '.' in res:
        res_raw_pkg, res_raw_msg = res.split('.')
        res_c_type = f"rpc_{res_raw_pkg}_{res_raw_msg}_t"
        res_fields = f"WINDRPC_TYPES_MSG_FIELDS({res_raw_msg})" if res_raw_pkg == 'types' else f"WINDRPC_SERVICE_MSG_FIELDS({res_raw_pkg}, {res_raw_msg})"
        res_tag = f"WINDRPC_SERVICE_RESPONSE_RESULT_TAG({service_name}, {rpc['name']})"
    else:
        res_raw_pkg = service_name
        res_raw_msg = res
        res_c_type = f"rpc_{service_name}_{res}_t"
        res_fields = f"WINDRPC_SERVICE_MSG_FIELDS({service_name}, {res})"
        res_tag = f"WINDRPC_SERVICE_RESPONSE_RESULT_TAG({service_name}, {rpc['name']})"

    if rpc_type == 'NOTIFICATION':
        sub_name = f"subscribe_{rpc['name']}"
        cmd_raw_pkg = "types"
        cmd_raw_msg = "Subscribe"
        cmd_c_type = "rpc_types_Subscribe_t"
        res_raw_pkg = "types"
        res_raw_msg = "Status"
        res_c_type = "rpc_types_Status_t"
        is_submsg = True
        res_fields = f"{prefix}_windrpc_types_Status_fields"
        res_tag = f"WINDRPC_SERVICE_RESPONSE_RESULT_TAG({service_name}, {sub_name})"

    return {
        'rpc_type': rpc_type,
        'cmd_type': cmd_c_type,
        'res_type': res_c_type,
        'is_submsg': is_submsg,
        'res_fields': res_fields,
        'res_tag': res_tag,
        'cmd_raw_pkg': cmd_raw_pkg,
        'cmd_raw_msg': cmd_raw_msg,
        'res_raw_pkg': res_raw_pkg,
        'res_raw_msg': res_raw_msg
    }


def _generate_rpc_index_enum(spec_data):
    services = spec_data.get('services', [])
    content = []
    content.append("typedef enum {\n")
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            rpc_name = rpc['name']
            if rpc.get('type', '').upper() == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            content.append(f"    {idx_name},\n")
    content.append("    WINDRPC_RPC_COUNT,\n")
    content.append("    WINDRPC_RPC_IDX_UNKNOWN = 0xFFFF\n")
    content.append("} windrpc_rpc_idx_t;\n")
    return "".join(content)


def _generate_res_payload_union(spec_data, package_name):
    services = spec_data.get('services', [])
    content = []
    content.append("union windrpc_res_payload {\n")
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            info = _get_rpc_types(rpc, svc_name, package_name)
            rpc_name = rpc['name']
            if info['rpc_type'] == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            if info['res_type'] != 'void':
                if info['res_raw_pkg'] and info['res_raw_msg']:
                    pkg = info['res_raw_pkg']
                    msg = info['res_raw_msg']
                    if pkg == 'types':
                        macro_type = f"WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_{msg})"
                    else:
                        macro_type = f"WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_{pkg}_{msg})"
                else:
                    macro_type = info['res_type']
                content.append(f"    {macro_type} {svc_name}_{rpc_name};\n")
    content.append("};\n")
    return "".join(content)


def _generate_dispatch_table(spec_data, package_name):
    services = spec_data.get('services', [])
    fw_decls = []
    table_entries = []

    table_entries.append("static const struct windrpc_handler_entry rpc_dispatch_table[WINDRPC_RPC_COUNT] = {\n")

    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            info = _get_rpc_types(rpc, svc_name, package_name)
            rpc_name = rpc['name']
            if info['rpc_type'] == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"

            exec_func = f"windrpc_on_{rpc_name}"

            if info['res_type'] == 'void':
                fw_decls.append(f"int32_t {exec_func}(const {info['cmd_type']} *req, void *context);\n")
            else:
                fw_decls.append(f"int32_t {exec_func}(const {info['cmd_type']} *req, {info['res_type']} *res, void *context);\n")

            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            has_res_str = "true" if info['rpc_type'] != 'REQUEST_ONLY' else "false"

            table_entries.append(f"    [{idx_name}] = {{\n")
            table_entries.append(f"        .execute = (int32_t (*)(const void *, void *, void *)){exec_func},\n")
            table_entries.append(f"        .has_response = {has_res_str},\n")
            table_entries.append(f"        .res_tag = {info['res_tag']},\n")
            table_entries.append(f"    }},\n")

    table_entries.append("};\n")
    return "".join(fw_decls) + "\n" + "".join(table_entries)


def _generate_get_command_tag_and_index_funcs(spec_data, package_name):
    services = spec_data.get('services', [])
    content = []

    content.append("static uint32_t get_command_tag(windrpc_request_msg_t *req) {\n")
    content.append("    switch (req->which_service) {\n")
    for service in services:
        svc_name = service['name']
        content.append(f"        case WINDRPC_SERVICE_REQUEST_TAG({svc_name}):\n")
        content.append(f"            return req->service.{svc_name}.which_command;\n")
    content.append("        default:\n")
    content.append("            return 0;\n")
    content.append("    }\n")
    content.append("}\n\n")

    content.append("static windrpc_rpc_idx_t windrpc_get_rpc_index(uint32_t service_tag, uint32_t command_tag) {\n")
    content.append("    switch (service_tag) {\n")
    for service in services:
        svc_name = service['name']
        content.append(f"        case WINDRPC_SERVICE_REQUEST_TAG({svc_name}):\n")
        content.append("            switch (command_tag) {\n")
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            content.append(f"                case WINDRPC_SERVICE_REQUEST_CMD_TAG({svc_name}, {rpc_name}):\n")
            content.append(f"                    return {idx_name};\n")
        content.append("            }\n")
        content.append("            break;\n")
    content.append("        default:\n")
    content.append("            break;\n")
    content.append("    }\n")
    content.append("    return WINDRPC_RPC_IDX_UNKNOWN;\n")
    content.append("}\n\n")

    content.append("static const void *windrpc_get_req_ptr(windrpc_request_msg_t *req, windrpc_rpc_idx_t idx) {\n")
    content.append("    switch (idx) {\n")
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            content.append(f"        case {idx_name}:\n")
            content.append(f"            return &req->service.{svc_name}.command.{rpc_name};\n")
    content.append("        default:\n")
    content.append("            return NULL;\n")
    content.append("    }\n")
    content.append("}\n\n")

    content.append("static void *windrpc_get_res_ptr(windrpc_response_msg_t *resp, windrpc_rpc_idx_t idx) {\n")
    content.append("    switch (idx) {\n")
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            if rpc_type == 'REQUEST_ONLY':
                continue
            rpc_name = rpc['name']
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            content.append(f"        case {idx_name}:\n")
            content.append(f"            return &resp->service.{svc_name}.result.{rpc_name};\n")
    content.append("        default:\n")
    content.append("            return NULL;\n")
    content.append("    }\n")
    content.append("}\n\n")

    content.append("static void windrpc_set_response_result_tag(windrpc_response_msg_t *resp, windrpc_rpc_idx_t idx, uint32_t tag) {\n")
    content.append("    switch (idx) {\n")
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            if rpc_type == 'REQUEST_ONLY':
                continue
            rpc_name = rpc['name']
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            content.append(f"        case {idx_name}:\n")
            content.append(f"            resp->service.{svc_name}.which_result = tag;\n")
            content.append(f"            break;\n")
    content.append("        default:\n")
    content.append("            break;\n")
    content.append("    }\n")
    content.append("}\n")

    return "".join(content)


def _generate_rpc_event_enum(spec_data):
    services = spec_data.get('services', [])
    content = []
    content.append("\n// Auto-generated WindRPC Event Enum & Event Flags\n")
    content.append("typedef enum {\n")
    events_found = 0
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            if rpc.get('type', '').upper() == 'NOTIFICATION':
                rpc_name = rpc['name']
                event_enum = f"WINDRPC_EVENT_{rpc_name.upper()}"
                content.append(f"    {event_enum} = {events_found},\n")
                events_found += 1
    content.append(f"    WINDRPC_EVENT_COUNT = {events_found}\n")
    content.append("} windrpc_event_t;\n\n")
    content.append("#ifndef WINDRPC_EVENT_FLAG\n")
    content.append("#define WINDRPC_EVENT_FLAG(x) (1U << (x))\n")
    content.append("#endif\n\n")
    return "".join(content)


def _generate_common_header_content(spec_data, package_name):
    file_path = _get_template_file_path('windrpc_common.h')
    cmd_dict = _get_service_commands(spec_data)
    header_paths = []
    for svc_name in cmd_dict:
        header_paths.append(
            f'#include "{package_name}/windrpc/service/{svc_name}.pb.h"\n')

    content = []

    try:
        lines = read_lines(file_path)
        for line in lines:
            if '--WINDRPC_PB_HEADERS' in line:
                content.append(line)
                content.extend(header_paths)
                content.append('\n')
            elif '--WINDRPC_PACKAGE_NAME' in line:
                content.append(line)
                content.append(
                    f"#define WINDRPC_PACKAGE_NAME {package_name}\n")
            elif '--WINDRPC_RPC_INDEX_ENUM' in line:
                content.append(line)
                content.append(_generate_rpc_index_enum(spec_data))
                content.append(_generate_rpc_event_enum(spec_data))
            else:
                content.append(line)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")
    content.append('\n')
    return "".join(content)


def _generate_typedef_aliases(spec_data, package_name):
    prefix = package_name.replace('/', '_').replace('-', '_').replace('.', '_')
    services = spec_data.get('services', [])

    content = []
    content.append(
        "/* ========================================================================== */\n")
    content.append(
        "/*                      WindRPC Type Aliases (Shortcuts)                      */\n")
    content.append(
        "/* ========================================================================== */\n\n")

    for service in services:
        svc_name = service['name']
        messages = service.get('messages', [])
        for msg in messages:
            msg_name = msg['name']
            nanopb_type = f"{prefix}_windrpc_service_{svc_name}_{msg_name}"
            alias_type = f"rpc_{svc_name}_{msg_name}_t"
            content.append(f"typedef {nanopb_type} {alias_type};\n")

    types_section = spec_data.get('types', {})
    if isinstance(types_section, dict):
        messages = types_section.get('messages', [])
        for msg in messages:
            msg_name = msg['name']
            nanopb_type = f"{prefix}_windrpc_types_{msg_name}"
            alias_type = f"rpc_types_{msg_name}_t"
            content.append(f"typedef {nanopb_type} {alias_type};\n")

    content.append("\n")
    return "".join(content)



def _generate_windrpc_header_content(spec_data, package_name):
    file_path = _get_template_file_path('windrpc.h')
    content = []
    aliases = _generate_typedef_aliases(spec_data, package_name)
    notify_decls = _generate_notify_declarations(spec_data, package_name)

    try:
        lines = read_lines(file_path)
        for line in lines:
            if '--WINDRPC_TYPEDEF_ALIASES' in line:
                content.append(aliases)
            elif '--WINDRPC_NOTIFY_DECLARATIONS' in line:
                content.append(notify_decls)
            else:
                content.append(line)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")

    return "".join(content)


def _generate_flat_dispatch_table(spec_data, package_name):
    prefix = package_name.replace('/', '_').replace('-', '_').replace('.', '_')
    services = spec_data.get('services', [])
    content = []

    content.append("// Core service handler prototypes for flat mode\n")
    content.append("int32_t windrpc_on_ping(const void *req, uint32_t *res, void *context);\n")
    content.append("int32_t windrpc_on_get_device_info(const void *req, rpc_common_DeviceInfo_t *res, void *context);\n\n")

    content.append("// Service RPC handler prototypes for flat mode\n")
    for service in services:
        svc_name = service['name']
        if svc_name == 'common':  # already hardcoded above
            continue
        for rpc in service.get('rpcs', []):
            rpc_name = rpc['name']
            info = _get_rpc_types(rpc, svc_name, package_name)
            cmd_arg = f"const {info['cmd_type']} *req" if info['cmd_type'] != 'void' else "const void *req"
            res_arg = f"{info['res_type']} *res" if info['res_type'] != 'void' else "void *res"
            exec_name = f"windrpc_on_subscribe_{rpc_name}" if info['rpc_type'] == 'NOTIFICATION' else f"windrpc_on_{rpc_name}"
            content.append(f"int32_t {exec_name}({cmd_arg}, {res_arg}, void *context);\n")

    content.append("\n// Flat req/res static buffers\n")
    content.append("static uint32_t res_common_ping;\n")
    for service in services:
        svc_name = service['name']
        if svc_name == 'common':  # handled by core
            continue
        svc_id = service['id']
        for rpc in service.get('rpcs', []):
            info = _get_rpc_types(rpc, svc_name, package_name)
            cmd_type = info['cmd_type']
            res_type = info['res_type']
            if cmd_type != 'void':
                content.append(f"static {cmd_type} req_{svc_name}_{rpc['name']};\n")
            if res_type != 'void':
                content.append(f"static {res_type} res_{svc_name}_{rpc['name']};\n")

    content.append("\n")

    content.append("static void *windrpc_get_flat_req_struct(uint16_t rpc_id) {\n")
    content.append("    switch (rpc_id) {\n")
    for service in services:
        svc_name = service['name']
        if svc_name == 'common':  # handled by core
            continue
        svc_id = service['id']
        for rpc in service.get('rpcs', []):
            rpc_name = rpc['name']
            rpc_id = rpc['id']
            combined_id = (svc_id << 8) | rpc_id
            info = _get_rpc_types(rpc, svc_name, package_name)
            if info['cmd_type'] != 'void':
                content.append(f"        case 0x{combined_id:04X}:\n")
                content.append(f"            memset(&req_{svc_name}_{rpc_name}, 0, sizeof(req_{svc_name}_{rpc_name}));\n")
                content.append(f"            return &req_{svc_name}_{rpc_name};\n")
    content.append("        default: return NULL;\n")
    content.append("    }\n}\n\n")

    content.append("static void *windrpc_get_flat_res_struct(uint16_t rpc_id) {\n")
    content.append("    switch (rpc_id) {\n")
    content.append("        case 0x0601:\n")
    content.append("            res_common_ping = 0;\n")
    content.append("            return &res_common_ping;\n")
    for service in services:
        svc_name = service['name']
        if svc_name == 'common':  # handled by core
            continue
        svc_id = service['id']
        for rpc in service.get('rpcs', []):
            info = _get_rpc_types(rpc, svc_name, package_name)
            has_response = info['rpc_type'] in ('REQUEST_RESPONSE', 'NOTIFICATION')
            if not has_response or info['res_type'] == 'void':
                continue
            rpc_name = rpc['name']
            rpc_id = rpc['id']
            combined_id = (svc_id << 8) | rpc_id
            content.append(f"        case 0x{combined_id:04X}:\n")
            content.append(f"            memset(&res_{svc_name}_{rpc_name}, 0, sizeof(res_{svc_name}_{rpc_name}));\n")
            content.append(f"            return &res_{svc_name}_{rpc_name};\n")
    content.append("        default: return NULL;\n")
    content.append("    }\n}\n\n")

    content.append("static const struct windrpc_handler_entry windrpc_dispatch_table[] = {\n")
    content.append("    {\n")
    content.append("        .rpc_id = 0x0601,\n")
    content.append("        .execute = (int32_t (*)(const void *, void *, void *))windrpc_on_ping,\n")
    content.append("        .has_response = true,\n")
    content.append(f"        .req_fields = {prefix}_windrpc_types_Empty_fields,\n")
    content.append("        .res_fields = NULL\n")
    content.append("    },\n")
    content.append("    {\n")
    content.append("        .rpc_id = 0x0602,\n")
    content.append("        .execute = (int32_t (*)(const void *, void *, void *))windrpc_on_get_device_info,\n")
    content.append("        .has_response = true,\n")
    content.append(f"        .req_fields = {prefix}_windrpc_types_Empty_fields,\n")
    content.append(f"        .res_fields = {prefix}_windrpc_service_common_DeviceInfo_fields\n")
    content.append("    },\n")
    for service in services:
        svc_name = service['name']
        if svc_name == 'common':  # already hardcoded as 0x0601 / 0x0602 above
            continue
        svc_id = service['id']
        for rpc in service.get('rpcs', []):
            rpc_name = rpc['name']
            rpc_id = rpc['id']
            combined_id = (svc_id << 8) | rpc_id
            info = _get_rpc_types(rpc, svc_name, package_name)
            has_response = info['rpc_type'] in ('REQUEST_RESPONSE', 'NOTIFICATION')

            cmd_pkg = info['cmd_raw_pkg']
            cmd_msg = info['cmd_raw_msg']
            if cmd_pkg and cmd_msg:
                if cmd_pkg == 'types':
                    cmd_fields = f"{prefix}_windrpc_types_{cmd_msg}_fields"
                else:
                    cmd_fields = f"{prefix}_windrpc_service_{cmd_pkg}_{cmd_msg}_fields"
            else:
                cmd_fields = "NULL"

            res_pkg = info['res_raw_pkg']
            res_msg = info['res_raw_msg']
            if has_response and res_pkg and res_msg:
                if res_pkg == 'types':
                    res_fields = f"{prefix}_windrpc_types_{res_msg}_fields"
                else:
                    res_fields = f"{prefix}_windrpc_service_{res_pkg}_{res_msg}_fields"
            else:
                res_fields = "NULL"

            exec_name = f"windrpc_on_subscribe_{rpc_name}" if info['rpc_type'] == 'NOTIFICATION' else f"windrpc_on_{rpc_name}"

            content.append("    {\n")
            content.append(f"        .rpc_id = 0x{combined_id:04X},\n")
            content.append(f"        .execute = (int32_t (*)(const void *, void *, void *)){exec_name},\n")
            content.append(f"        .has_response = {'true' if has_response else 'false'},\n")
            content.append(f"        .req_fields = {cmd_fields},\n")
            content.append(f"        .res_fields = {res_fields}\n")
            content.append("    },\n")
    content.append("};\n\n")

    content.append("static const struct windrpc_handler_entry *windrpc_find_flat_handler(uint16_t rpc_id) {\n")
    content.append("    size_t count = sizeof(windrpc_dispatch_table) / sizeof(windrpc_dispatch_table[0]);\n")
    content.append("    for (size_t i = 0; i < count; i++) {\n")
    content.append("        if (windrpc_dispatch_table[i].rpc_id == rpc_id) return &windrpc_dispatch_table[i];\n")
    content.append("    }\n")
    content.append("    return NULL;\n")
    content.append("}\n\n")
    return "".join(content)


def _generate_windrpc_c_content(spec_data, package_name):
    file_path = _get_template_file_path('windrpc.c')
    content = []
    try:
        lines = read_lines(file_path)
        for line in lines:
            if '--WINDRPC_DISPATCH_TABLE' in line:
                content.append(line)
                content.append(_generate_dispatch_table(spec_data, package_name))
                content.append('\n')
            elif '--WINDRPC_FLAT_DISPATCH_TABLE' in line:
                content.append(line)
                content.append(_generate_flat_dispatch_table(spec_data, package_name))
                content.append('\n')
            elif '--WINDRPC_GET_COMMAND_TAG_AND_INDEX_FUNCS' in line:
                content.append(line)
                content.append(_generate_get_command_tag_and_index_funcs(spec_data, package_name))
                content.append('\n')
            else:
                content.append(line)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")
    content.append('\n')
    return "".join(content)


def write_smart_merge(file_path, new_content):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Generated {file_path}")
        return

    # Create backup copy of existing file before merging
    backup_path = file_path + ".bak"
    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"Created backup of existing file at: {backup_path}")
    except Exception as e:
        print(f"Warning: Failed to create backup file: {e}")

    with open(file_path, 'r', encoding='utf-8') as f:
        existing_content = f.read()

    blocks = new_content.split('\n\n')
    additions = []

    for block in blocks:
        block_strip = block.strip()
        if not block_strip:
            continue

        # Skip header comments or license headers
        if block_strip.startswith('/**') or block_strip.startswith('#include') or block_strip.startswith('LOG_MODULE_REGISTER'):
            continue

        lines = block_strip.split('\n')
        sig_line = ""
        for line in lines:
            if not line.strip().startswith('/*') and not line.strip().startswith('*') and not line.strip().startswith('//'):
                sig_line = line
                break

        if not sig_line or sig_line.startswith('struct ') or sig_line.startswith('K_') or sig_line.startswith('typedef '):
            continue  # Ignore comment or static struct/macro declaration blocks without actual handler code

        tokens = sig_line.replace('(', ' ').replace(')', ' ').replace(
            '{', ' ').replace('=', ' ').split()

        key_token = None
        for token in tokens:
            if token.startswith('windrpc_on_') or token.startswith('windrpc_notify_') or token.endswith('_service') or token == 'windrpc_services' or token.startswith('rpc_'):
                key_token = token
                break

        if key_token:
            if key_token in existing_content:
                continue
            additions.append(block)

    if additions:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(
                "\n\n/* ========================================================================== */\n")
            f.write(
                "/* --- AUTO-GENERATED ADDITIONS (New RPCs / Services) ---                     */\n")
            f.write(
                "/* ========================================================================== */\n\n")
            f.write("\n\n".join(additions))
            f.write("\n")
        print(f"Updated {file_path} with new additions")
    else:
        print(f"No new callbacks to merge into {file_path}")


def _generate_callbacks_skeleton(spec_data, package_name):
    services = spec_data.get('services', [])

    content = []
    content.append("/**\n")
    content.append(" * @file windrpc_callbacks.c\n")
    content.append(
        " * @brief Auto-generated Callbacks Skeleton for WindRPC server.\n")
    content.append(
        " * @note Copy this file as windrpc_callbacks.c and implement your logic.\n")
    content.append(" */\n\n")
    content.append('#include "windrpc.h"\n')
    content.append('#include <zephyr/logging/log.h>\n')
    content.append('#include <stdio.h>\n\n')
    content.append('LOG_MODULE_REGISTER(windrpc_callbacks, LOG_LEVEL_INF);\n\n')

    for service in services:
        svc_name = service['name']
        if svc_name == 'common':
            continue
        content.append(
            f"/* ========================================================================== */\n")
        content.append(
            f"/*                             Service: {svc_name}                           */\n")
        content.append(
            f"/* ========================================================================== */\n\n")

        for rpc in service.get('rpcs', []):
            info = _get_rpc_types(rpc, svc_name, package_name)
            rpc_name = rpc['name']

            cmd_arg = f"const {info['cmd_type']} *req" if info['cmd_type'] != 'void' else "const void *req"
            res_arg = f"{info['res_type']} *res" if info['res_type'] != 'void' else "void *res"

            if info['rpc_type'] == 'NOTIFICATION':
                sub_name = f"subscribe_{rpc_name}"
                content.append(f"/**\n")
                content.append(f" * @brief Execute handler for subscribing to {rpc_name}\n")
                content.append(f" */\n")
                content.append(f"int32_t windrpc_on_{sub_name}(const rpc_types_Subscribe_t *req, void *res, void *context) {{\n")
                content.append(f"    ARG_UNUSED(res);\n")
                content.append(f"    LOG_INF(\"Execute subscription: {sub_name}, enable=%d\", req ? req->enable : 0);\n")
                content.append(f"    // [USER TODO]: Implement subscription enable/disable logic based on req->enable\n")
                content.append(f"    // Example: if (req->enable) windrpc_notify_{rpc_name}(...);\n")
                content.append(f"    return 0;\n")
                content.append(f"}}\n\n")
            elif info['rpc_type'] == 'REQUEST_ONLY':
                content.append(f"/**\n")
                content.append(f" * @brief Execute handler for RPC {rpc_name} (no response)\n")
                content.append(f" */\n")
                content.append(f"int32_t windrpc_on_{rpc_name}({cmd_arg}, void *res, void *context) {{\n")
                if info['cmd_type'] == 'void':
                    content.append(f"    ARG_UNUSED(req);\n")
                content.append(f"    ARG_UNUSED(res);\n")
                content.append(f"    LOG_INF(\"Execute RPC: {rpc_name}\");\n")
                content.append(f"    // [USER TODO]: Implement execution logic here\n")
                content.append(f"    return 0;\n")
                content.append(f"}}\n\n")
            else: # REQUEST_RESPONSE
                content.append(f"/**\n")
                content.append(f" * @brief Execute handler for RPC {rpc_name}\n")
                content.append(f" */\n")
                content.append(f"int32_t windrpc_on_{rpc_name}({cmd_arg}, {res_arg}, void *context) {{\n")
                if info['cmd_type'] == 'void':
                    content.append(f"    ARG_UNUSED(req);\n")
                if info['res_type'] == 'void':
                    content.append(f"    ARG_UNUSED(res);\n")
                content.append(f"    LOG_INF(\"Execute RPC: {rpc_name}\");\n")
                content.append(f"    // [USER TODO]: Implement execution logic and populate response result (*res) here\n")
                content.append(f"    return 0;\n")
                content.append(f"}}\n\n")

    return "".join(content)


def _generate_notify_skeleton(spec_data, package_name):
    prefix = package_name.replace('/', '_').replace('-', '_')
    envelope_mode = spec_data.get('config', {}).get('envelope_mode', 'flat')
    services = spec_data.get('services', [])

    content = []
    content.append("/**\n")
    content.append(" * @file windrpc_notify.c\n")
    content.append(
        " * @brief Auto-generated Notification Helper Skeleton for WindRPC.\n")
    content.append(
        " * @note Copy/incorporate this into your notification thread.\n")
    content.append(" */\n\n")
    content.append('#include "windrpc.h"\n')
    content.append('#include <stdio.h>\n\n')

    has_notif = False
    for service in services:
        svc_name = service['name']
        svc_id = service.get('id', 0)
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']

            if rpc_type == 'NOTIFICATION':
                has_notif = True
                event_type = rpc.get('event', rpc.get('result', 'types.Empty'))
                rpc_id = rpc['id']
                event_combined_id = (svc_id << 8) | (rpc_id | 0x80)

                if '.' in event_type:
                    res_pkg, res_msg = event_type.split('.')
                    c_type = f"rpc_{res_pkg}_{res_msg}_t" if res_pkg != 'types' else f"rpc_types_{res_msg}_t"
                    fields_macro = f"{prefix}_windrpc_types_{res_msg}_fields" if res_pkg == 'types' else f"{prefix}_windrpc_service_{res_pkg}_{res_msg}_fields"
                else:
                    c_type = f"rpc_{svc_name}_{event_type}_t"
                    fields_macro = f"{prefix}_windrpc_service_{svc_name}_{event_type}_fields"

                content.append("/**\n")
                content.append(
                    f" * @brief Notify helper for event: {rpc_name} (Event ID: 0x{event_combined_id:04X})\n")
                content.append(" */\n")

                if envelope_mode == 'flat':
                    content.append(
                        f"int32_t windrpc_notify_{rpc_name}(const {c_type} *data, struct windrpc_transaction *txn) {{\n")
                    content.append(f"    if (!data || !txn) return -1;\n")
                    content.append(f"    struct windrpc_buffer *buffer = &txn->buffer;\n")
                    content.append(f"    uint8_t *tx_data = buffer->tx_data;\n")
                    content.append(f"    if (buffer->tx_size < 5) return -1;\n\n")
                    content.append(f"    uint16_t event_id = 0x{event_combined_id:04X};\n")
                    content.append(f"    tx_data[0] = (uint8_t)((event_id >> 8) & 0xFF);\n")
                    content.append(f"    tx_data[1] = (uint8_t)(event_id & 0xFF);\n")
                    content.append(f"    tx_data[2] = 0; // seq_id = 0 for server push notification\n")
                    content.append(f"    tx_data[3] = 0;\n\n")
                    content.append(
                        f"    pb_ostream_t ostream = pb_ostream_from_buffer(&tx_data[5], buffer->tx_size - 5);\n")
                    content.append(
                        f"    if (!pb_encode(&ostream, {fields_macro}, data)) {{\n")
                    content.append(
                        f"        LOG_ERR(\"Failed to encode notification event '{rpc_name}': %s\", PB_GET_ERROR(&ostream));\n")
                    content.append(f"        buffer->bytes_written = 0;\n")
                    content.append(f"        return -1;\n")
                    content.append(f"    }}\n\n")
                    content.append(f"    tx_data[4] = (uint8_t)ostream.bytes_written;\n")
                    content.append(f"    buffer->bytes_written = 5 + (uint16_t)ostream.bytes_written;\n")
                    content.append(
                        f"    LOG_DBG(\"Encoded flat notification '{rpc_name}'. Total Size: %u bytes\", buffer->bytes_written);\n")
                    content.append(f"    return 0;\n")
                    content.append(f"}}\n\n")
                else:
                    content.append(
                        f"int32_t windrpc_notify_{rpc_name}(const {c_type} *data, struct windrpc_transaction *txn) {{\n")
                    content.append(f"    if (!data || !txn) return -1;\n")
                    content.append(
                        f"    {prefix}_windrpc_core_ServerMessage notif_msg = {prefix}_windrpc_core_ServerMessage_init_zero;\n")
                    content.append(
                        f"    notif_msg.which_payload = {prefix}_windrpc_core_ServerMessage_notification_tag;\n")
                    content.append(
                        f"    {prefix}_windrpc_core_Notification *notif = &notif_msg.payload.notification;\n")
                    content.append(
                        f"    notif->which_service = {prefix}_windrpc_core_Notification_{svc_name}_tag;\n")
                    content.append(
                        f"    notif->service.{svc_name}.which_event = {prefix}_windrpc_service_{svc_name}_Notification_{rpc_name}_tag;\n")
                    content.append(
                        f"    notif->service.{svc_name}.event.{rpc_name} = *data;\n\n")
                    content.append(f"    txn->operation.server_msg = notif_msg;\n")
                    content.append(f"    return windrpc_notify(txn);\n")
                    content.append(f"}}\n\n")

    if not has_notif:
        content.append(
            "// Note: No NOTIFICATION type RPCs found in specifications.\n")

    return "".join(content)


def _generate_notify_declarations(spec_data, package_name):
    services = spec_data.get('services', [])
    content = []
    content.append("\n/* Notification Function Declarations */\n")
    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == 'NOTIFICATION':
                event_type = rpc.get('event', rpc.get('result', 'types.Empty'))
                if '.' in event_type:
                    res_pkg, res_msg = event_type.split('.')
                    c_type = f"rpc_{res_pkg}_{res_msg}_t" if res_pkg != 'types' else f"rpc_types_{res_msg}_t"
                else:
                    c_type = f"rpc_{svc_name}_{event_type}_t"
                content.append(f"int32_t windrpc_notify_{rpc_name}(const {c_type} *data, struct windrpc_transaction *txn);\n")
    return "".join(content)


def _calculate_max_payload_size(spec_data):
    max_size = 64
    services = spec_data.get('services', [])
    types = spec_data.get('types', {})

    all_messages = []
    for svc in services:
        all_messages.extend(svc.get('messages', []))
    if isinstance(types, dict):
        all_messages.extend(types.get('messages', []))

    for msg in all_messages:
        msg_size = 0
        for field in msg.get('fields', []):
            f_type = field.get('type', '')
            f_prop = field.get('property', '')
            nanopb = field.get('nanopb', {})

            count = nanopb.get('max_count', 1) if f_prop == 'repeated' else 1

            if f_type in ['uint32', 'int32', 'fixed32', 'sfixed32', 'float']:
                base_len = 5
            elif f_type in ['uint64', 'int64', 'fixed64', 'sfixed64', 'double']:
                base_len = 10
            elif f_type in ['bool', 'enum']:
                base_len = 2
            elif f_type in ['string', 'bytes']:
                base_len = nanopb.get('max_length', nanopb.get('max_size', 64)) + 2
            else:
                base_len = 64

            msg_size += base_len * count

        if msg_size > max_size:
            max_size = msg_size

    return max_size


def _calculate_stack_and_buffer_sizes(spec_data):
    """Calculate WINDRPC_MAX_BUFFER_SIZE and WINDRPC_RECOMMENDED_STACK_SIZE from spec."""
    max_payload = _calculate_max_payload_size(spec_data)

    # 5B header + payload + COBS overhead safety
    max_buffer_size = max(256, max_payload + 64)

    # Align buffer size to power of 2 or 64-byte boundary
    max_buffer_size = (max_buffer_size + 63) & ~63

    # Recommended RTOS Stack Size (Zephyr thread context + buffers + driver stack)
    recommended_stack_size = max(2048, max_buffer_size * 2 + 1024)
    # Align stack size to 256-byte boundary for RTOS MPU alignment
    recommended_stack_size = (recommended_stack_size + 255) & ~255

    return max_buffer_size, recommended_stack_size, max_payload


def generate(core_spec_path, user_spec_path, output_dir, mode=None, rtos="zephyr", verbose=False):
    """
    주어진 YAML 스펙 파일들로부터 .proto와 .options 파일들을 생성합니다.
    """
    try:
        with open(core_spec_path, 'r', encoding='utf-8') as f:
            core_spec_data = yaml.load(f, Loader=LineNumberLoader)
    except FileNotFoundError:
        print(
            f"Error: Core spec file '{core_spec_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing core YAML file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(user_spec_path, 'r', encoding='utf-8') as f:
            user_spec_data = yaml.load(f, Loader=LineNumberLoader)
    except FileNotFoundError:
        print(
            f"Error: User spec file '{user_spec_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing user YAML file: {e}", file=sys.stderr)
        sys.exit(1)

    spec_data = merge_specs(core_spec_data, user_spec_data)
    if mode:
        if 'config' not in spec_data or not isinstance(spec_data['config'], dict):
            spec_data['config'] = {}
        spec_data['config']['envelope_mode'] = mode

    spec_validator.validate(spec_data, verbose=verbose)
    print("YAML Specification validation successful.")

    package_name = spec_data.get('package', 'default_package')
    # output_path = os.path.join(output_dir, package_name)
    output_path = output_dir
    os.makedirs(output_path, exist_ok=True)

    print("\nGenerating WindRPC server files...")

    # generate windrpc_common.h
    common_header_content = _generate_common_header_content(
        spec_data, package_name)
    file_path = os.path.join(output_path, f"windrpc_common.h")
    write(file_path, common_header_content)
    print(f"Generated {file_path}")

    winrpc_header_content = _generate_windrpc_header_content(
        spec_data, package_name)
    file_path = os.path.join(output_path, f"windrpc.h")
    write(file_path, winrpc_header_content)
    print(f"Generated {file_path}")

    # copy / update windrpc_config.h
    file_path = os.path.join(output_dir, 'windrpc_config.h')
    envelope_mode = spec_data.get('config', {}).get('envelope_mode', 'flat')
    mode_macro_val = "WINDRPC_ENVELOPE_FLAT" if envelope_mode == 'flat' else "WINDRPC_ENVELOPE_NESTED"

    max_buffer_size, recommended_stack_size, max_payload = _calculate_stack_and_buffer_sizes(spec_data)
    stack_and_buffer_defines = (
        f"/* Dynamically Calculated Stack & Buffer Sizes based on Specification */\n"
        f"#ifndef WINDRPC_MAX_BUFFER_SIZE\n"
        f"#define WINDRPC_MAX_BUFFER_SIZE {max_buffer_size} // Maximum Message Payload Size: {max_payload} B\n"
        f"#endif\n\n"
        f"#ifndef WINDRPC_RECOMMENDED_STACK_SIZE\n"
        f"#define WINDRPC_RECOMMENDED_STACK_SIZE {recommended_stack_size} // Recommended Thread Stack Size\n"
        f"#endif"
    )

    source_path = _get_template_file_path('windrpc_config.h')
    config_content = read_lines(source_path)
    config_str = "".join(config_content)
    config_str = config_str.replace(
        "#define WINDRPC_ENVELOPE_MODE WINDRPC_ENVELOPE_NESTED",
        f"#define WINDRPC_ENVELOPE_MODE {mode_macro_val}"
    )
    config_str = config_str.replace(
        "// --WINDRPC_STACK_AND_BUFFER_DEFINES",
        stack_and_buffer_defines
    )
    write(file_path, config_str)
    print(f"Generated/Updated {file_path} (envelope mode: {envelope_mode})")

    # generate windrpc.c
    windrpc_c_content = _generate_windrpc_c_content(spec_data, package_name)
    file_path = os.path.join(output_dir, 'windrpc.c')
    write(file_path, windrpc_c_content)
    print(f"Generated {file_path}")

    # generate callbacks skeleton
    callbacks_skeleton = _generate_callbacks_skeleton(spec_data, package_name)
    file_path = os.path.join(output_dir, "windrpc_callbacks.c")
    write_smart_merge(file_path, callbacks_skeleton)

    # generate notify skeleton
    notify_skeleton = _generate_notify_skeleton(spec_data, package_name)
    file_path = os.path.join(output_dir, "windrpc_notify.c")
    write_smart_merge(file_path, notify_skeleton)

