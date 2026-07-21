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


def _generate_dispatch_table(spec_data):
    services = spec_data.get('services', [])
    fw_decls = []
    table_entries = []

    table_entries.append("static const struct windrpc_handler_entry rpc_dispatch_table[WINDRPC_RPC_COUNT] = {\n")

    for service in services:
        svc_name = service['name']
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"

            has_res = (rpc_type != 'REQUEST_ONLY')
            exec_func = f"execute_{rpc_name}"
            enc_func = f"encode_{rpc_name}" if has_res else "NULL"

            fw_decls.append(f"int32_t {exec_func}(struct windrpc_operation *operation, void *context);\n")
            if has_res:
                fw_decls.append(f"void {enc_func}(windrpc_response_msg_t *response, void *context);\n")

            idx_name = f"WINDRPC_RPC_IDX_{svc_name.upper()}_{rpc_name.upper()}"
            has_res_str = "true" if has_res else "false"

            table_entries.append(f"    [{idx_name}] = {{\n")
            table_entries.append(f"        .decode_req = NULL,\n")
            table_entries.append(f"        .encode_res = {enc_func},\n")
            table_entries.append(f"        .execute = {exec_func},\n")
            table_entries.append(f"        .has_response = {has_res_str},\n")
            table_entries.append(f"    }},\n")

    table_entries.append("};\n")
    return "".join(fw_decls) + "\n" + "".join(table_entries)


def _generate_get_command_tag_and_index_funcs(spec_data):
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
    content.append("}\n")

    return "".join(content)


def _generate_common_header_content(spec_data, package_name):
    file_path = _get_template_file_path('windrpc_common.h')
    cmd_dict = _get_service_commands(spec_data)
    header_paths = [
        f'#include "{package_name}/windrpc/core/windrpc.pb.h"\n',
        f'#include "{package_name}/windrpc/types/types.pb.h"\n'
    ]
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
    try:
        lines = read_lines(file_path)
        for line in lines:
            content.append(line)
        aliases = _generate_typedef_aliases(spec_data, package_name)
        content.append("\n" + aliases)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")

    content.append('\n')
    return "".join(content)


