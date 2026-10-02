#!/usr/bin/env sh
# Fetch the assets the kit uses but does not carry.
#
# Both are large and neither is ours: the kitty-themes pool is ~400 community
# colour schemes, the sprite packs about a megabyte of pixel art. Cloning them
# on install keeps the repo about this plugin.
#
# Never fails the install. Every feature that needs an asset already checks for
# it and no-ops, so a machine with no network gets a working kit minus colour
# variety and sprites — worth more than a plugin that refuses to install.
set -u

cache="${XDG_CACHE_HOME:-$HOME/.cache}"
themes="$cache/kitty-themes"
sprites="$cache/herdr-kit/sprites"

if command -v git >/dev/null 2>&1; then
  if [ -d "$themes/.git" ]; then
    git -C "$themes" pull --ff-only >/dev/null 2>&1 \
      && echo "themes: updated" || echo "themes: kept existing clone"
  else
    mkdir -p "$(dirname "$themes")"
    git clone --depth 1 https://github.com/kovidgoyal/kitty-themes.git "$themes" >/dev/null 2>&1 \
      && echo "themes: cloned" || echo "themes: clone failed, palettes fall back to the herdr theme"
  fi
else
  echo "themes: git not found, skipping"
fi

# Sprites are optional decoration on the blocked alert; there is no upstream to
# clone, so this only reports what is already there.
if [ -d "$sprites" ] && [ -n "$(ls -A "$sprites" 2>/dev/null)" ]; then
  echo "sprites: present"
else
  mkdir -p "$sprites"
  echo "sprites: none installed — blocked alerts flash and sound without one"
fi

exit 0
