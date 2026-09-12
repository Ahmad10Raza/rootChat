#!/bin/bash
set -e

echo "Building rootChat..."

# Change to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

# Use the .venv environment if it exists, otherwise use system python
if [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv) to avoid bundling bloated system libraries..."
    source .venv/bin/activate
    export PATH="$(pwd)/.venv/bin:$PATH"
fi

# Ensure PyInstaller is installed in the active environment
if ! python -c "import PyInstaller" &> /dev/null
then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
rm -rf build/ dist/

# Run PyInstaller
python -m PyInstaller packaging/rootChat.spec

echo "Building .deb package..."
mkdir -p dist/rootChat-deb/usr/bin
mkdir -p dist/rootChat-deb/opt/rootChat
mkdir -p dist/rootChat-deb/usr/share/applications
mkdir -p dist/rootChat-deb/usr/share/icons/hicolor/scalable/apps
mkdir -p dist/rootChat-deb/DEBIAN

# Copy application files
cp -r dist/rootChat/* dist/rootChat-deb/opt/rootChat/

# Create launcher
cat << 'EOF' > dist/rootChat-deb/usr/bin/rootChat
#!/bin/bash
export LD_LIBRARY_PATH="/opt/rootChat:$LD_LIBRARY_PATH"
exec /opt/rootChat/rootChat "$@"
EOF
chmod +x dist/rootChat-deb/usr/bin/rootChat

# Copy desktop and icons
cp resources/desktop/rootChat.desktop dist/rootChat-deb/usr/share/applications/
cp resources/icons/rootChat.svg dist/rootChat-deb/usr/share/icons/hicolor/scalable/apps/

# Install multi-resolution PNG icons
for size in 16 24 32 48 64 128 256 512; do
    mkdir -p "dist/rootChat-deb/usr/share/icons/hicolor/${size}x${size}/apps"
    if [ -f "resources/icons/rootChat_${size}.png" ]; then
        cp "resources/icons/rootChat_${size}.png" "dist/rootChat-deb/usr/share/icons/hicolor/${size}x${size}/apps/rootChat.png"
    fi
done

# Standard pixmaps fallback
mkdir -p dist/rootChat-deb/usr/share/pixmaps
cp resources/icons/rootChat_256.png dist/rootChat-deb/usr/share/pixmaps/rootChat.png 2>/dev/null || cp resources/icons/rootChat.png dist/rootChat-deb/usr/share/pixmaps/rootChat.png

# Create DEBIAN/control
VERSION=$(PYTHONPATH=. python -c "import version; print(version.__version__)")
cat << EOF > dist/rootChat-deb/DEBIAN/control
Package: rootchat
Version: $VERSION
Architecture: amd64
Maintainer: rootChat Project
Description: Local AI desktop assistant powered by Ollama
Section: utils
Priority: optional
EOF

# Create DEBIAN/postinst to refresh icon cache
cat << 'EOF' > dist/rootChat-deb/DEBIAN/postinst
#!/bin/sh
set -e
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi
EOF
chmod +x dist/rootChat-deb/DEBIAN/postinst

# Build .deb
dpkg-deb --build dist/rootChat-deb
mv dist/rootChat-deb.deb dist/rootChat_${VERSION}_amd64.deb

echo ".deb build complete: dist/rootChat_${VERSION}_amd64.deb"

echo "Building AppImage..."
cd dist
# Download linuxdeploy if not present
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    wget -q -nc -O linuxdeploy-x86_64.AppImage https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

# Create AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/scalable/apps

cp -r rootChat/* AppDir/usr/bin/
cp ../resources/desktop/rootChat.desktop AppDir/usr/share/applications/
cp ../resources/icons/rootChat.svg AppDir/usr/share/icons/hicolor/scalable/apps/

# Run linuxdeploy
./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage -d AppDir/usr/share/applications/rootChat.desktop -i AppDir/usr/share/icons/hicolor/scalable/apps/rootChat.svg

mv rootChat-x86_64.AppImage rootChat-${VERSION}-x86_64.AppImage

echo "AppImage build complete: dist/rootChat-${VERSION}-x86_64.AppImage"

# Checksums
sha256sum rootChat_${VERSION}_amd64.deb rootChat-${VERSION}-x86_64.AppImage > SHA256SUMS
echo "Checksums generated in dist/SHA256SUMS"
