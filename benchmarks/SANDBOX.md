# Sandbox for the benchmark tasks

Terminal-Bench runs each task in a container whose image already carries the
toolchain (COBOL compiler, TeX, proof assistant). On this machine the Docker
CLI is installed but the daemon socket is not reachable (the user is not in
the `docker` group and there is no passwordless `sudo`), and there is no
rootless Podman socket.

Unprivileged user namespaces are enabled, so `bwrap` gives us a container-like
root filesystem without root:

```bash
# one-time: fetch a base image
mkdir -p ~/containers/ubuntu && cd ~/containers/ubuntu
curl -sL -o base.tar.gz \
  https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/ubuntu-base-24.04.5-base-amd64.tar.gz
tar -xzf base.tar.gz

# run a command inside it (network shared, writable rootfs)
bwrap --bind ~/containers/ubuntu / --dev /dev --proc /proc --tmpfs /run \
  --share-net --ro-bind /etc/resolv.conf /etc/resolv.conf \
  --uid 0 --gid 0 --chdir /root bash
```

`apt` needs `-o APT::Sandbox::User=root` inside the namespace: its `_apt`
user is not mapped, so `setgroups` fails otherwise.

```bash
apt-get -o APT::Sandbox::User=root update
apt-get -o APT::Sandbox::User=root install -y gnucobol
```

What is installed today in `~/containers/ubuntu`: GnuCOBOL 3.1.2 (`cobc`).
`overfull_hbox` uses TinyTeX (`~/.local/bin/pdflatex`) and `prove_plus_comm`
uses Lean 4.36 (`~/.local/lean/bin/lean`), both user-space binaries that need
no container.

`tasks/cobol_modernize/verify.py` uses `cobc` as the oracle when it is
reachable (in `PATH`, or through the rootfs above), and falls back to the
embedded Python reference otherwise. The two were checked to agree on the
sample and both hidden inputs.

Still open: the agents themselves run on the host, not inside the rootfs, so
the task's toolchain is the host's. Running `vibe`/`maki` inside the rootfs
means installing Python and their dependencies there, which is the next step
if task images must match Terminal-Bench exactly.
