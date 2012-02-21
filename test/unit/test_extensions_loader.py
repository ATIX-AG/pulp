#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
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
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.gc_client.framework import loader
from pulp.gc_client.framework.core import PulpCli, PulpPrompt, ClientContext

# -- test data ----------------------------------------------------------------

TEST_DIRS_ROOT = os.path.abspath(os.path.dirname(__file__)) + "/data/extensions_loader_tests/"

# Contains 3 properly structured plugins, 2 of which contain the CLI init module
VALID_SET = TEST_DIRS_ROOT + 'valid_set'

# Contains 2 plugins, 1 of which loads correct and another that fails
PARTIAL_FAIL_SET = TEST_DIRS_ROOT + 'partial_fail_set'

# Not meant to be loaded as a base directory, each should be loaded individually
# through _load_pack to verify the proper exception case is raised
INDIVIDUAL_FAIL_DIR = TEST_DIRS_ROOT + 'individual_fail_extensions'

# -- test cases ---------------------------------------------------------------

class ExtensionLoaderTests(testutil.PulpTest):

    def setUp(self):
        super(ExtensionLoaderTests, self).setUp()

        self.prompt = PulpPrompt()
        self.cli = PulpCli(self.prompt)
        self.context = ClientContext(None, None, None, self.prompt, cli=self.cli)

    def test_load_valid_set_cli(self):
        """
        Tests loading the set of CLI extensions in the valid_set directory. These
        extensions have the following properties:
        * Three extensions, all of which are set up correctly to be loaded
        * Only two of them (ext1 and ext2) contain a CLI loading module
        * Each of those will add a single section to the CLI named section-X,
          where X is the number in the directory name
        """

        # Test
        loader.load_extensions(VALID_SET, self.context)

        # Verify
        self.assertTrue(self.cli.root_section.find_subsection('section-1') is not None)
        self.assertTrue(self.cli.root_section.find_subsection('section-2') is not None)

    def test_load_extensions_bad_dir(self):
        """
        Tests loading extensions on a directory that doesn't exist.
        """
        try:
            loader.load_extensions('fake_dir', self.context)
        except loader.InvalidExtensionsDirectory, e:
            self.assertEqual(e.dir, 'fake_dir')
            print(e) # for coverage

    def test_load_partial_fail_set_cli(self):
        """
        Tests loading the set of CLI extensions in the partial_fail_set directory.
        The extensions within will load errors for various reasons. The final
        extension pack in there (in the sense that it's loaded last) is valid
        and this test is to ensure that despite all of the errors it is still
        loaded.
        """

        # Test
        try:
            loader.load_extensions(PARTIAL_FAIL_SET, self.context)
            self.fail('Exception expected')
        except loader.LoadFailed, e:
            self.assertTrue(2, len(e.failed_packs))
            self.assertTrue('init_exception' in e.failed_packs)
            self.assertTrue('not_python_module' in e.failed_packs)

        # Verify
        self.assertTrue(self.cli.root_section.find_subsection('section-z') is not None)

    def test_load_failed_import(self):
        """
        Tests an extension pack where the import is unsuccessful.
        """
        self.assertRaises(loader.ImportFailed, loader._load_pack, INDIVIDUAL_FAIL_DIR, 'failed_import', self.context)

    def test_load_not_python_module(self):
        """
        Tests loading an extension that forgot to identify itself as a python module.
        """
        self.assertRaises(loader.ImportFailed, loader._load_pack, INDIVIDUAL_FAIL_DIR, 'not_python_module', self.context)

    def test_load_no_init_module(self):
        """
        Tests loading an extension pack that doesn't contain the cli init module.
        """
        # Make sure it doesn't raise an exception
        loader._load_pack(INDIVIDUAL_FAIL_DIR, 'no_ui_hook', self.context)

    def test_load_initialize_error(self):
        """
        Tests loading an extension that raises an error during the initialize call.
        """
        self.assertRaises(loader.InitError, loader._load_pack, INDIVIDUAL_FAIL_DIR, 'init_error', self.context)

    def test_load_no_init_function(self):
        """
        Tests loading an extension that doesn't have a properly defined UI hook.
        """
        self.assertRaises(loader.NoInitFunction, loader._load_pack, INDIVIDUAL_FAIL_DIR, 'no_init_function', self.context)
