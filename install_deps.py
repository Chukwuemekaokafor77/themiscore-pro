import os
import sys
import subprocess
import site
import platform
from pathlib import Path

def run_command(command, description):
    print(f"{description}...")
    try:
        subprocess.check_call(command, shell=True)
        print("✓ Done")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed: {e}")
        return False

def get_pip_command():
    """Get the appropriate pip command based on the platform."""
    if platform.system() == 'Windows':
        return f'"{sys.executable}" -m pip install --prefer-binary'
    return f'{sys.executable} -m pip install --prefer-binary'

def install_dependencies():
    """Install Python dependencies from requirements.txt."""
    pip_cmd = get_pip_command()
    requirements_file = 'requirements.txt'
    
    print("\n1. Installing Python dependencies...")
    
    # Read the requirements file
    try:
        with open(requirements_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"\nError: {requirements_file} not found in the current directory.")
        return False
    
    # Separate spacy and its model from other requirements
    other_reqs = []
    for req in requirements:
        if req.lower().startswith('spacy=='):
            spacy_req = req
        elif 'en_core_web_sm' in req.lower():
            spacy_model_req = req
        else:
            other_reqs.append(req)
    
    # Install other requirements first
    if other_reqs:
        print("Installing base dependencies...")
        for req in other_reqs:
            if not run_command(
                f'{pip_cmd} --prefer-binary {req}',
                f"Installing {req.split('==')[0] if '==' in req else req}"
            ):
                print(f"\nFailed to install {req}")
                return False
    
    # Install spacy with specific flags for Windows
    if 'spacy_req' in locals():
        print("\nInstalling spaCy with pre-built wheels...")
        spacy_pkg = spacy_req.split('==')[0]
        
        # First try with the exact version and --no-deps to avoid building blis
        if not run_command(
            f'{pip_cmd} --no-cache-dir --prefer-binary --only-binary :all: {spacy_req}',
            f"Installing {spacy_req} with pre-built wheels"
        ):
            print(f"\nWarning: Could not install {spacy_req} with pre-built wheels. Trying latest version...")
            # Fall back to latest version if specific version fails
            if not run_command(
                f'{pip_cmd} --no-cache-dir --prefer-binary --only-binary :all: {spacy_pkg}',
                f"Installing latest {spacy_pkg} with pre-built wheels"
            ):
                print(f"\nFailed to install {spacy_pkg}. You may need to install it manually.")
                print(f"Try: pip install --prefer-binary --only-binary :all: {spacy_pkg}")
                return False
    
    # Install spacy model if specified
    if 'spacy_model_req' in locals():
        print("\nInstalling spaCy model...")
        if not run_command(
            f'{sys.executable} -m pip install --prefer-binary --no-deps {spacy_model_req}',
            f"Installing {spacy_model_req}"
        ):
            print(f"\nWarning: Could not install {spacy_model_req}")
            print(f"You can try installing it later with: python -m spacy download en_core_web_sm")
    
    return True

def setup_directories():
    """Create necessary directories."""
    print("\n2. Setting up directories...")
    base_dir = Path(__file__).parent
    
    # Create uploads directory
    uploads_dir = base_dir / 'uploads'
    try:
        uploads_dir.mkdir(exist_ok=True)
        print(f"✓ Created uploads directory at: {uploads_dir}")
    except Exception as e:
        print(f"✗ Failed to create uploads directory: {e}")
        return False
    
    # Create data directory for SpaCy models
    data_dir = base_dir / 'data'
    try:
        data_dir.mkdir(exist_ok=True)
        print(f"✓ Created data directory at: {data_dir}")
    except Exception as e:
        print(f"✗ Failed to create data directory: {e}")
        return False
    
    return True

def main():
    print("Setting up development environment...\n")
    
    # 1. Install Python dependencies
    if not install_dependencies():
        return False
    
    # 2. Set up directories
    if not setup_directories():
        return False
    
    # 3. Verify SpaCy installation
    print("\n3. Verifying SpaCy installation...")
    try:
        import spacy
        print("✓ SpaCy is installed")
        
        # Try to load the English model
        try:
            nlp = spacy.load('en_core_web_sm')
            print("✓ English language model is available")
        except OSError:
            print("\nEnglish model not found. Installing...")
            if not run_command(
                f"{sys.executable} -m spacy download en_core_web_sm --user",
                "Downloading SpaCy English model"
            ):
                print("\nFailed to download SpaCy model. Trying alternative method...")
                if not run_command(
                    f"{sys.executable} -m pip install --user https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.6.0/en_core_web_sm-3.6.0.tar.gz",
                    "Installing SpaCy model from direct URL"
                ):
                    print("\nFailed to install SpaCy model. Please install it manually with:")
                    print("python -m spacy download en_core_web_sm")
                    return False
    except Exception as e:
        print(f"\n✗ Error during SpaCy verification: {e}")
        print("You may need to install SpaCy manually with: pip install spacy")
        return False
    
    print("\n✓ Setup completed successfully!")
    print("You can now run the application with: python app.py")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)
