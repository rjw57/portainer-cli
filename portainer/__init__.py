#!/usr/bin/env python3
"""
Authenticate docker to a portainer instance

Usage:
    portainer (-h|--help)
    portainer [--credentials=PATH] [--credentials-name=NAME] [--docker-cmd=COMMAND] \
        [--] [<argument>...]

Options:

    -h, --help                      Show a brief usage summary.

    -c, --credentials=PATH          Path to Portainer credentials. See below.
    -n, --credentials-name=NAME     Which credentials in the credentials file should be used.

    --docker-cmd=COMMAND            Command used to run docker. [default: docker]

    <argument>...                   Remaining arguments to be passed to docker command.

Credentials:

    Portainer credentials are specified in a YAML file with the following format:

      default:
        host: "<hostname of portainer instance>",
        username: "<username of portainer user>",
        password: "<password of portainer user>",
        endpoint_id: "<optional id of portainer endpoint, default is 1>",
        ca_certificate: "<optional PEM encoded root CA certificate>"

    Multiple credentials can be present in one file. They are named after the top-level key in the
    credentials file and selected via the --credentials-name argument.

    If the --credentials-name argument is not given, the value of the PORTAINER_CREDENTIALS_NAME
    environment variable is used. If the environment variable is not set, "default" is used.

    If a credential file is not specified, the following file locations are checked and the first
    file which exists is used:

    - portainer-credentials.yaml in the current directory
    - ~/.portainer-credentials.yaml
    - /etc/portainer-credentials.yaml

TLS verification:

    If no "cacert" property is present in the credentials, the --tlsverify flag is not passed to
    the Docker binary and the connection will not be verified. This is probably *NOT* what you
    want.

"""  # noqa:E501
import json
import logging
import os
import subprocess
import sys
import tempfile

import docopt
import requests
import yaml

LOG = logging.getLogger('portainer-auth')


def main():
    opts = docopt.docopt(__doc__, options_first=True)
    logging.basicConfig(level=logging.WARN)

    # Search for credentials files. If one is specified on the command line, it replaces the
    # default search path.
    if opts['--credentials'] is not None:
        credential_files = [opts['--credentials']]
    else:
        credential_files = [
            os.path.abspath(os.path.join(os.getcwd(), 'portainer-credentials.yaml')),
            os.path.expanduser('~/.portainer-credentials.yaml'),
            '/etc/portainer-credentials.yaml',
        ]

    valid_credential_files = [path for path in credential_files if os.path.isfile(path)]
    if len(valid_credential_files) == 0:
        LOG.error('Could not find credentials file. Tried:')
        for path in credential_files:
            LOG.error(f'  - {path}')
        sys.exit(1)

    # Load credentials
    credentials_file = valid_credential_files[0]
    with open(credentials_file) as fobj:
        all_credentials = yaml.load(fobj)
    credentials_name = opts['--credentials-name']
    if credentials_name is None:
        credentials_name = os.environ.get('PORTAINER_CREDENTIALS_NAME', 'default')
    credentials = all_credentials.get(credentials_name)
    if credentials is None:
        LOG.error(f'Credentials "{credentials_name}" not found in "{credentials_file}"')
        sys.exit(1)

    # Extract credentials from file.
    portainer_host = credentials['host']
    portainer_username = credentials['username']
    portainer_password = credentials['password']
    portainer_endpoint_id = credentials.get('endpoint_id', '1')
    portainer_ca_certificate = credentials.get('ca_certificate')

    # Fetch an auth token from portainer.
    token = get_portainer_token(
        portainer_host, portainer_username, portainer_password)
    if token is None:
        LOG.error('Could not retrieve auth token')
        sys.exit(1)

    # Run docker with appropriate magic to use portainer.
    with tempfile.TemporaryDirectory(prefix='portainer-') as tmpdir:
        # Generate docker configuration
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, 'config.json'), 'w') as fobj:
            json.dump({'HttpHeaders': {'Authorization': f'Bearer {token}'}}, fobj)

        docker_args = [
            opts['--docker-cmd'],
            '--config', config_dir,
            '--host', f'tcp://{portainer_host}:443/api/endpoints/{portainer_endpoint_id}/docker/',
            '--tls',
        ]

        # Add TLS verification if present
        if portainer_ca_certificate is not None:
            cacert_path = os.path.join(tmpdir, 'cacert.pem')
            with open(cacert_path, 'w') as fobj:
                fobj.write(portainer_ca_certificate)
            docker_args.extend(['--tlsverify', '--tlscacert', cacert_path])
        else:
            LOG.warn('No CA root certificate supplied. TLS verification is disabled.')

        # Add remaining docker arguments
        if opts['<argument>'] is not None:
            docker_args.extend(opts['<argument>'])

        completed_process = subprocess.run(docker_args)

    # Teleport exit code from docker to calling process
    sys.exit(completed_process.returncode)


def get_portainer_token(host, username, password):
    """Retrieve a JWT authorization token for portainer."""
    r = requests.post(
        f'https://{host}/api/auth',
        json={'Username': username, 'Password': password})

    if not r.ok:
        LOG.error(f'Error {r.status_code} from portainer. Response:')
        for line in r.text.splitlines():
            LOG.error('    ' + line)
        return None

    return r.json().get('jwt')


if __name__ == '__main__':
    main()
