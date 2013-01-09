# -*- coding: utf-8 -*-
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

import datetime
import os
import shutil

import mock

from pulp.common import dateutils
from pulp.server.compat import ObjectId
from pulp.server.dispatch.call import CallRequest
from pulp.server.itineraries.repo import sync_with_auto_publish_itinerary
from pulp.server.managers.auth.principal import PrincipalManager
from pulp.server.managers.auth.user.system import SystemUser
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.db import repos

from base_db_upgrade import BaseDbUpgradeTests


DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


class RepoUpgradeDefaultsTests(BaseDbUpgradeTests):

    def test_skip_is_disabled(self):
        self.assertTrue(not repos.SKIP_SERVER_CONF)
        self.assertTrue(not repos.SKIP_GPG_KEYS)


class ReposUpgradeNoFilesTests(BaseDbUpgradeTests):

    def setUp(self):
        super(ReposUpgradeNoFilesTests, self).setUp()
        repos.SKIP_SERVER_CONF = True
        repos.SKIP_GPG_KEYS = True

    def tearDown(self):
        super(ReposUpgradeNoFilesTests, self).tearDown()
        repos.SKIP_SERVER_CONF = False
        repos.SKIP_GPG_KEYS = False

    def test_repos(self):
        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            # Repo
            v2_repo = self.tmp_test_db.database.repos.find_one({'id' : repo_id})
            self.assertTrue(v2_repo is not None)
            self.assertTrue(isinstance(v2_repo['_id'], ObjectId))
            self.assertEqual(v2_repo['id'], v1_repo['id'])
            self.assertEqual(v2_repo['display_name'], v1_repo['name'])
            self.assertEqual(v2_repo['description'], None)
            self.assertEqual(v2_repo['scratchpad'], {})
            self.assertEqual(v2_repo['content_unit_count'], 0)

            # Importer
            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None)
            self.assertTrue(isinstance(v2_importer['_id'], ObjectId))
            self.assertEqual(v2_importer['id'], repos.YUM_IMPORTER_ID)
            self.assertEqual(v2_importer['importer_type_id'], repos.YUM_IMPORTER_TYPE_ID)
            self.assertEqual(v2_importer['last_sync'], v1_repo['last_sync'])

            config = v2_importer['config']
            self.assertEqual(config['feed'], v1_repo['source']['url'])
            self.assertEqual(config['ssl_ca_cert'], v1_repo['feed_ca'])
            self.assertEqual(config['ssl_client_cert'], v1_repo['feed_cert'])
            self.assertTrue('skip' not in config)
            self.assertTrue('proxy_url' not in config)
            self.assertTrue('proxy_port' not in config)
            self.assertTrue('proxy_user' not in config)
            self.assertTrue('proxy_pass' not in config)

            # Distributor
            v2_distributor = self.tmp_test_db.database.repo_distributors.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_distributor is not None)
            self.assertTrue(isinstance(v2_distributor['_id'], ObjectId))
            self.assertEqual(v2_distributor['id'], repos.YUM_DISTRIBUTOR_ID)
            self.assertEqual(v2_distributor['distributor_type_id'], repos.YUM_DISTRIBUTOR_TYPE_ID)
            self.assertEqual(v2_distributor['auto_publish'], True)
            self.assertEqual(v2_distributor['scratchpad'], None)
            self.assertEqual(v2_distributor['last_publish'], v1_repo['last_sync'])

            config = v2_distributor['config']
            self.assertEqual(config['relative_url'], v1_repo['relative_path'])
            self.assertEqual(config['http'], False)
            self.assertEqual(config['https'], True)
            self.assertTrue('https_ca' not in config)
            self.assertTrue('gpgkey' not in config)

    def test_repos_idempotency(self):
        # Setup
        repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            v2_repo = self.tmp_test_db.database.repos.find_one({'id' : repo_id})
            self.assertTrue(v2_repo is not None)

            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None)

            v2_distributor = self.tmp_test_db.database.repo_distributors.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_distributor is not None)

    @mock.patch('pulp.server.upgrade.db.repos._repos')
    def test_repos_failed_repo_step(self, mock_repos_call):
        # Setup
        mock_repos_call.return_value = False

        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(not report.success)

    @mock.patch('pulp.server.upgrade.db.repos._repo_importers')
    def test_repos_failed_importer_step(self, mock_importer_call):
        # Setup
        mock_importer_call.return_value = False

        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(not report.success)

    @mock.patch('pulp.server.upgrade.db.repos._repo_distributors')
    def test_repos_failed_distributor_step(self, mock_distributor_call):
        # Setup
        mock_distributor_call.return_value = False

        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(not report.success)

    @mock.patch('pulp.server.upgrade.db.repos._sync_schedules')
    def test_repos_failed_sync_schedules_step(self, mock_sync_schedules_call):
        mock_sync_schedules_call.return_value = False
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        self.assertFalse(report.success)


