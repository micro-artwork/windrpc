# windrpc/utils/protoc_resolver.py
import os
import sys
import shutil
import platform
import subprocess
import urllib.request
import zipfile

PROTOBUF_RELEASE_VERSION = "25.3"  # Stable Protobuf Release Version

class ProtocResolver:
    """
    Smart resolver for protoc executable.
    Resolution Priority:
    1. System PATH ('protoc')
    2. Python 'grpc_tools.protoc' module if available
    3. User Local Cache (~/.windrpc/bin/protoc) with auto-download from GitHub releases
    """

    @staticmethod
    def get_protoc_runner():
        # 1. System PATH
        sys_protoc = shutil.which("protoc")
        if sys_protoc:
            return ("cli", sys_protoc)

        # 2. Try grpc_tools.protoc
        try:
            from grpc_tools import protoc as grpc_protoc
            return ("python_module", grpc_protoc)
        except ImportError:
            pass

        # 3. User Local Cache & Auto-download
        cache_dir = os.path.expanduser("~/.windrpc/bin")
        os.makedirs(cache_dir, exist_ok=True)

        exe_name = "protoc.exe" if sys.platform == "win32" else "protoc"
        target_bin = os.path.join(cache_dir, exe_name)

        if not os.path.exists(target_bin):
            ProtocResolver._download_protoc(cache_dir, target_bin)

        return ("cli", target_bin)

    @staticmethod
    def _download_protoc(cache_dir, target_bin):
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Map OS & Architecture
        if system == "windows":
            os_str = "win64" if "64" in machine else "win32"
        elif system == "darwin":
            os_str = "osx-universal_binary"
        elif system == "linux":
            os_str = "linux-x86_64" if "64" in machine or "x86" in machine else "linux-aarch_64"
        else:
            raise RuntimeError(f"Unsupported operating system for automatic protoc download: {system}")

        zip_name = f"protoc-{PROTOBUF_RELEASE_VERSION}-{os_str}.zip"
        url = f"https://github.com/protocolbuffers/protobuf/releases/download/v{PROTOBUF_RELEASE_VERSION}/{zip_name}"

        print(f"[WindRPC] protoc not found locally. Downloading official binary from GitHub ({zip_name})...")
        zip_path = os.path.join(cache_dir, zip_name)

        try:
            # Download zip
            urllib.request.urlretrieve(url, zip_path)

            # Extract bin/protoc
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.startswith("bin/protoc") or member.startswith("bin/protoc.exe"):
                        zip_ref.extract(member, cache_dir)

            # Move bin/protoc to ~/.windrpc/bin/protoc
            extracted_bin = os.path.join(cache_dir, "bin", os.path.basename(target_bin))
            if os.path.exists(extracted_bin):
                if os.path.exists(target_bin):
                    os.remove(target_bin)
                shutil.move(extracted_bin, target_bin)
                shutil.rmtree(os.path.join(cache_dir, "bin"), ignore_errors=True)

            if sys.platform != "win32":
                os.chmod(target_bin, 0o755)

            os.remove(zip_path)
            print(f"[WindRPC] protoc successfully installed to: {target_bin}")

        except Exception as e:
            raise RuntimeError(f"Failed to download and install protoc automatically: {e}\n"
                               f"Please install protoc manually or run 'pip install grpcio-tools'.")

    @staticmethod
    def compile(proto_files, proto_imports, out_dir, lang="csharp"):
        """
        Compiles .proto files into target language (e.g. C#) using resolved protoc.
        """
        runner_type, runner = ProtocResolver.get_protoc_runner()
        os.makedirs(out_dir, exist_ok=True)

        import_flags = [f"-I{inc}" for inc in proto_imports]

        if lang.lower() in ('js', 'javascript'):
            print(f"[WindRPC] Compiling Protobuf to JS using npx pbjs ({lang})...")
            bundle_out = os.path.join(out_dir, "proto_bundle.js")
            # npx pbjs CLI syntax: pbjs --es6 <out_path> <proto_files>
            npx_cmd = f'npx --yes pbjs --es6 "{bundle_out}" ' + " ".join([f'"{p}"' for p in proto_files])
            res_pbjs = subprocess.run(npx_cmd, capture_output=True, text=True, shell=True)
            if res_pbjs.returncode == 0 and os.path.exists(bundle_out):
                print(f"[WindRPC] Successfully compiled JS Protobuf bundle via npx pbjs -> {bundle_out}")
                return
            else:
                print(f"[WindRPC] npx pbjs notice: {res_pbjs.stderr or res_pbjs.stdout}")

            lang_flag = f"--js_out=import_style=commonjs,binary:{out_dir}"
        else:
            lang_flag = f"--{lang}_out={out_dir}"

        if runner_type == "python_module":
            args = ['protoc'] + import_flags + [lang_flag] + proto_files
            print(f"[WindRPC] Compiling Protobuf using python module 'grpc_tools.protoc' ({lang})...")
            code = runner.main(args)
            if code != 0:
                raise RuntimeError(f"protoc compilation failed with exit code: {code}")
        else:
            cmd = [runner] + import_flags + [lang_flag] + proto_files
            print(f"[WindRPC] Compiling Protobuf using protoc CLI ({lang}): {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"protoc compilation failed:\n{res.stderr}")

        print(f"[WindRPC] Protobuf compilation finished successfully. Output: {out_dir}")