def _generate_windrpc_c_content(spec_data, package_name):
    file_path = _get_template_file_path('windrpc.c')
    content = []
    try:
        lines = read_lines(file_path)
        for line in lines:
            if '--WINDRPC_DISPATCH_TABLE' in line:
                content.append(line)
                content.append(_generate_dispatch_table(spec_data))
                content.append('\n')
            elif '--WINDRPC_GET_COMMAND_TAG_AND_INDEX_FUNCS' in line:
                content.append(line)
                content.append(_generate_get_command_tag_and_index_funcs(spec_data))
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

        if block_strip.startswith('/**') or block_strip.startswith('#include'):
            continue

        lines = block_strip.split('\n')
        # Skip leading comments in block to find signature line
        sig_line = lines[0]
        for line in lines:
            if not line.strip().startswith('/*') and not line.strip().startswith('*'):
                sig_line = line
                break

        tokens = sig_line.replace('(', ' ').replace(')', ' ').replace(
            '{', ' ').replace('=', ' ').split()

        key_token = None
        for token in tokens:
            if token.startswith('execute_') or token.startswith('encode_') or token.startswith('rpc_notify_') or token.endswith('_service') or token == 'windrpc_services':
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
    prefix = package_name.replace('/', '_').replace('-', '_')
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
    content.append('#include <stdio.h>\n\n')

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
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']

            if rpc_type == 'NOTIFICATION':
                # Notification subscribe/unsubscribe handler
                sub_name = f"subscribe_{rpc_name}"
                content.append(f"/**\n")
                content.append(
                    f" * @brief Execute handler for subscribing to {rpc_name}\n")
                content.append(f" */\n")
                content.append(
                    f"int32_t execute_{sub_name}(struct windrpc_operation *operation, void *context) {{\n")
                content.append(
                    f"    printf(\"Execute subscription: {sub_name}\\n\");\n")
                content.append(
                    f"    // TODO: Implement subscription enable/disable check\n")
                content.append(
                    f"    // windrpc_request_msg_t *req = &operation->client_msg.payload.request;\n")
                content.append(
                    f"    // bool enable = req->service.{svc_name}.command.{sub_name}.enable;\n")
                content.append(f"    return 0;\n")
                content.append(f"}}\n\n")

                content.append(f"/**\n")
                content.append(
                    f" * @brief Response encoder for subscription of {rpc_name}\n")
                content.append(f" */\n")
                content.append(
                    f"void encode_{sub_name}(windrpc_response_msg_t *response, void *context) {{\n")
                content.append(
                    f"    response->which_service = {prefix}_core_Response_{svc_name}_tag;\n")
                content.append(
                    f"    response->service.{svc_name}.which_result = {prefix}_service_{svc_name}_Response_{sub_name}_tag;\n")
                content.append(
                    f"    // TODO: Optionally fill subscribe response results\n")
                content.append(f"}}\n\n")
            else:
                # Normal RPC (REQUEST_ONLY or REQUEST_RESPONSE)
                content.append(f"/**\n")
                content.append(
                    f" * @brief Execute handler for RPC {rpc_name}\n")
                content.append(f" */\n")
                content.append(
                    f"int32_t execute_{rpc_name}(struct windrpc_operation *operation, void *context) {{\n")
                content.append(
                    f"    printf(\"Execute RPC: {rpc_name}\\n\");\n")
                content.append(f"    // TODO: Implement execution logic\n")
                content.append(f"    return 0;\n")
                content.append(f"}}\n\n")

                if rpc_type == 'REQUEST_RESPONSE':
                    result_type = rpc.get('result', 'types.Empty')
                    # package prefix handling for result message
                    if '.' in result_type:
                        res_pkg, res_msg = result_type.split('.')
                        full_res_type = f"{prefix}_service_{res_pkg}_{res_msg}" if res_pkg != 'types' else f"{prefix}_types_{res_msg}"
                    else:
                        full_res_type = f"{prefix}_service_{svc_name}_{result_type}"

                    content.append(f"/**\n")
                    content.append(
                        f" * @brief Response encoder for RPC {rpc_name}\n")
                    content.append(f" */\n")
                    content.append(
                        f"void encode_{rpc_name}(windrpc_response_msg_t *response, void *context) {{\n")
                    content.append(
                        f"    response->which_service = {prefix}_core_Response_{svc_name}_tag;\n")
                    content.append(
                        f"    response->service.{svc_name}.which_result = {prefix}_service_{svc_name}_Response_{rpc_name}_tag;\n")
                    content.append(f"    \n")
                    content.append(
                        f"    // TODO: Populate response result fields below\n")
                    content.append(
                        f"    // {full_res_type} *res = &response->service.{svc_name}.result.{rpc_name};\n")
                    content.append(f"}}\n\n")

    return "".join(content)


def _generate_notify_skeleton(spec_data, package_name):
    prefix = package_name.replace('/', '_').replace('-', '_')
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
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']

            if rpc_type == 'NOTIFICATION':
                has_notif = True
                result_type = rpc.get('result', 'types.Empty')
                if '.' in result_type:
                    res_pkg, res_msg = result_type.split('.')
                    full_res_type = f"{prefix}_service_{res_pkg}_{res_msg}" if res_pkg != 'types' else f"{prefix}_types_{res_msg}"
                else:
                    full_res_type = f"{prefix}_service_{svc_name}_{result_type}"

                content.append(f"/**\n")
                content.append(
                    f" * @brief Notify helper for event: {rpc_name}\n")
                content.append(f" */\n")
                content.append(
                    f"int32_t rpc_notify_{rpc_name}({full_res_type} *data) {{\n")
                content.append(
                    f"    // TODO: Resolve notify transport config and route\n")
                content.append(
                    f"    // enum transport_type type = rpc_get_notif_trans_type(RPC_EVENT_{rpc_name.upper()});\n\n")
                content.append(
                    f"    windrpc_server_msg_t notif_msg = windrpc_server_msg_t_init_zero;\n")
                content.append(
                    f"    notif_msg.which_payload = WINDRPC_SERVER_NOTIFICAION_TAG;\n")
                content.append(f"    \n")
                content.append(
                    f"    windrpc_notification_msg_t *notif = &notif_msg.payload.notification;\n")
                content.append(
                    f"    notif->which_service = {prefix}_core_Notification_{svc_name}_tag;\n")
                content.append(
                    f"    notif->service.{svc_name}.which_event = {prefix}_service_{svc_name}_Notification_{rpc_name}_tag;\n")
                content.append(
                    f"    notif->service.{svc_name}.event.{rpc_name} = *data;\n\n")
                content.append(
                    f"    // TODO: Send or queue notif_msg (using windrpc_notify(&txn))\n")
                content.append(
                    f"    // struct windrpc_transaction txn = {0};\n")
                content.append(
                    f"    // txn.operation.server_msg = notif_msg;\n")
                content.append(f"    // windrpc_notify(&txn);\n")
                content.append(f"    return 0;\n")
                content.append(f"}}\n\n")

    if not has_notif:
        content.append(
            "// Note: No NOTIFICATION type RPCs found in specifications.\n")

    return "".join(content)


