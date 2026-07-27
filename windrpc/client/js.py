# windrpc/client/js.py
import json
import os


def to_camel(name):
    if not name:
        return ""
    parts = name.split('_')
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def to_pascal(name):
    if not name:
        return ""
    parts = name.split('_')
    return "".join(p.capitalize() for p in parts if p)


def _get_template_file_path(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'templates', file_name)


def build_protobufjs_root_json(spec_data):
    """
    Builds a JSON descriptor object compatible with protobuf.Root.fromJSON().
    Returns (root_json, enum_names, message_names).
    """
    nested = {}
    enum_names = []
    message_names = []

    # 1. Add enums from types.enums
    types_sec = spec_data.get('types', {})
    for enum_item in types_sec.get('enums', []):
        enum_name = enum_item.get('name')
        if not enum_name:
            continue
        values = {}
        for idx, m in enumerate(enum_item.get('members', [])):
            if isinstance(m, dict):
                v_name = m['name']
                val = m['value']
            else:
                v_name = str(m)
                val = idx
            values[v_name] = val
        nested[enum_name] = {"values": values}
        if enum_name not in enum_names:
            enum_names.append(enum_name)

    # 2. Add messages from types.messages
    for msg in types_sec.get('messages', []):
        msg_name = msg.get('name')
        if not msg_name:
            continue
        fields_dict = {}
        for f in msg.get('fields', []):
            f_num = f.get('number', 1)
            f_name = f.get('name', '')
            f_type = f.get('type', 'bytes')
            f_prop = f.get('property', '')

            f_type_clean = f_type.split('.')[-1]
            f_entry = {"id": f_num, "type": f_type_clean}
            if f_prop == 'repeated':
                f_entry["rule"] = "repeated"
            fields_dict[f_name] = f_entry
        nested[msg_name] = {"fields": fields_dict}
        if msg_name not in message_names:
            message_names.append(msg_name)

    # 3. Add messages from services[].messages
    for svc in spec_data.get('services', []):
        for msg in svc.get('messages', []):
            msg_name = msg.get('name')
            if not msg_name:
                continue
            fields_dict = {}
            for f in msg.get('fields', []):
                f_num = f.get('number', 1)
                f_name = f.get('name', '')
                f_type = f.get('type', 'bytes')
                f_prop = f.get('property', '')

                f_type_clean = f_type.split('.')[-1]
                f_entry = {"id": f_num, "type": f_type_clean}
                if f_prop == 'repeated':
                    f_entry["rule"] = "repeated"
                fields_dict[f_name] = f_entry
            nested[msg_name] = {"fields": fields_dict}
            if msg_name not in message_names:
                message_names.append(msg_name)

    return {"nested": nested}, enum_names, message_names


