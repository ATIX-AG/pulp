# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import re


class Bundle:
    """
    Represents x509, pem encoded key & certificate bundles.
    """

    KEY_BEGIN = re.compile(r'[\n]*[\-]{5}BEGIN (RSA|DSA) PRIVATE KEY[\-]{5}')
    KEY_END = re.compile(r'[\-]{5}END (RSA|DSA) PRIVATE KEY[\-]{5}')
    CRT_BEGIN = re.compile(r'[\n]*[\-]{5}BEGIN CERTIFICATE[\-]{5}')
    CRT_END = re.compile(r'[\-]{5}END CERTIFICATE[\-]{5}')
    
    @classmethod
    def haskey(cls, bundle):
        """
        Get whether the string contains a PEM encoded private key.
        @param bundle: A PEM string.
        @type bundle: str
        @return: True if contains a key.
        @rtype: bool
        """
        m = cls.KEY_BEGIN.search(bundle)
        return ( m is not None )

    @classmethod
    def hascrt(cls, bundle):
        """
        Get whether the string contains a PEM encoded certificate.
        @param bundle: A PEM string.
        @type bundle: str
        @return: True if contains a certificate.
        @rtype: bool
        """
        m = cls.CRT_BEGIN.search(bundle)
        return ( m is not None )

    @classmethod
    def hasboth(cls, bundle):
        """
        Get whether the string contains both
          a PEM encoded private key AND certificate.
        @param bundle: A PEM string.
        @type bundle: str
        @return: True if contains a key & cert.
        @rtype: bool
        """
        return ( cls.haskey(bundle) and cls.hascrt(bundle) )
    
    @classmethod
    def split(cls, bundle):
        """
        Split the bundle into key and certificate components.
        @param bundle: A bundle containing the key and certificate PEM.
        @type bundle: str
        @return: (key,crt)
        @rtype: tuple
        """
        # key
        begin = cls.KEY_BEGIN.search(bundle)
        end = cls.KEY_END.search(bundle)
        if not (begin and end):
            raise Exception, '%s, not valid' % bundle
        begin = begin.start(0)
        end = end.end(0)
        key = bundle[begin:end]
        # certificate
        begin = cls.CRT_BEGIN.search(bundle)
        end = cls.CRT_END.search(bundle)
        if not (begin and end):
            raise Exception, '%s, not valid' % bundle
        begin = begin.start(0)
        end = end.end(0)
        crt= bundle[begin:end]
        return (key, crt)

    @classmethod
    def join(cls, key, crt):
        """
        Join the specified key and certificate not a bundle.
        @param key: A private key (PEM).
        @type key: str
        @param crt: A certificate (PEM).
        @type crt: str
        @return: A bundle containing the key and certifiate.
        @rtype: str
        """
        key = key.strip()
        crt = crt.strip()
        return '\n'.join((key, crt))
    
    def __init__(self, path):
        """
        @param path: The absolute path to the bundle represented.
        @type path: str
        """
        self.path = os.path.expanduser(path)

    def crtpath(self):
        """
        Get the absolute path to the certificate file.
        @return: absolute path to certificate.
        @rtype: str
        """
        return self.path

    def valid(self):
        """
        Validate the bundle.
        @return: True if exists & valid.
        @rtype: bool
        """
        s = self.read()
        return self.hasboth(s)

    def read(self):
        """
        Read and return the bundle contents.
        @return: A string containing the PEM encoded key & cert.
        @rtype: str
        """
        f = open(self.crtpath())
        bundle = f.read()
        f.close()
        assert(self.hasboth(bundle))
        return bundle

    def write(self, bundle):
        """
        Write the specified bundle content.
        @param bundle: The PEM text for the private key and certificate.
        @type bundle: str
        """
        self.mkdir()
        assert(self.hasboth(bundle))
        f = open(self.crtpath(), 'w')
        f.write(bundle)
        f.close()

    def delete(self):
        """
        Delete the certificate.
        """
        path = self.crtpath()
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except IOError:
            log.error(path, exc_info=1)

    def mkdir(self):
        """
        Ensure I{root} directory exists.
        """
        path = os.path.dirname(self.crtpath())
        if not os.path.exists(path):
            os.makedirs(path)

    def __str__(self):
        return 'bundle: %s' % self.crtpath()
