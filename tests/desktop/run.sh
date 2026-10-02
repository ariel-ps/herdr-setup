#!/bin/bash
set -euo pipefail
setup_root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$setup_root"
docker_cmd=(docker)
if [[ -n "${HERDR_TEST_DOCKER_CONTEXT:-}" ]]; then
    docker_cmd+=(--context "$HERDR_TEST_DOCKER_CONTEXT")
fi
docker_cmd+=(compose -f "$setup_root/tests/desktop/compose.yaml")
case "${1:-start}" in
  start)
    "${docker_cmd[@]}" up -d --build --wait
    echo 'Desktop: http://localhost:6080/vnc.html?autoconnect=true&resize=scale'
    echo 'Next: ./tests/desktop/run.sh install' ;;
  install)
    # shellcheck disable=SC2016
    "${docker_cmd[@]}" exec -T -e GH_TOKEN -e GITHUB_TOKEN desktop bash -o pipefail -c \
      'cd /opt/herdr-setup; ./install.sh 2>&1 | tee "$HOME/test-results/install.log"' ;;
  shell) "${docker_cmd[@]}" exec desktop bash ;;
  reset)
    "${docker_cmd[@]}" down
    "${docker_cmd[@]}" up -d --wait
    echo 'Fresh desktop. Run install again.' ;;
  stop) "${docker_cmd[@]}" down ;;
  *) echo 'Usage: run.sh start|install|shell|reset|stop' >&2; exit 2 ;;
esac
