"""Build script for pyX2Cscope.

This script automates the build process for pyX2Cscope, including downloading
the wheel from PyPI, building the executable, and creating a distribution package.
"""

import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime

import requests

import pyx2cscope

project_dir = os.path.join(os.path.dirname(pyx2cscope.__file__), "..")
os.chdir(project_dir)


def get_version():
    """Extract version from pyproject.toml or use a default."""
    try:
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.strip().startswith("version"):
                    return line.split("=")[1].strip().strip("\"'")
    except Exception:
        pass
    # Fallback to current date if version not found.
    return datetime.now().strftime("%Y.%m.%d")


def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable with PyInstaller...")
    result = subprocess.run(
        ["pyinstaller", "--noconfirm", "--clean", "pyx2cscope_win.spec"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("Error building executable:")
        print(result.stderr)
        sys.exit(1)
    print("Build completed successfully!")


def copy_batch_file():
    """Copy the batch file to the dist directory."""
    print("Copying batch file...")
    dst_dir = os.path.join("dist", "pyX2Cscope")
    src = os.path.join("scripts", "startWebInterface.bat")
    dst = os.path.join(dst_dir, "startWebInterface.bat")

    try:
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"Successfully copied {src} to {dst}")
        return dst_dir
    except Exception as e:
        print(f"Error copying file: {e}")
        sys.exit(1)


def create_zip_archive(source_dir, version):
    """Create a zip archive of the distribution.

    Args:
        source_dir: Directory containing files to be zipped.
        version: Version string to include in the zip filename.

    Returns:
        Path to the created zip file.
    """
    print("Creating zip archive...")
    dist_path = os.path.join("dist")
    zip_filename = f"pyX2Cscope_win_amd64_{version}.zip"
    zip_path = os.path.join(dist_path, zip_filename)

    # Remove existing zip if it exists.
    if os.path.exists(zip_path):
        os.remove(zip_path)

    # Create zip file while preserving directory structure
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Get the parent directory of source_dir to maintain relative paths
        base_dir = os.path.dirname(source_dir)
        for root, dirs, files in os.walk(source_dir):
            # Calculate the relative path from the base directory
            rel_path = os.path.relpath(root, base_dir)
            for file in files:
                file_path = os.path.join(root, file)
                # Create the path inside the zip file
                arcname = os.path.join(rel_path, file)
                zipf.write(file_path, arcname)

    print(f"Created archive: {zip_path}")
    return zip_path


def download_wheel(version):
    """Download the wheel from PyPI.

    Args:
        version: Version of the wheel to download.

    Returns:
        Path to the downloaded wheel file.
    """
    print(f"Downloading wheel package version {version} from PyPI...")
    wheel_name = f"pyx2cscope-{version}-py3-none-any.whl"
    url = f"https://files.pythonhosted.org/packages/py3/p/pyx2cscope/{wheel_name}"

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs("dist", exist_ok=True)
        wheel_path = os.path.join("dist", wheel_name)

        with open(wheel_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Successfully downloaded {wheel_name}")
        return wheel_path
    except Exception as e:
        print(f"Error downloading wheel: {e}")
        sys.exit(1)


def main():
    """Main function to run the build process."""
    version = get_version()
    print(f"Building pyX2Cscope version {version}")

    # Build the executable.
    build_executable()

    # Copy the batch file.
    dist_dir = copy_batch_file()

    # Create zip archive.
    zip_path = create_zip_archive(dist_dir, version)
    print(f"Zip archive created: {zip_path}")

    # Download the wheel from PyPI.
    wheel_path = download_wheel(version)
    print(f"Downloaded wheel: {wheel_path}")

    print("\nBuild process completed successfully!")
    print(f"Executable location: {dist_dir}")


if __name__ == "__main__":
    main()