def generate_js_client(spec_data, package_name):
    """
    Generates JavaScript Client SDK for WindRPC using template substitution.
    Powered by protobufjs dynamic schema descriptors.
    """
    services = spec_data.get('services', [])
    root_json, enum_names, message_names = build_protobufjs_root_json(spec_data)

    # 1. RPC ID Constants
    rpc_id_lines = []
    for svc in services:
        svc_name = svc['name']
        svc_id = svc['id']
        svc_upper = svc_name.upper()
        for rpc in svc.get('rpcs', []):
            rpc_name = rpc['name']
            rpc_id = rpc['id']
            rpc_upper = rpc_name.upper()
            rpc_type = rpc.get('type', '').upper()

            if rpc_type == 'NOTIFICATION':
                sub_combined_id = (svc_id << 8) | rpc_id
                combined_id = (svc_id << 8) | (rpc_id | 0x80)
                rpc_id_lines.append(f"    {svc_upper}_SUBSCRIBE_{rpc_upper}: 0x{sub_combined_id:04X},")
                rpc_id_lines.append(f"    {svc_upper}_{rpc_upper}: 0x{combined_id:04X},")
            else:
                combined_id = (svc_id << 8) | rpc_id
                rpc_id_lines.append(f"    {svc_upper}_{rpc_upper}: 0x{combined_id:04X},")

    # 2. Helpers for Enums and Messages
    msg_helpers_lines = []

    # Enums
    for enum_name in enum_names:
        pascal_name = to_pascal(enum_name)
        msg_helpers_lines.append(f"// Enum: {enum_name}")
        msg_helpers_lines.append(f"export const {pascal_name}Enum = root.lookupEnum('{enum_name}');")
        msg_helpers_lines.append("")

    # Messages
    for msg_name in message_names:
        pascal_name = to_pascal(msg_name)
        msg_helpers_lines.append(f"// Message: {msg_name}")
        msg_helpers_lines.append(f"export const {pascal_name}Type = root.lookupType('{msg_name}');")
        msg_helpers_lines.append(f"export function encode{pascal_name}(payload = {{}}) {{")
        msg_helpers_lines.append(f"    if (payload instanceof Uint8Array) return payload;")
        msg_helpers_lines.append(f"    const message = {pascal_name}Type.create(payload);")
        msg_helpers_lines.append(f"    return {pascal_name}Type.encode(message).finish();")
        msg_helpers_lines.append(f"}}")
        msg_helpers_lines.append(f"export function decode{pascal_name}(binary) {{")
        msg_helpers_lines.append(f"    return {pascal_name}Type.decode(binary);")
        msg_helpers_lines.append(f"}}")
        msg_helpers_lines.append("")

    # 3. Sub-client Initialization
    sub_init_lines = []
    for svc in services:
        svc_pascal = to_pascal(svc['name'])
        svc_camel = to_camel(svc['name'])
        sub_init_lines.append(f"        this.{svc_camel} = new {svc_pascal}ServiceClient(this);")

    # 4. Service Client Classes
    svc_class_lines = []
    for svc in services:
        svc_name = svc['name']
        svc_pascal = to_pascal(svc_name)
        svc_upper = svc_name.upper()

        svc_class_lines.append(f"// ─────────────────────────────────────────────")
        svc_class_lines.append(f"// Service: {svc_name}")
        svc_class_lines.append(f"// ─────────────────────────────────────────────")
        svc_class_lines.append(f"export class {svc_pascal}ServiceClient {{")
        svc_class_lines.append("    constructor(client) {")
        svc_class_lines.append("        this.client = client;")
        svc_class_lines.append("    }")
        svc_class_lines.append("")

        msg_map = {msg.get('name'): msg.get('fields', []) for msg in svc.get('messages', [])}

        for rpc in svc.get('rpcs', []):
            rpc_name = rpc['name']
            rpc_upper = rpc_name.upper()
            rpc_pascal = to_pascal(rpc_name)
            rpc_type = rpc.get('type', 'REQUEST_RESPONSE').upper()
            command = rpc.get('command') or rpc.get('request', '')

            cmd_msg = command.split('.')[-1] if command else ''
            cmd_pascal = to_pascal(cmd_msg)
            has_payload = bool(cmd_msg and cmd_msg.lower() not in ('empty', ''))

            # ── buildXxxFrame(): always generated for all RPC types ──────────
            if has_payload:
                svc_class_lines.append(f"    /**")
                svc_class_lines.append(f"     * Builds a binary packet frame for {rpc_name}.")
                svc_class_lines.append(f"     * @param {{{{ {', '.join(f['name'] for f in msg_map.get(cmd_msg, []))} }}}} payload - {cmd_msg} message")
                svc_class_lines.append(f"     * @returns {{Uint8Array}} ready-to-send frame")
                svc_class_lines.append(f"     */")
                svc_class_lines.append(f"    build{rpc_pascal}Frame(payload = {{}}) {{")
                svc_class_lines.append(f"        const payloadBytes = encode{cmd_pascal}(payload);")
                svc_class_lines.append(f"        return this.client.buildFrame(RPC_ID.{svc_upper}_{rpc_upper}, payloadBytes);")
                svc_class_lines.append("    }")
            else:
                svc_class_lines.append(f"    /**")
                svc_class_lines.append(f"     * Builds a binary packet frame for {rpc_name} (no payload).")
                svc_class_lines.append(f"     * @returns {{Uint8Array}} ready-to-send frame")
                svc_class_lines.append(f"     */")
                svc_class_lines.append(f"    build{rpc_pascal}Frame() {{")
                svc_class_lines.append(f"        return this.client.buildFrame(RPC_ID.{svc_upper}_{rpc_upper});")
                svc_class_lines.append("    }")
            svc_class_lines.append("")

            # ── sendXxx(): only for REQUEST_RESPONSE — Promise-based with timeout ──
            if rpc_type == 'REQUEST_RESPONSE':
                payload_arg = "payload = {}, " if has_payload else ""
                payload_encode = f"encode{cmd_pascal}(payload)" if has_payload else "new Uint8Array(0)"
                svc_class_lines.append(f"    /**")
                svc_class_lines.append(f"     * Sends {rpc_name} and returns a Promise that resolves with the response.")
                svc_class_lines.append(f"     * Registers a pending entry so the response frame is matched by seqId.")
                if has_payload:
                    svc_class_lines.append(f"     * @param {{{{ {', '.join(f['name'] for f in msg_map.get(cmd_msg, []))} }}}} payload - {cmd_msg} message")
                svc_class_lines.append(f"     * @param {{function}} sendFn - function(frame: Uint8Array) that writes to transport")
                svc_class_lines.append(f"     * @param {{number}} [timeoutMs=2000] - response timeout in milliseconds")
                svc_class_lines.append(f"     * @returns {{Promise<{{rpcId: number, seqId: number, payload: Uint8Array}}>>}}")
                svc_class_lines.append(f"     */")
                svc_class_lines.append(f"    send{rpc_pascal}({payload_arg}sendFn, timeoutMs = 2000) {{")
                svc_class_lines.append(f"        const payloadBytes = {payload_encode};")
                svc_class_lines.append(f"        return this.client.sendRequest(RPC_ID.{svc_upper}_{rpc_upper}, payloadBytes, sendFn, timeoutMs);")
                svc_class_lines.append("    }")
                svc_class_lines.append("")

        svc_class_lines.append("}")
        svc_class_lines.append("")

    # Load Template
    template_path = _get_template_file_path('WindRpcClient.js')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Substitute Placeholders
    schema_json_str = json.dumps(root_json, indent=4)
    result = template_content
    result = result.replace("// --WINDRPC_RPC_ID_CONSTANTS", "\n".join(rpc_id_lines))
    result = result.replace("// --WINDRPC_PROTO_SCHEMA", schema_json_str)
    result = result.replace("// --WINDRPC_MESSAGE_HELPERS", "\n".join(msg_helpers_lines))
    result = result.replace("// --WINDRPC_SUB_CLIENT_INIT", "\n".join(sub_init_lines))
    result = result.replace("// --WINDRPC_SERVICE_CLIENT_CLASSES", "\n".join(svc_class_lines))

    return result


def generate_cobs_js():
    """
    Generates cobs.js using template file.
    """
    template_path = _get_template_file_path('cobs.js')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()