class RepoUpgradeWithProxyTests(BaseDbUpgradeTests):

    def setUp(self):
        super(RepoUpgradeWithProxyTests, self).setUp()

        self.conf_orig = repos.V1_SERVER_CONF
        repos.V1_SERVER_CONF = os.path.join(DATA_DIR, 'server_configs', 'with-proxy.conf')
        repos.SKIP_SERVER_CONF = False
        repos.SKIP_GPG_KEYS = True

    def tearDown(self):
        super(RepoUpgradeWithProxyTests, self).tearDown()

        repos.V1_SERVER_CONF = self.conf_orig
        repos.SKIP_SERVER_CONF = False
        repos.SKIP_GPG_KEYS = False

    def test_upgrade(self):
        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_repos = self.v1_test_db.database.repos.find({'content_types' : 'yum'})

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None, msg='Missing importer for repo: %s' % repo_id)
            config = v2_importer['config']

            # Values taken from the with-proxy.conf file
            self.assertEqual(config['proxy_url'], 'http://localhost')
            self.assertEqual(config['proxy_port'], '8080')
            self.assertEqual(config['proxy_user'], 'admin')
            self.assertEqual(config['proxy_pass'], 'admin')


class RepoUpgradeWithSslCaCertificateTests(BaseDbUpgradeTests):

    def setUp(self):
        super(RepoUpgradeWithSslCaCertificateTests, self).setUp()

        self.conf_orig = repos.V1_SERVER_CONF
        repos.V1_SERVER_CONF = os.path.join(DATA_DIR, 'server_configs', 'with-ssl-ca-cert.conf')
        repos.SKIP_SERVER_CONF = False
        repos.SKIP_GPG_KEYS = True

        # The .conf file points to /tmp for the cert, so copy it over
        # there so it can be found.
        self.test_cert = os.path.join(DATA_DIR, 'repo_related_files', 'ssl_ca.crt')
        shutil.copy(self.test_cert, '/tmp')

    def tearDown(self):
        super(RepoUpgradeWithSslCaCertificateTests, self).tearDown()

        repos.V1_SERVER_CONF = self.conf_orig
        repos.SKIP_SERVER_CONF = False
        repos.SKIP_GPG_KEYS = False

        tmp_cert = os.path.join('/tmp', 'ssl_ca.crt')
        if os.path.exists(tmp_cert):
            os.remove(tmp_cert)

    def test_upgrade(self):
        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        f = open(self.test_cert, 'r')
        contents = f.read()
        f.close()

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            v2_distributor = self.tmp_test_db.database.repo_distributors.find_one({'repo_id' : repo_id})
            config = v2_distributor['config']
            self.assertEqual(contents, config['https_ca'])


class RepoGpgKeyTests(BaseDbUpgradeTests):

    # These are unsafe to run with non-unit test databases due to the reliance
    # on the filesystem. The following flag should be used in those cases to
    # prevent them from running.
    ENABLED = True

    def setUp(self):
        if not self.ENABLED:
            return

        super(RepoGpgKeyTests, self).setUp()

        self.gpg_root_orig = repos.GPG_KEY_ROOT
        repos.GPG_KEY_ROOT = os.path.join(DATA_DIR, 'gpg_keys')
        repos.SKIP_GPG_KEYS = False
        repos.SKIP_SERVER_CONF = True

        # Munge the relative path of each repo to point to where the GPG
        # key is located
        v1_repos = self.v1_test_db.database.repos.find()
        for index, v1_repo in enumerate(v1_repos):
            v1_repo['relative_path'] = 'repo-%s' % (index + 1)
            self.v1_test_db.database.repos.save(v1_repo, safe=True)

    def tearDown(self):
        if not self.ENABLED:
            return

        super(RepoGpgKeyTests, self).tearDown()
        repos.SKIP_GPG_KEYS = False
        repos.SKIP_SERVER_CONF = False

    def test_upgrade(self):
        if not self.ENABLED:
            return

        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        gpg_key_filename = os.path.join(DATA_DIR, 'gpg_keys', 'repo-1', 'gpg.key')
        f = open(gpg_key_filename, 'r')
        contents = f.read()
        f.close()

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            v2_distributor = self.tmp_test_db.database.repo_distributors.find_one({'repo_id' : repo_id})
            config = v2_distributor['config']
            self.assertEqual(config['gpgkey'], contents)


