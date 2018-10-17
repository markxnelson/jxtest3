#!/usr/bin/env python3

import argparse
import logging
import math
import os
import requests
import sys
import time

from requests.auth import HTTPBasicAuth

try:
    from http.client import HTTPConnection # py3
except ImportError:
    from httplib import HTTPConnection # py2


PSM_URL="https://psm.us.oraclecloud.com"

class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

# functional sugar for the above
def env_default(envvar):
    def wrapper(**kwargs):
        return EnvDefault(envvar, **kwargs)
    return wrapper

def __debug_requests_on(level):
    '''Switches on logging of the requests module.'''
    if level == logging.DEBUG:
        HTTPConnection.debuglevel = 1

    #requests_log = logging.getLogger("requests.packages.urllib3")
    #requests_log.setLevel(level)
    #requests_log.propagate = True

def __object_store_container_exists(storage_url, container_name, username, password):
    container_url = '{0}/{1}'.format(storage_url, container_name)
    logging.info('Checking if container {0} exists in Object Store'.format(container_name))
    response = requests.head(container_url, auth=HTTPBasicAuth(username, password))
    return (response.status_code != 404)

def __create_object_store_container(storage_url, container_name, username, password):
    container_url = '{0}/{1}'.format(storage_url, container_name)
    logging.info('Creating container {0} in Object Store'.format(container_name))
    response = requests.put(container_url, auth=HTTPBasicAuth(username, password))
    if(response.status_code != 201):
        raise Exception('Failed to create container {0} in Object Store! Response status and message is {1}: {2}'.format(response.status_code, response.text))
    logging.info('Created container {0} in Object Store'.format(container_name))

def __verify(storage_url, identity_domain, username, password):
    storage_resp = requests.head(storage_url, auth=HTTPBasicAuth(username, password))
    storage_resp.raise_for_status()

    psm_apps_url = '{0}/paas/service/apaas/api/v1.1/apps/{1}'.format(PSM_URL, identity_domain)
    psm_resp = requests.head(storage_url, auth=HTTPBasicAuth(username, password), headers={'X-ID-TENANT-NAME':identity_domain})
    psm_resp.raise_for_status()

def __cmd_verify(args):
    __verify(args.storage_url, args.identity_domain, args.username, args.password)

def __filegen(fo):
    yield fo.read(65534)

def __archive_object_storage_uri(app_name, app_version, app_archive):
    basename = os.path.basename(app_archive)
    (prefix, suffix) = os.path.splitext(basename)
    archive_name = '{0}-{1}{2}'.format(prefix, app_version, suffix)
    return '{0}/{1}'.format(app_name, archive_name)

def __upload(storage_url, identity_domain, username, password, app_name, app_version, app_archive):
    if not __object_store_container_exists(storage_url, app_name, username, password):
        __create_object_store_container(storage_url, app_name, username, password)
    with open(app_archive, 'rb') as file:
        object_url = '{0}/{1}'.format(storage_url, __archive_object_storage_uri(app_name, app_version, app_archive))
        logging.info('Uploading {0} to {1}'.format(app_archive, object_url))
        http_debuglevel = HTTPConnection.debuglevel
        try:
            HTTPConnection.debuglevel = 0
            response = requests.put(object_url, auth=HTTPBasicAuth(username, password), data=file, timeout=(6.05, 300))
            response.raise_for_status()
        finally:
            HTTPConnection.debuglevel = http_debuglevel

def __cmd_upload(args):
    __upload(args.storage_url, args.identity_domain, args.username, args.password, args.app_name, args.app_version, args.app_archive)

def __accs_app_exists(identity_domain, username, password, app_name):
    app_url = '{0}/paas/service/apaas/api/v1.1/apps/{1}/{2}'.format(PSM_URL, identity_domain, app_name)
    logging.info('Checking if ACCS application {0} exists in identity domain {1}'.format(app_name, identity_domain))
    response = requests.head(app_url, auth=HTTPBasicAuth(username, password),
            headers={'X-ID-TENANT-NAME':identity_domain})
    return (response.status_code != 404)

