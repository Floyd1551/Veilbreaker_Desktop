#!/bin/sh
# Run from an extracted native Linux release. Installs for this user only.
set -eu
bundle=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test -x "$bundle/VeilbreakerDesktop" || { echo "Run the installer from an extracted Linux release." >&2; exit 1; }
prefix="${XDG_DATA_HOME:-$HOME/.local/share}/veilbreaker-app"
bindir="$HOME/.local/bin"
desktopdir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
if test -d "$prefix" && ! test -f "$prefix/build-manifest.json"; then
    echo "Refusing an unrecognized existing directory: $prefix" >&2; exit 1
fi
for name in veilbreaker veilbreaker-desktop; do
    link="$bindir/$name"
    expected="$prefix/veilbreaker"
    test "$name" = veilbreaker && : || expected="$prefix/VeilbreakerDesktop"
    if test -e "$link" || test -L "$link"; then
        test -L "$link" && test "$(readlink "$link")" = "$expected" || {
            echo "Refusing to replace an unrelated command: $link" >&2; exit 1;
        }
    fi
done
mkdir -p "$prefix" "$bindir" "$desktopdir"
cp -R "$bundle/." "$prefix/"
ln -sfn "$prefix/veilbreaker" "$bindir/veilbreaker"
ln -sfn "$prefix/VeilbreakerDesktop" "$bindir/veilbreaker-desktop"
# Quote desktop-entry reserved characters without evaluating a shell command.
escaped=$(printf '%s' "$prefix" | sed 's/\\/\\\\/g; s/"/\\"/g; s/`/\\`/g; s/\$/\\$/g; s/%/%%/g')
cat > "$desktopdir/veilbreaker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Veilbreaker
Comment=Field network diagnostics and evidence
Exec="$escaped/VeilbreakerDesktop"
Icon=$prefix/_internal/veilbreaker/assets/app.png
Terminal=false
Categories=Network;Utility;
EOF
echo "Installed in $prefix"
echo "Launch Veilbreaker from your application menu. CLI: $bindir/veilbreaker"
echo "Add $bindir to PATH if your shell does not already include it."
