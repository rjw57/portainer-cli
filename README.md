# Docker swarm CLI via portainer

Portainer provides facilities to proxy the docker socket to allow one to use the
docker client your local machine.

```bash
$ cd ~/path/to/this/repo
$ pip3 install --user ./portainer-wrapper
```

Credentials must be provided. See ``portainer --help`` for where the credentials
need to be. A [template credentials
file](portainer-credentials.example.yaml) is available in this repository.

With the correct credentials, the ``portainer`` command can be used as a wrapper
for docker:

```bash
# Get a list of running containers
$ portainer ps --format {{.Names}}
... list of containers ...
```

Use ``--`` to separate out arguments intended for docker from those intended for
the wrapper:

```bash
# Show help on the wrapper
$ portainer --help

# Show help on docker
$ portainer -- --help
```
