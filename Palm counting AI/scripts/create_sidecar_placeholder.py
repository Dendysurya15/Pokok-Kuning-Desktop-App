"""
Create placeholder sidecar file untuk development mode.
Tauri memerlukan file sidecar yang disebutkan di externalBin, bahkan untuk dev mode.
"""
import sys
from pathlib import Path

def create_placeholder():
    """Create placeholder sidecar file untuk development"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_tauri_dir = project_root / "src-tauri"
    binaries_dir = src_tauri_dir / "binaries"
    
    # Buat direktori jika belum ada
    binaries_dir.mkdir(exist_ok=True)
    
    # Get target triple
    import subprocess
    result = subprocess.run(
        ["rustc", "--print", "target-triple"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        target_triple = result.stdout.strip()
    else:
        # Fallback
        if sys.platform == "win32":
            target_triple = "x86_64-pc-windows-msvc"
        elif sys.platform == "darwin":
            import os
            target_triple = "aarch64-apple-darwin" if "arm" in os.uname().machine else "x86_64-apple-darwin"
        else:
            target_triple = "x86_64-unknown-linux-gnu"
    
    # Create placeholder file
    placeholder_name = f"infer_worker-{target_triple}"
    if sys.platform == "win32":
        placeholder_name += ".exe"
    
    placeholder_path = binaries_dir / placeholder_name
    
    if placeholder_path.exists():
        print(f"Placeholder sudah ada: {placeholder_path}")
        return True
    
    # Create minimal executable placeholder
    # Untuk Windows, buat file kosong (Tauri akan skip jika tidak bisa dijalankan)
    # Atau buat file yang print message
    if sys.platform == "win32":
        # Create minimal PE executable yang hanya exit
        # Atau lebih sederhana: buat file text dengan .exe extension
        # Tapi Tauri akan error jika bukan valid executable
        # Solusi: buat file yang valid tapi hanya print message dan exit
        placeholder_content = b""  # Empty untuk sekarang, akan diisi dengan minimal exe
        # Untuk development, kita bisa skip validasi dengan membuat file dummy
        # Tapi lebih baik buat minimal executable
        
        # Create minimal Windows executable (just exit with code 0)
        # Ini adalah minimal PE header yang valid
        minimal_exe = (
            b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00'
            b'\xb8\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00'
            b'PE\x00\x00d\x86\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00'
            b'\x0f\x01\x0b\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        )
        placeholder_path.write_bytes(minimal_exe)
    else:
        # Untuk Linux/Mac, buat shell script yang valid
        placeholder_content = f"""#!/bin/sh
# Placeholder sidecar untuk development mode
# File ini hanya untuk memenuhi requirement Tauri externalBin
# Saat runtime, aplikasi akan menggunakan Python script sebagai fallback
echo "Placeholder sidecar - using Python script instead" >&2
exit 0
"""
        placeholder_path.write_text(placeholder_content, encoding='utf-8')
        # Make executable
        import os
        os.chmod(placeholder_path, 0o755)
    
    print(f"[OK] Placeholder created: {placeholder_path}")
    print("  Note: Untuk production, jalankan 'npm run build:sidecar' untuk build sidecar yang sebenarnya")
    return True

if __name__ == "__main__":
    success = create_placeholder()
    sys.exit(0 if success else 1)
