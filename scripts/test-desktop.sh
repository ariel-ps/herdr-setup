#!/bin/bash
set -euo pipefail
setup_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$setup_root"
docker_cmd=(docker)
if [[ -n "${HERDR_TEST_DOCKER_CONTEXT:-}" ]]; then
    docker_cmd+=(--context "$HERDR_TEST_DOCKER_CONTEXT")
fi
case "${1:-start}" in
  start)
    "${docker_cmd[@]}" compose up -d --build --wait
    echo 'Desktop: http://localhost:6080/vnc.html?autoconnect=true&resize=scale'
    echo 'Next: ./scripts/test-desktop.sh auth, then ./scripts/test-desktop.sh install' ;;
  auth)
    # Credential is streamed, never put in command arguments or the image.
    gh auth token | "${docker_cmd[@]}" compose exec -T desktop bash -c \
      'umask 077; cat > /run/setup-secrets/github_token'
    echo 'GitHub credential available inside the disposable container until restart.' ;;
  install)
    # shellcheck disable=SC2016
    "${docker_cmd[@]}" compose exec -T desktop bash -o pipefail -c \
      'cd /opt/herdr-setup; ./install.sh 2>&1 | tee "$HOME/test-results/install.log"' ;;
  shell) "${docker_cmd[@]}" compose exec desktop bash ;;
  reset)
    "${docker_cmd[@]}" compose down
    "${docker_cmd[@]}" compose up -d --wait
    echo 'Fresh desktop. Run auth and install again.' ;;
  stop) "${docker_cmd[@]}" compose down ;;
  *) echo 'Usage: test-desktop.sh start|auth|install|shell|reset|stop' >&2; exit 2 ;;
esac
