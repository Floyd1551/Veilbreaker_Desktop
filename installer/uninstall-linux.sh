#!/bin/sh
# Remove only this application's per-user installation, retaining diagnostic data.
set -eu
prefix="${XDG_DATA_HOME:-$HOME/.local/share}/veilbreaker-app"
bindir="$HOME/.local/bin"
desktop="${XDG_DATA_HOME:-$HOME/.local/share}/applications/veilbreaker.desktop"
test -f "$prefix/build-manifest.json" && test -f "$prefix/VeilbreakerDesktop" || {
    echo "No recognized Veilbreaker installation at $prefix" >&2; exit 1;
}
for name in veilbreaker veilbreaker-desktop; do
    link="$bindir/$name"
    expected="$prefix/veilbreaker"
    test "$name" = veilbreaker && : || expected="$prefix/VeilbreakerDesktop"
    if test -L "$link" && test "$(readlink "$link")" = "$expected"; then rm -- "$link"; fi
done
if test -f "$desktop" && grep -F 'Name=Veilbreaker' "$desktop" >/dev/null; then rm -- "$desktop"; fi
# Prefix is fixed to the app-only directory; it never equals the user data path.
case "$prefix" in /*/veilbreaker-app) rm -rf -- "$prefix" ;; *) echo "Refusing unexpected install path" >&2; exit 1 ;; esac
echo "Veilbreaker removed. Diagnostic data and configuration were preserved."
