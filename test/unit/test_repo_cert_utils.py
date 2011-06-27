#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import shutil
import sys
import os

import testutil

from pulp.repo_auth import repo_cert_utils

# -- constants -----------------------------------------------------------------------

# Used to sign the test certificate
VALID_CA = os.path.abspath(os.path.dirname(__file__)) + '/data/test_repo_cert_utils/valid_ca.crt'

# Not used to sign the test certificate  :)
INVALID_CA = os.path.abspath(os.path.dirname(__file__)) + '/data/test_repo_cert_utils/invalid_ca.crt'

# Test certificate
CERT = os.path.abspath(os.path.dirname(__file__)) + '/data/test_repo_cert_utils/cert.crt'

# -- test cases ----------------------------------------------------------------------

class TestValidateCertBundle(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.utils = repo_cert_utils.RepoCertUtils(self.config)

    def test_validate_cert_bundle_valid(self):
        '''
        Tests that validating a valid cert bundle does not indicate an error.
        '''

        # Setup
        bundle = {'ca' : 'PEM', 'cert' : 'PEM'}

        # Test
        self.utils.validate_cert_bundle(bundle) # should not throw an error

    def test_validate_cert_bundle_missing_keys(self):
        '''
        Tests that a cert bundle missing any of the required keys indicates
        an error.
        '''

        # Test missing CA
        self.assertRaises(ValueError, self.utils.validate_cert_bundle, {'cert' : 'PEM'})
        self.assertRaises(ValueError, self.utils.validate_cert_bundle, {'ca' : 'PEM'})

    def test_validate_cert_bundle_non_dict(self):
        '''
        Tests that calling validate without passing a dict correctly indicates
        an error.
        '''

        # Test bad parameter
        self.assertRaises(ValueError, self.utils.validate_cert_bundle, 'foo')

    def test_validate_cert_bundle_none(self):
        '''
        Tests that calling validate with None throws the correct error.
        '''

        # Test missing parameter
        self.assertRaises(ValueError, self.utils.validate_cert_bundle, None)

    def test_validate_cert_bundle_extra_keys(self):
        '''
        Tests that calling validate with non-cert bundle keys raises an error.
        '''

        # Setup
        bundle = {'ca' : 'PEM', 'cert' : 'PEM', 'foo' : 'bar'}

        # Test
        self.assertRaises(ValueError, self.utils.validate_cert_bundle, bundle)


class TestCertStorage(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        if os.path.exists(self.config.get('repos', 'cert_location')):
            shutil.rmtree(self.config.get('repos', 'cert_location'))

        if os.path.exists(self.utils._global_cert_directory()):
            shutil.rmtree(self.utils._global_cert_directory())

    def setUp(self):
        self.config = testutil.load_test_config()
        self.utils = repo_cert_utils.RepoCertUtils(self.config)
        testutil.PulpAsyncTest.setUp(self)

    def test_write_feed_certs(self):
        '''
        Tests writing repo feed certificates to disk.
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}

        # Test
        files = self.utils.write_feed_cert_bundle(repo_id, bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(2, len(files))

        repo_cert_dir = self.utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self._verify_repo_file_contents(repo_id, 'feed-%s.ca' % repo_id, bundle['ca'])
        self._verify_repo_file_contents(repo_id, 'feed-%s.cert' % repo_id, bundle['cert'])

    def test_write_consumer_certs(self):
        '''
        Tests writing repo consumer certificates to disk.        
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}

        # Test
        files = self.utils.write_consumer_cert_bundle(repo_id, bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(2, len(files))

        repo_cert_dir = self.utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self._verify_repo_file_contents(repo_id, 'consumer-%s.ca' % repo_id, bundle['ca'])
        self._verify_repo_file_contents(repo_id, 'consumer-%s.cert' % repo_id, bundle['cert'])

    def test_write_read_global_certs(self):
        '''
        Tests writing out the global repo cert bundle.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}

        # Test Write
        files = self.utils.write_global_repo_cert_bundle(bundle)

        # Verify Write
        self.assertTrue(files is not None)
        self.assertEqual(2, len(files))

        global_cert_dir = self.utils._global_cert_directory()
        self.assertTrue(os.path.exists(global_cert_dir))

        # -----

        # Test Read All
        read_bundle = self.utils.read_global_cert_bundle()

        # Verify Read All
        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

        # -----

        # Test Read Subset
        read_bundle  = self.utils.read_global_cert_bundle(['ca'])

        # Verify Read Subset
        self.assertTrue(read_bundle is not None)
        self.assertEqual(1, len(read_bundle))
        self.assertTrue('ca' in read_bundle)
        self.assertEqual(read_bundle['ca'], bundle['ca'])
        
    def test_write_read_partial_bundle(self):
        '''
        Tests that only a subset of the bundle components can be specified and still
        correctly written out.
        '''

        # Setup
        bundle = {'cert' : 'FOO'}

        # Test
        files = self.utils.write_global_repo_cert_bundle(bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(1, len(files))

        global_cert_dir = self.utils._global_cert_directory()
        self.assertTrue(os.path.exists(global_cert_dir))

        read_bundle = self.utils.read_global_cert_bundle(['cert'])

        self.assertEqual(read_bundle['cert'], bundle['cert'])

        self.assertTrue(not os.path.exists(os.path.join(self.utils._global_cert_directory(), 'pulp-global-repo.ca')))

    def test_remove_bundle_item(self):
        '''
        Tests that specifying None as the content of an item in the bundle removes
        it's file if it exists.
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}
        self.utils.write_feed_cert_bundle(repo_id, bundle)

        # Test
        clean_bundle = {'ca' : None, 'cert' : 'BAR'} # remove ca, cert unchanged
        files = self.utils.write_feed_cert_bundle(repo_id, clean_bundle)
        self.assertTrue(files is not None)
        self.assertEqual(2, len(files)) # no change to cert
        self.assertEqual(files['ca'], None)

        repo_cert_dir = self.utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self.assertTrue(not os.path.exists(os.path.join(self.utils._repo_cert_directory(repo_id), 'feed-%s.ca' % repo_id)))
        self._verify_repo_file_contents(repo_id, 'feed-%s.cert' % repo_id, clean_bundle['cert'])

    def test_write_none_item(self):
        '''
        Tests that specifying None as the content of an item that was not previously
        written does not throw an error or create an empty file.
        '''

        # Setup
        repo_id = 'test-repo-5'

        # Test
        clean_bundle = {'ca' : None, 'cert' : None}
        files = self.utils.write_feed_cert_bundle(repo_id, clean_bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(2, len(files))

        self.assertEqual(files['ca'], None)
        self.assertEqual(files['cert'], None)

        self.assertTrue(not os.path.exists(os.path.join(self.utils._repo_cert_directory(repo_id), 'feed-%s.ca' % repo_id)))
        self.assertTrue(not os.path.exists(os.path.join(self.utils._repo_cert_directory(repo_id), 'feed-%s.cert' % repo_id)))

    def test_write_none_consumer_bundle(self):
        '''
        Tests that specifying None as the bundle will delete all consumer bundle items
        for a repo that previously had them.
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}
        files = self.utils.write_consumer_cert_bundle(repo_id, bundle)

        for f in files.values():
            self.assertTrue(os.path.exists(f))

        # Test
        self.utils.write_consumer_cert_bundle(repo_id, None)

        # Verify
        for f in files.values():
            self.assertTrue(not os.path.exists(f))

    def test_read_global_no_bundle(self):
        '''
        Tests that attempting to read the global repo bundle when it doesn't exist
        returns None.
        '''

        # Test
        bundle = self.utils.read_global_cert_bundle()

        # Verify
        self.assertTrue(bundle is None)

    def test_delete_bundles(self):
        '''
        Tests deleting bundles for a repo.
        '''

        # Setup
        repo_id = 'test-repo-2'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}

        self.utils.write_feed_cert_bundle(repo_id, bundle)
        self.utils.write_consumer_cert_bundle(repo_id, bundle)

        repo_cert_dir = self.utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        cert_files = os.listdir(repo_cert_dir)
        self.assertEqual(4, len(cert_files)) # 2 bundles, 2 files each

        # Test
        self.utils.delete_for_repo(repo_id)

        # Verify
        self.assertTrue(not os.path.exists(repo_cert_dir))

    def test_delete_global_bundle(self):
        '''
        Tests deleting the global repo auth bundle.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR'}

        self.utils.write_global_repo_cert_bundle(bundle)

        # Test
        self.utils.delete_global_cert_bundle()

        # Verify
        read_bundle = self.utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)

    def _verify_repo_file_contents(self, repo_id, filename, contents):
        full_filename = os.path.join(self.utils._repo_cert_directory(repo_id), filename)
        f = open(full_filename, 'r')
        read_contents = f.read()
        f.close()

        self.assertEqual(read_contents, contents)

class TestCertVerify(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.utils = repo_cert_utils.RepoCertUtils(self.config)
        
    def test_valid(self):
        '''
        Tests that verifying a cert with its signing CA returns true.
        '''
        self.assertTrue(self.utils.validate_certificate(CERT, VALID_CA))

    def test_invalid(self):
        '''
        Tests that verifying a cert with an incorrect CA returns false.
        '''
        self.assertTrue(not self.utils.validate_certificate(CERT, INVALID_CA))

    def test_valid_pem(self):
        '''
        Tests that verifying a PEM encoded cert string with its signing CA returns true.
        '''

        # Setup
        f = open(VALID_CA)
        ca = f.read()
        f.close()

        f = open(CERT)
        cert = f.read()
        f.close()

        # Test
        self.assertTrue(self.utils.validate_certificate_pem(cert, ca))

    def test_invalid_pem(self):
        '''
        Tests that verifying a PEM encoded cert string with an incorrect CA returns false.
        '''

        # Setup
        f = open(INVALID_CA)
        ca = f.read()
        f.close()

        f = open(CERT)
        cert = f.read()
        f.close()

        # Test
        self.assertTrue(not self.utils.validate_certificate_pem(cert, ca))
