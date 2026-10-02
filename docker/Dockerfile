# A desktop only: Herdr, Rust, Go, uv, jq and zsh are installed by install.sh.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git sudo bash python3 \
    xvfb x11vnc novnc websockify openbox kitty dbus-x11 \
    fonts-dejavu-core mesa-utils libgl1-mesa-dri x11-utils \
    pulseaudio procps \
    && rm -rf /var/lib/apt/lists/*
RUN if id ubuntu >/dev/null 2>&1; then userdel -r ubuntu; fi
RUN useradd --create-home --uid 1000 --shell /bin/bash tester \
    && printf 'tester ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/tester \
    && chmod 0440 /etc/sudoers.d/tester
COPY desktop.sh /usr/local/bin/desktop
COPY github-askpass.sh /usr/local/bin/github-askpass
RUN chmod +x /usr/local/bin/desktop /usr/local/bin/github-askpass
USER tester
ENV HOME=/home/tester DISPLAY=:1 TERM=xterm-kitty LIBGL_ALWAYS_SOFTWARE=1
ENV PATH=/home/tester/.local/bin:/home/tester/.cargo/bin:/usr/local/bin:/usr/bin:/bin
ENV GIT_ASKPASS=/usr/local/bin/github-askpass GIT_TERMINAL_PROMPT=0
WORKDIR /home/tester
EXPOSE 6080
ENTRYPOINT ["/usr/local/bin/desktop"]
