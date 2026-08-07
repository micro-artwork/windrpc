# windrpc/client/csharp.py
import os

def to_pascal(name):
    if not name:
        return ""
    parts = name.split('_')
    res = []
    for p in parts:
        if not p:
            continue
        res.append(p[0].upper() + p[1:])
    return "".join(res)


def _get_template_file_path(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'templates', file_name)


def generate_csharp_client(spec_data, package_name):
    """
    Generates C# Client SDK for WindRPC using template substitution.
    """
    services = spec_data.get('services', [])
    pkg_pascal = to_pascal(package_name)
    namespace_name = f"{pkg_pascal}.WindRpc"

    # 1. Imports
    imports_lines = [
        f"using {pkg_pascal}.Windrpc.Types;",
        "using HilightBox.Communication;"
    ]

    # 2. RPC ID Constants
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
                combined_id = (svc_id << 8) | (rpc_id | 0x80)
                sub_combined_id = (svc_id << 8) | rpc_id
                rpc_id_lines.append(f"        private const ushort RPC_{svc_upper}_SUBSCRIBE_{rpc_upper} = 0x{sub_combined_id:04X};")
                rpc_id_lines.append(f"        private const ushort RPC_{svc_upper}_{rpc_upper} = 0x{combined_id:04X};")
            else:
                combined_id = (svc_id << 8) | rpc_id
                rpc_id_lines.append(f"        private const ushort RPC_{svc_upper}_{rpc_upper} = 0x{combined_id:04X};")

    # 3. Sub-client Properties & Init
    sub_props = []
    sub_init = []
    for svc in services:
        svc_pascal = to_pascal(svc['name'])
        sub_props.append(f"        public {svc_pascal}ServiceClient {svc_pascal} {{ get; }}")
        sub_init.append(f"            {svc_pascal} = new {svc_pascal}ServiceClient(_handler);")

    # 4. Notification Dispatch
    notif_lines = []
    for svc in services:
        svc_name = svc['name']
        svc_upper = svc_name.upper()
        svc_pascal = to_pascal(svc_name)
        for rpc in svc.get('rpcs', []):
            if rpc.get('type', '').upper() == 'NOTIFICATION':
                rpc_upper = rpc['name'].upper()
                notif_lines.append(f"                case RPC_{svc_upper}_{rpc_upper}:")
                notif_lines.append(f"                    {svc_pascal}.HandleNotification_{rpc['name']}(packet);")
                notif_lines.append(f"                    break;")

    # 5. Service Sub-client Classes
    svc_class_lines = []
    for svc in services:
        svc_name = svc['name']
        svc_pascal = to_pascal(svc_name)

        svc_class_lines.append(f"        // ─────────────────────────────────────────────")
        svc_class_lines.append(f"        // Service: {svc_name}")
        svc_class_lines.append(f"        // ─────────────────────────────────────────────")
        svc_class_lines.append(f"        public class {svc_pascal}ServiceClient")
        svc_class_lines.append("        {")
        svc_class_lines.append("            private readonly RpcHandler _handler;")
        svc_class_lines.append(f"            internal {svc_pascal}ServiceClient(RpcHandler handler) => _handler = handler;")
        svc_class_lines.append("")

        for rpc in svc.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            rpc_pascal = to_pascal(rpc_name)
            svc_upper = svc_name.upper()
            rpc_upper = rpc_name.upper()

            cmd_type = rpc.get('command', 'types.Empty')
            if '.' in cmd_type:
                cmd_pkg, cmd_msg = cmd_type.split('.')
                cmd_cls = "Empty" if cmd_msg == "Empty" else f"Hlt.Windrpc.Service.{to_pascal(cmd_pkg)}.{to_pascal(cmd_msg)}"
            elif cmd_type in ['types.Empty', 'Empty']:
                cmd_cls = "Empty"
            else:
                cmd_cls = f"Hlt.Windrpc.Service.{svc_pascal}.{to_pascal(cmd_type)}"

            res_type = rpc.get('result', 'types.Empty')
            if '.' in res_type:
                res_pkg, res_msg = res_type.split('.')
                res_cls = "Empty" if res_msg == "Empty" else f"Hlt.Windrpc.Service.{to_pascal(res_pkg)}.{to_pascal(res_msg)}"
            elif res_type in ['uint32', 'int32', 'bool', 'uint64']:
                res_cls = res_type
            elif res_type in ['types.Empty', 'Empty']:
                res_cls = "Empty"
            else:
                res_cls = f"Hlt.Windrpc.Service.{svc_pascal}.{to_pascal(res_type)}"

            if rpc_type == 'NOTIFICATION':
                event_type = rpc.get('event', 'types.Empty')
                if '.' in event_type:
                    ev_pkg, ev_msg = event_type.split('.')
                    ev_cls = f"Hlt.Windrpc.Service.{to_pascal(ev_pkg)}.{to_pascal(ev_msg)}"
                else:
                    ev_cls = f"Hlt.Windrpc.Service.{svc_pascal}.{to_pascal(event_type)}"

                svc_class_lines.append(f"            public async Task<bool> Subscribe{rpc_pascal}Async(bool enable, CancellationToken cancellationToken = default)")
                svc_class_lines.append("            {")
                svc_class_lines.append(f"                var req = new Subscribe {{ Enable = enable }};")
                svc_class_lines.append(f"                var packet = await _handler.SendRequestAsync(RPC_{svc_upper}_SUBSCRIBE_{rpc_upper}, req, cancellationToken: cancellationToken);")
                svc_class_lines.append("                return true;")
                svc_class_lines.append("            }")
                svc_class_lines.append("")
                svc_class_lines.append(f"            public event EventHandler<{ev_cls}>? On{rpc_pascal};")
                svc_class_lines.append("")
                svc_class_lines.append(f"            internal void HandleNotification_{rpc_name}(FlatPacket packet)")
                svc_class_lines.append("            {")
                svc_class_lines.append("                try")
                svc_class_lines.append("                {")
                svc_class_lines.append(f"                    var ev = {ev_cls}.Parser.ParseFrom(packet.Payload);")
                svc_class_lines.append(f"                    On{rpc_pascal}?.Invoke(this, ev);")
                svc_class_lines.append("                }")
                svc_class_lines.append("                catch (Exception ex)")
                svc_class_lines.append("                {")
                svc_class_lines.append(f"                    Debug.WriteLine($\"{rpc_pascal} Notification parse error: {{ex.Message}}\");")
                svc_class_lines.append("                }")
                svc_class_lines.append("            }")
                svc_class_lines.append("")

            elif rpc_type == 'REQUEST_ONLY':
                if cmd_cls == "Empty":
                    svc_class_lines.append(f"            public void {rpc_pascal}(Empty? request = null)")
                    svc_class_lines.append("            {")
                    svc_class_lines.append(f"                var req = request ?? new Empty();")
                    svc_class_lines.append(f"                _handler.SendRequestNoResponse(RPC_{svc_upper}_{rpc_upper}, req);")
                    svc_class_lines.append("            }")
                    svc_class_lines.append("")
                else:
                    svc_class_lines.append(f"            public void {rpc_pascal}({cmd_cls} request)")
                    svc_class_lines.append("            {")
                    svc_class_lines.append(f"                _handler.SendRequestNoResponse(RPC_{svc_upper}_{rpc_upper}, request);")
                    svc_class_lines.append("            }")
                    svc_class_lines.append("")
                    if "PixelData" in cmd_cls:
                        svc_class_lines.append(f"            public void {rpc_pascal}(uint[] colors)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append(f"                var req = new {cmd_cls}();")
                        svc_class_lines.append("                foreach (var c in colors) req.Colors.Add(c);")
                        svc_class_lines.append(f"                {rpc_pascal}(req);")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")

            else: # REQUEST_RESPONSE
                if res_cls in ['uint32', 'int32', 'bool', 'uint64']:
                    if cmd_cls == "Empty":
                        svc_class_lines.append(f"            public async Task<bool> {rpc_pascal}Async(Empty? request = null, CancellationToken cancellationToken = default)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append("                var req = request ?? new Empty();")
                        svc_class_lines.append(f"                var packet = await _handler.SendRequestAsync(RPC_{svc_upper}_{rpc_upper}, req, cancellationToken: cancellationToken);")
                        svc_class_lines.append("                return true;")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")
                        svc_class_lines.append(f"            public async Task<bool> {rpc_pascal}Async(CancellationToken cancellationToken)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append(f"                return await {rpc_pascal}Async(null, cancellationToken);")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")
                    else:
                        svc_class_lines.append(f"            public async Task<bool> {rpc_pascal}Async({cmd_cls} request, CancellationToken cancellationToken = default)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append(f"                var packet = await _handler.SendRequestAsync(RPC_{svc_upper}_{rpc_upper}, request, cancellationToken: cancellationToken);")
                        svc_class_lines.append("                return true;")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")
                else:
                    if cmd_cls == "Empty":
                        svc_class_lines.append(f"            public async Task<{res_cls}?> {rpc_pascal}Async(Empty? request = null, CancellationToken cancellationToken = default)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append("                var req = request ?? new Empty();")
                        svc_class_lines.append(f"                var packet = await _handler.SendRequestAsync(RPC_{svc_upper}_{rpc_upper}, req, cancellationToken: cancellationToken);")
                        svc_class_lines.append("                if (packet.Payload == null || packet.Payload.Length == 0) return null;")
                        svc_class_lines.append(f"                return {res_cls}.Parser.ParseFrom(packet.Payload);")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")
                        svc_class_lines.append(f"            public async Task<{res_cls}?> {rpc_pascal}Async(CancellationToken cancellationToken)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append(f"                return await {rpc_pascal}Async(null, cancellationToken);")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")
                    else:
                        svc_class_lines.append(f"            public async Task<{res_cls}?> {rpc_pascal}Async({cmd_cls} request, CancellationToken cancellationToken = default)")
                        svc_class_lines.append("            {")
                        svc_class_lines.append(f"                var packet = await _handler.SendRequestAsync(RPC_{svc_upper}_{rpc_upper}, request, cancellationToken: cancellationToken);")
                        svc_class_lines.append("                if (packet.Payload == null || packet.Payload.Length == 0) return null;")
                        svc_class_lines.append(f"                return {res_cls}.Parser.ParseFrom(packet.Payload);")
                        svc_class_lines.append("            }")
                        svc_class_lines.append("")

        svc_class_lines.append("        }")
        svc_class_lines.append("")

    # Load Template
    template_path = _get_template_file_path('WindRpcClient.cs')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Substitute Placeholders
    result = template_content
    result = result.replace("// --WINDRPC_CLIENT_IMPORTS", "\n".join(imports_lines))
    result = result.replace("--WINDRPC_CLIENT_NAMESPACE", namespace_name)
    result = result.replace("// --WINDRPC_RPC_ID_CONSTANTS", "\n".join(rpc_id_lines))
    result = result.replace("// --WINDRPC_SUB_CLIENT_PROPERTIES", "\n".join(sub_props))
    result = result.replace("// --WINDRPC_SUB_CLIENT_INIT", "\n".join(sub_init))
    result = result.replace("// --WINDRPC_NOTIFICATION_DISPATCH", "\n".join(notif_lines))
    result = result.replace("// --WINDRPC_SERVICE_CLIENT_CLASSES", "\n".join(svc_class_lines))

    return result