def __deploy_accs_app(storage_url, identity_domain, username, password, app_name, app_version, app_archive):
    logging.info('Deploying ACCS application {0} in identity domain {1}'.format(app_name, identity_domain))

    app_url = '{0}/paas/service/apaas/api/v1.1/apps/{1}'.format(PSM_URL, identity_domain)
    operation = requests.post
    formdata = {
        'name': (None, app_name),
        'runtime': (None, 'java'),
        'subscription': (None, 'Hourly'),
        'archiveURL': (None, __archive_object_storage_uri(app_name, app_version, app_archive))
    }

    if __accs_app_exists(identity_domain, username, password, app_name):
        app_url = '{0}/paas/service/apaas/api/v1.1/apps/{1}/{2}'.format(PSM_URL, identity_domain, app_name)
        operation = requests.put
        formdata = {
            'archiveURL': (None, __archive_object_storage_uri(app_name, app_version, app_archive))
        }

    response = operation(app_url, auth=HTTPBasicAuth(username, password),
            headers={'X-ID-TENANT-NAME':identity_domain}, files=formdata,)
    logging.info(response.text)
    response.raise_for_status()

    poll_url = response.headers['Location']

    sleep_time_exp = lambda attempt: math.pow(2, attempt) * .1
    attempt = 1
    max_attempts = 30
    max_sleep_time = 30
    finished = False
    status = 'InProgress'
    poll_response = {'text':''}
    while status not in ['Failed', 'Succeeded']:
        if attempt > max_attempts:
            break
        poll_response = requests.get(poll_url, auth=HTTPBasicAuth(username, password),
                 headers={'X-ID-TENANT-NAME':identity_domain})
        status = poll_response.json()['opStatus']
        logging.info("After polling url {0}, {1} times, opStatus = {2}".format(
            poll_url, attempt - 1, status))
        if status not in ['Failed', 'Succeeded'] and attempt < max_attempts:
            sleep_time = sleep_time_exp(attempt)
            time.sleep(sleep_time if sleep_time < max_sleep_time else max_sleep_time)
        attempt = attempt + 1

    logging.info("After polling url {0}, {1} times, opStatus = {2}".format(
        poll_url, attempt - 1, status))
    if status != 'Succeeded':
        raise Exception('Application deployment failed: {0}'.format(poll_response.text))

def __cmd_deploy(args):
    __upload(args.storage_url, args.identity_domain, args.username, args.password, args.app_name, args.app_version, args.app_archive)
    __deploy_accs_app(args.storage_url, args.identity_domain, args.username, args.password, args.app_name, args.app_version, args.app_archive)

def __existing_file(v):
    path = os.path.abspath(v)
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError("File {0} does not exist".format(path))

def main(argv):
    parser = argparse.ArgumentParser(description="Oracle Application Container Cloud Service deployer", formatter_class=argparse.RawDescriptionHelpFormatter)

    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument('-i', '--info', dest='info', default=False, action='store_true',
            help='Produce informational output')
    debug_group.add_argument('-d', '--debug', dest='debug', default=False, action='store_true',
            help='Produce debug output')

    subparsers = parser.add_subparsers()
    subparsers.required = True
    subparsers.dest = 'command'

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('--storage-url', dest='storage_url', action=env_default('STORAGE_URL'), required=True, help='Storage URL')
    common_parser.add_argument('-i', '--identity-domain', dest='identity_domain', action=env_default('IDENTITY_DOMAIN'), required=True, help='IDCS identity domain')
    common_parser.add_argument('-u', '--username', dest='username', required=True, action=env_default('USERNAME'), help='Username')
    common_parser.add_argument('-p', '--password', dest='password', required=True, action=env_default('PASSWORD'), help='Password')

    verify_parser = subparsers.add_parser('verify', parents=[common_parser], help='Verify connectivity')
    verify_parser.set_defaults(function=__cmd_verify, command='verify')

    upload_parser = subparsers.add_parser('upload', parents=[common_parser], help='Upload to object store')
    upload_parser.add_argument('app_name', help='ACCS application name')
    upload_parser.add_argument('app_version', help='ACCS application version')
    upload_parser.add_argument('app_archive', type=__existing_file, help='ACCS application archive file')
    upload_parser.set_defaults(function=__cmd_upload, command='upload')

    deploy_parser = subparsers.add_parser('deploy', parents=[common_parser], help='Deploy ACCS app to object store')
    deploy_parser.add_argument('app_name', help='ACCS application name')
    deploy_parser.add_argument('app_version', help='ACCS application version')
    deploy_parser.add_argument('app_archive', type=__existing_file, help='ACCS application archive file')
    deploy_parser.set_defaults(function=__cmd_deploy, command='deploy')

    args = parser.parse_args()

    logging_level = logging.WARNING
    if args.debug:
        logging_level = logging.DEBUG
    elif args.info:
        logging_level = logging.INFO

    logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S %Z',
            level=logging_level)
    logging.getLogger().setLevel(logging_level)
    logging.getLogger().propagate = True

    __debug_requests_on(logging_level)

    args.function(args)

if __name__ == '__main__':
    main(sys.argv)