class RepoUpgradeGroupsTests(BaseDbUpgradeTests):

    def setUp(self):
        super(RepoUpgradeGroupsTests, self).setUp()

        # Unfortunately the test database doesn't have any repo groups, so only
        # for these tests we'll munge the DB for interesting data.

        self.num_repos = 10
        self.num_groups = 3

        new_repos = []
        self.repo_ids_by_group_id = {}
        for i in range(0, self.num_repos):
            repo_id = 'repo-%s' % i
            group_id = 'group-%s' % (i % self.num_groups)
            new_repo = {
                'id' : repo_id,
                'groupid' : [group_id],
                'relative_path' : 'path-%s' % i,
                'content_types' : 'yum'
            }
            self.repo_ids_by_group_id.setdefault(group_id, []).append(repo_id)

            if i % 2 == 0:
                new_repo['groupid'].append('group-x')
                self.repo_ids_by_group_id.setdefault('group-x', []).append(repo_id)

            new_repos.append(new_repo)

        # Add a non-yum repos to make sure it isn't picked up
        file_repo = {
            'id' : 'non-yum',
            'groupid' : ['group-x'],
            'relative_path' : 'path-x',
            'content_types' : 'file',
        }
        new_repos.append(file_repo)

        self.v1_test_db.database.repos.insert(new_repos, safe=True)

    def test_repo_groups(self):
        # Test
        report = UpgradeStepReport()
        result = repos._repo_groups(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertEqual(result, True)

        v2_coll = self.tmp_test_db.database.repo_groups
        all_groups = list(v2_coll.find())
        self.assertEqual(self.num_groups + 1, len(all_groups))

        for group_id, repo_ids in self.repo_ids_by_group_id.items():
            group = self.tmp_test_db.database.repo_groups.find_one({'id' : group_id})
            self.assertTrue(isinstance(group['_id'], ObjectId))
            self.assertEqual(group['id'], group_id)
            self.assertEqual(group['display_name'], None)
            self.assertEqual(group['description'], None)
            self.assertEqual(group['notes'], {})
            self.assertEqual(group['repo_ids'], repo_ids)


class RepoScheduledSyncUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(self.__class__, self).setUp()

        repos.SKIP_SERVER_CONF = True
        repos.SKIP_GPG_KEYS = True

        self.v1_repo_1_id = 'errata-repo'
        self.v1_repo_1_schedule = 'PT30M'

        self.v1_repo_2_id = 'pulp-v1-17-64'
        self.v1_repo_2_schedule = 'R6/2012-01-01T00:00:00Z/P21DT'

        repositories = (self.v1_repo_1_id, self.v1_repo_2_id)
        schedules = (self.v1_repo_1_schedule, self.v1_repo_2_schedule)
        for repo, schedule in zip(repositories, schedules):
            self._insert_scheduled_v1_repo(repo, schedule)

    def tearDown(self):
        super(self.__class__, self).tearDown()

        repos.SKIP_SERVER_CONF = False
        repos.SKIP_GPG_KEYS = False

    def _insert_scheduled_v1_repo(self, repo_id, schedule):
        doc = {'sync_schedule': schedule,
               'sync_options': None,
               'last_sync': None}
        self.v1_test_db.database.repos.update({'_id': repo_id}, {'$set': doc}, safe=True)

    def _insert_scheduled_v2_repo(self, repo_id, schedule):
        importer_id = ObjectId()
        schedule_id = ObjectId()

        importer_doc = {'repo_id': repo_id,
                        'importer_id': importer_id,
                        'importer_type_id': repos.YUM_IMPORTER_TYPE_ID,
                        'scheduled_syncs': [str(schedule_id)]}
        self.tmp_test_db.database.repo_importers.insert(importer_doc, safe=True)

        call_request = CallRequest(sync_with_auto_publish_itinerary, [repo_id], {'overrides': {}})
        interval, start, recurrences = dateutils.parse_iso8601_interval(schedule)
        scheduled_call_doc = {'_id': schedule_id,
                              'id': str(schedule_id),
                              'serialized_call_request': call_request.serialize(),
                              'schedule': schedule,
                              'failure_threshold': None,
                              'consecutive_failures': 0,
                              'first_run': start or datetime.datetime.utcnow(),
                              'next_run': None,
                              'last_run': None,
                              'remaining_runs': recurrences,
                              'enabled': True}
        scheduled_call_doc['next_run'] = repos._calculate_next_run(scheduled_call_doc)
        self.tmp_test_db.database.scheduled_calls.insert(scheduled_call_doc, safe=True)

    @mock.patch('pulp.server.managers.auth.principal.PrincipalManager.get_principal', SystemUser)
    @mock.patch('pulp.server.managers.factory.principal_manager', PrincipalManager)
    def test_schedule_upgrade(self):
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        self.assertTrue(report.success)

    @mock.patch('pulp.server.managers.auth.principal.PrincipalManager.get_principal', SystemUser)
    @mock.patch('pulp.server.managers.factory.principal_manager', PrincipalManager)
    def test_schedule_upgrade_idempotency(self):
        self._insert_scheduled_v2_repo(self.v1_repo_1_id, self.v1_repo_1_schedule)
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        self.assertTrue(report.success)

