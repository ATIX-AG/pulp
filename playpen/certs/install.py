#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

import os
import shlex
import socket
import sys
import subprocess

from base import get_parser, run_command

def restart_httpd():
    cmd = "service httpd restart"
    return run_command(cmd)

def copy_file(src, dst):
    cmd = "cp %s %s" % (src, dst)
    if not run_command(cmd):
        return False
    return True

def update_httpd_config(ca_key, ca_cert, httpd_ssl_confd="/etc/httpd/conf.d/ssl.conf"):
    ca_key = ca_key.replace("/", "\/")
    ca_cert = ca_cert.replace("/", "\/")
    cmd = "sed -i 's/^SSLCertificateFile.*/SSLCertificateFile %s/' %s" % (ca_cert, httpd_ssl_confd)
    if not run_command(cmd):
        return False
    cmd = "sed -i 's/^SSLCertificateKeyFile.*/SSLCertificateKeyFile %s/' %s" % (ca_key, httpd_ssl_confd)
    if not run_command(cmd):
        return False
    return True

def enable_repo_auth(repo_auth_config="/etc/pulp/repo_auth.conf"):
    cmd = "sed -i 's/enabled: false/enabled: true/' %s" % (repo_auth_config)
    return run_command(cmd)

if __name__ == "__main__":
    default_install_dir = "/etc/pki/content"
    parser = get_parser(limit_options=["ca_key", "ca_cert"])
    parser.add_option("--install_dir", action="store", 
            help="Install directory for CA cert/key.  Default is %s" % (default_install_dir), 
            default=default_install_dir)
    (opts, args) = parser.parse_args()
    ca_key = opts.ca_key
    ca_cert = opts.ca_cert
    install_dir = opts.install_dir

    if not os.path.exists(install_dir):
        os.makedirs(install_dir)
    installed_ca_key = os.path.join(install_dir, os.path.basename(ca_key))
    installed_ca_cert = os.path.join(install_dir, os.path.basename(ca_cert))
    if not copy_file(ca_key, installed_ca_key):
        print "Error installing ca_key"
        sys.exit(1)
    if not copy_file(ca_cert, installed_ca_cert):
        print "Error installing ca_cert"
        sys.exit(1)

    if not update_httpd_config(installed_ca_key, installed_ca_cert):
        print "Error updating httpd"
        sys.exit(1)
    print "Httpd ssl.conf has been updated"

    if not enable_repo_auth():
        print "Error enabling repo auth"
        sys.exit(1)

    if not restart_httpd():
        print "Error restarting httpd"
        sys.exit(1)