def _generate_handler_skeleton(spec_data, package_name):
    prefix = package_name.replace('/', '_').replace('-', '_')
    services = spec_data.get('services', [])

    content = []
    content.append("/**\n")
    content.append(" * @file windrpc_handler.c\n")
    content.append(
        " * @brief Auto-generated Server Handler Runner Skeleton for WindRPC.\n")
    content.append(
        " * @note Adapt and incorporate this file into your RTOS task scheduler.\n")
    content.append(" */\n\n")
    content.append('#include "windrpc.h"\n')
    content.append('#include <stdio.h>\n\n')

    content.append(
        "/* ========================================================================== */\n")
    content.append(
        "/*                       WindRPC Static Service Definitions                   */\n")
    content.append(
        "/* ========================================================================== */\n\n")

    user_services = []
    for service in services:
        svc_name = service['name']
        if svc_name == 'common':
            continue

        user_services.append(svc_name)
        content.append(
            f"static struct windrpc_service_{svc_name} {svc_name}_service = {{\n")

        rpcs = service.get('rpcs', [])
        for idx, rpc in enumerate(rpcs):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']

            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"

            content.append(f"    .{rpc_name} = {{\n")

            # decode_req binding
            if rpc_type != 'NOTIFICATION' and rpc.get('command') and rpc.get('command') != 'types.Empty':
                content.append(f"        .decode_req = decode_{rpc_name},\n")
            else:
                content.append(f"        .decode_req = NULL,\n")

            # execute binding
            content.append(f"        .execute = execute_{rpc_name},\n")

            # encode_res binding
            if rpc_type == 'REQUEST_RESPONSE' or rpc_type == 'NOTIFICATION':
                content.append(f"        .encode_res = encode_{rpc_name}\n")
            else:
                content.append(f"        .encode_res = NULL\n")

            if idx == len(rpcs) - 1:
                content.append(f"    }}\n")
            else:
                content.append(f"    }},\n")
        content.append(f"}};\n\n")

    content.append("static struct windrpc_user_service windrpc_services = {\n")
    for idx, svc in enumerate(user_services):
        if idx == len(user_services) - 1:
            content.append(f"    .{svc} = &{svc}_service\n")
        else:
            content.append(f"    .{svc} = &{svc}_service,\n")
    content.append("};\n\n")

    content.append(
        "/* ========================================================================== */\n")
    content.append(
        "/*                 RTOS Platform-Agnostic Handler Runner Skeletons           */\n")
    content.append(
        "/* ========================================================================== */\n\n")

    content.append("/* [Platform Configuration Guide]\n")
    content.append(
        " * Choose your RTOS model below and define message queues, events or thread spawners.\n")
    content.append(" *\n")
    content.append(" * --- Zephyr RTOS Definition Example ---\n")
    content.append(
        " * K_MSGQ_DEFINE(serial_rx_data_msgq, sizeof(struct serial_data), 5, 1);\n")
    content.append(" * K_MUTEX_DEFINE(rpc_transport_mutex);\n")
    content.append(" * K_EVENT_DEFINE(rpc_event_sub);\n")
    content.append(" *\n")
    content.append(" * --- FreeRTOS Definition Example ---\n")
    content.append(" * QueueHandle_t serial_rx_data_msgq;\n")
    content.append(" * SemaphoreHandle_t rpc_transport_mutex;\n")
    content.append(" * EventGroupHandle_t rpc_event_sub;\n")
    content.append(" */\n\n")

    content.append("/**\n")
    content.append(
        " * @brief Main RPC Handler loop. Receives data from queue, decodes COBS,\n")
    content.append(
        " *        handles Command execution, and dispatches Response.\n")
    content.append(" */\n")
    content.append(
        "void rpc_handler_thread_entry(void *arg1, void *arg2, void *arg3) {\n")
    content.append("    static uint8_t buffer[256];\n")
    content.append("    static struct windrpc_transaction txn = {\n")
    content.append("        .buffer = {\n")
    content.append("            .data = buffer,\n")
    content.append("            .size = sizeof(buffer),\n")
    content.append("            .bytes_written = 0\n")
    content.append("        },\n")
    content.append("        .context = {0},\n")
    content.append("        .operation = {0}\n")
    content.append("    };\n\n")
    content.append("    // 1. Initialize Framework\n")
    content.append("    static struct windrpc_device_info device_info = {\n")
    content.append("        .serial_number = NULL, // TODO: set chip UID string here\n")
    content.append("    };\n")
    content.append("    windrpc_init(&device_info);\n\n")
    content.append("    while (1) {\n")
    content.append(
        "        // TODO: Wait for communication packet from RX message queue\n")
    content.append(
        "        // e.g. k_msgq_get(&serial_rx_data_msgq, &rx_data, K_FOREVER);\n\n")
    content.append(
        "        // TODO: COBS Decode payload into txn.buffer.data\n")
    content.append(
        "        // txn.buffer.bytes_written = cobs_decode(txn.buffer.data, rx_data.data, rx_data.len);\n\n")
    content.append("        // 2. Handle transaction\n")
    content.append("        int32_t err = windrpc_handle(&txn);\n\n")
    content.append("        // 3. Dispatch response if generated\n")
    content.append("        if (!err && txn.buffer.bytes_written > 0) {\n")
    content.append(
        "            // TODO: COBS Encode response and send it to TX queue\n")
    content.append(
        "            // dispatch_tx_message(txn.buffer.data, txn.buffer.bytes_written);\n")
    content.append("        }\n")
    content.append("    }\n")
    content.append("}\n\n")

    content.append("/**\n")
    content.append(
        " * @brief Notification Runner thread. Dequeues events and encodes as notifications.\n")
    content.append(" */\n")
    content.append(
        "void rpc_notif_thread_entry(void *arg1, void *arg2, void *arg3) {\n")
    content.append("    static uint8_t buffer[256];\n")
    content.append(
        "    static windrpc_server_msg_t server_msg = WINDRPC_SERVER_MESSAGE_INIT;\n\n")
    content.append("    while (1) {\n")
    content.append("        // TODO: Retrieve notification item from queue\n")
    content.append(
        "        // e.g. k_msgq_get(&rpc_noti_msgq, &notif_msg, K_FOREVER);\n\n")
    content.append(
        "        server_msg.which_payload = WINDRPC_SERVER_NOTIFICAION_TAG;\n")
    content.append(
        "        // server_msg.payload.notification = notif_msg.msg;\n\n")
    content.append(
        "        pb_ostream_t ostream = pb_ostream_from_buffer(buffer, sizeof(buffer));\n")
    content.append(
        "        if (!pb_encode(&ostream, WINDRPC_SERVER_MESSAGE_FIELDS, &server_msg)) {\n")
    content.append(
        "            printf(\"Failed to encode notification stream\\n\");\n")
    content.append("        } else {\n")
    content.append(
        "            // TODO: COBS Encode and dispatch to TX driver queue\n")
    content.append(
        "            // dispatch_tx_message(buffer, ostream.bytes_written);\n")
    content.append("        }\n")
    content.append("    }\n")
    content.append("}\n")

    return "".join(content)


def generate(core_spec_path, user_spec_path, output_dir, verbose=False):
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

    # copy windrpc_config.h
    file_path = os.path.join(output_dir, 'windrpc_config.h')
    if os.path.exists(file_path):
        print(f"'{file_path}' is already exist!")
    else:
        source_path = _get_template_file_path('windrpc_config.h')
        copy(source_path, file_path)

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

    # generate handler skeleton
    handler_skeleton = _generate_handler_skeleton(spec_data, package_name)
    file_path = os.path.join(output_dir, "windrpc_handler.c")
    write_smart_merge(file_path, handler_skeleton)
