#!/bin/bash
set -euo pipefail
mkdir -p "$HOME/.config/kitty" "$HOME/test-results"
printf 'enable_audio_bell no\nconfirm_os_window_close 0\n' > "$HOME/.config/kitty/kitty.conf"
Xvfb :1 -screen 0 1440x900x24 -nolisten tcp &
for _ in {1..50}; do
    xdpyinfo >/dev/null 2>&1 && break
    sleep 0.1
done
pulseaudio --start --exit-idle-time=-1 || true
dbus-run-session -- openbox-session &
x11vnc -display :1 -forever -shared -nopw -localhost -rfbport 5900 -quiet &
websockify --web=/usr/share/novnc 6080 localhost:5900 &
kitty --title 'Herdr installation test — clean Ubuntu' bash -lc \
  'printf "Clean Ubuntu desktop. No Herdr or plugins installed yet.\n\nRun: cd /opt/herdr-setup && ./install.sh\n\n"; exec bash' &
wait -n
