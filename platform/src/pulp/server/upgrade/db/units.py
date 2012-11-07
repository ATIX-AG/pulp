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

"""
Moreso than anywhere else in the DB upgrade process, this script is written
against Pulp at a point in time. It is expected that any changes to the unit
schemas will be done through DB migration scripts. Same with standard
collections such as content_types.

As such, this script intentionally does not use code in pulp.server despite
the obvious temptation. The collection names for each unit is duplicated here;
if it changes in the future, a migration script will move everything and this
script will continue to use the original names. Same goes for the content_types
model. It'd be useful to use the ContentType class, but if that changes, there
is potential that this script would break or the migration to the new changes
would fail, so in the interest of not having to perpetually maintain this
script, that model is duplicated here.

Another aspect of this is the fact that the content types are explicitly set
to version 0. This will cause the migrations to take place to move from that
point in time (which corresponds to before the first migration script being
written) to the latest.
"""

from gettext import gettext as _
import os
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from pymongo.objectid import ObjectId

from pulp.server.upgrade.model import UpgradeStepReport


# Passed to mongo to scope the returned results to only the RPM unit key
V2_RPM_KEYS_FIELDS = {
    'name' : 1,
    'epoch' : 1,
    'version' : 1,
    'release' : 1,
    'arch' : 1,
    'checksumtype' : 1,
    'checksum' : 1,
}


DIR_STORAGE_ROOT = '/var/lib/pulp/content/'
DIR_RPMS = os.path.join(DIR_STORAGE_ROOT, 'rpm')
DIR_SRPMS = os.path.join(DIR_STORAGE_ROOT, 'srpm')
DIR_DRPM = os.path.join(DIR_STORAGE_ROOT, 'drpm')
DIR_DISTRIBUTION = os.path.join(DIR_STORAGE_ROOT, 'distribution')

PACKAGE_PATH_TEMPLATE = '%(name)s/%(version)s/%(release)s/%(arch)s/%(checksum)s/%(filename)s'

# Type definition constants located at the end of this file for readability


def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    init_success = _initialize_content_types(v2_database)

    rpms_success = _rpms(v1_database, v2_database, report)
    srpms_success = _srpms(v1_database, v2_database, report)
    drpms_success = _drpms(v1_database, v2_database, report)
    errata_success = _errata(v1_database, v2_database, report)
    distributions_success = _distributions(v1_database, v2_database, report)

    report.success = (init_success and
                      rpms_success and srpms_success and drpms_success and
                      errata_success and distributions_success)
    return report

# -- upgrade steps ------------------------------------------------------------

def _initialize_content_types(v2_database):

    # See module-level docstring for information about why this exists.

    # Collection initialization
    types_coll = v2_database.content_types
    migrations_coll = v2_database.migration_trackers

    # These calls mimic what the base Model class does, which is why the
    # DESCENDING IS used.
    types_coll.ensure_index([('id', DESCENDING)], unique=True)
    migrations_coll.ensure_index([('name', DESCENDING)], unique=True)

    # Idempotency: The type definition id is the uniqueness. There are so few
    # that we can simply iterate over each one to see if it is already in the
    # v2 database.

    for type_def in TYPE_DEFS:
        existing = types_coll.find_one({'id' : type_def['id']})
        if not existing:
            # The ObjectId will be added by mongo, no need to do it here
            types_coll.insert(type_def, safe=True)

            # Apply the uniqueness for the unit key. This is necessary as the
            # upgrade calls in this module rely on that for idempotency checks.
            units_coll = getattr(v2_database, _units_collection_name(type_def['id']))

            # These indexes mimic how the types database code creates indexes,
            # which is admittedly different than how Model uses DESCENDING above.
            unit_index = [(k, ASCENDING) for k in type_def['unit_key']]
            units_coll.ensure_index(unit_index, unique=True)

        existing = migrations_coll.find_one({'name' : type_def['display_name']})
        if not existing:
            new_migration = {
                '_id' : ObjectId(), # for clarity
                'name' : type_def['display_name'],
                'version' : 0,
            }
            migrations_coll.insert(new_migration, safe=True)

    return True


def _rpms(v1_database, v2_database, report):
    rpm_coll = v2_database.units_rpm
    all_rpms = v1_database.packages.find({'arch' : {'$ne' : 'src'}})
    return __packages(rpm_coll, all_rpms, report)


def _srpms(v1_database, v2_database, report):
    srpm_coll = v2_database.units_srpm
    all_srpms = v1_database.packages.find({'arch' : 'src'})
    return __packages(srpm_coll, all_srpms, report)


def __packages(package_coll, all_v1_packages, report):

    # In v1, both RPMs and SRPMs are stored in the packages collection.
    # The differentiating factor is the arch which will be 'src' for SRPMs and,
    # well, not src for normal RPMs. This call handles both cases, with the
    # differentiator being done by the parameters.

    # Idempotency: This one is ugly. The unique key for an RPM/SRPM in v2
    # is NEVRA, checksumtype, and checksum. It's less efficient but way simpler
    # to iterate over each package in v1 and attempt to insert it, letting
    # mongo's uniqueness check prevent a duplicate.

    for v1_rpm in all_v1_packages:
        v2_rpm = {
            'name' : v1_rpm['name'],
            'epoch' : v1_rpm['epoch'],
            'version' : v1_rpm['version'],
            'release' : v1_rpm['release'],
            'arch' : v1_rpm['arch'],
            'description' : v1_rpm['description'],
            'vendor' : v1_rpm['vendor'],
            'filename' : v1_rpm['filename'],
            'requires' : v1_rpm['requires'],
            'provides' : v1_rpm['provides'],
            'buildhost' : v1_rpm['buildhost'],
            'license' : v1_rpm['license'],

            '_id' : ObjectId(),
            '_content_type_id' : 'rpm'
        }

        # Checksum is weird, it's stored as a dict of checksum type to the
        # checksum value. In practice the data should never contain multiple
        # entries (instead, multiple documents would be created in the packages
        # collection), so if we encouter it warn the user and only store the
        # first entry.
        if len(v1_rpm['checksum']) > 1:
            warning = _('Multiple checksums found for the RPM %(filename)s,'
                        'only the checksum of type %(type)s will be saved')
            report.warning(warning % {'filename' : v1_rpm['filename'], 'type' : v1_rpm['checksum'].keys()[0]})

        v2_rpm['checksumtype'] = v1_rpm['checksum'].keys()[0]
        v2_rpm['checksum'] = v1_rpm['checksum'][v2_rpm['checksumtype']]

        # Relative path will be set during the associations. That information
        # is only obtainable from a repo itself in v1. Not ideal, but so far
        # one of the very few places where it's a multi-step process to upgrade
        # a data type.

        # Storage path
        rpm_path = PACKAGE_PATH_TEMPLATE % v2_rpm
        storage_path = os.path.join(DIR_RPMS, rpm_path)
        v2_rpm['_storage_path'] = storage_path

        try:
            package_coll.insert(v2_rpm, safe=True)
        except DuplicateKeyError:
            # I really dislike this pattern, but it's easiest. This is the
            # idempotency check and isn't a problem that needs to be handled.
            pass

    return True


def _drpms(v1_database, v2_database, report):
    return True


def _errata(v1_database, v2_database, report):

    v1_coll = v1_database.errata
    v2_coll = v2_database.units_erratum

    # Idempotency: We're lucky here, the uniqueness is just by ID, so we can
    # do a pre-fetch and determine what needs to be added.

    v2_errata_ids = [x['id'] for x in v2_coll.find({}, {'id' : 1})]
    missing_v1_errata = v1_coll.find({'id' : {'$nin' : v2_errata_ids}})

    new_errata = []
    for v1_erratum in missing_v1_errata:
        new_erratum = {
            '_id' : ObjectId(),
            '_storage_path' : None,
            'description' : v1_erratum['description'],
            'from_str' : v1_erratum['from_str'],
            'id' : v1_erratum['id'],
            'issued' : v1_erratum['issued'],
            'pushcount' : v1_erratum['pushcount'],
            'reboot_suggested' : v1_erratum['reboot_suggested'],
            'references' : v1_erratum['references'],
            'release' : v1_erratum['release'],
            'rights' : v1_erratum['rights'],
            'severity' : v1_erratum['severity'],
            'solution' : v1_erratum['solution'],
            'status' : v1_erratum['status'],
            'summary' : v1_erratum['summary'],
            'title' : v1_erratum['title'],
            'type' : v1_erratum['type'],
            'updated' : v1_erratum['updated'],
            'version' : v1_erratum['version'],
        }
        new_errata.append(new_erratum)

    if new_errata:
        v2_coll.insert(new_errata, safe=True)

    return True


def _distributions(v1_database, v2_database, report):

    # Idempotency: Like RPMs/SRPMs, this is ugly due to the complex key that
    # makes up unique distributions. It's complicated by the fact that in v1,
    # there is no uniqueness contraint on the collection, so it's possible
    # (however unlikely) that we'll run into data integrity issues.

    v1_coll = v1_database.distribution
    v2_coll = v2_database.units_distribution

    all_v1_distros = v1_coll.find()
    for v1_distro in all_v1_distros:
        new_distro = {
            '_id' : ObjectId(),
            '_content_type_id' : 'distribution',
            'id' : v1_distro['id'],
            'arch' : v1_distro['arch'],
            'version' : v1_distro['version'],
            'variant' : v1_distro['variant'],
            'family' : v1_distro['family'],
            'files' : v1_distro['files'],
        }

        # Storage path
        distro_path = os.path.join(DIR_DISTRIBUTION, new_distro['id'])
        new_distro['_storage_path'] = distro_path

        try:
            v2_coll.insert(new_distro, safe=True)
        except DuplicateKeyError:
            # Same pattern as for RPMs, try to insert and rely on the uniqueness
            # check in the DB to enforce idempotency.
            pass

    return True


def _package_groups(v1_database, v2_database, report):

    # In v2, the unique identifier for a package group is the
    # pairing of the group ID and the repository it's in. In v1, the package
    # group is embedded in the repo document itself, which is where we get
    # that information from.

    # In v1 the repository owns the relationship to a package group. Don't look
    # at the model class itself, it wasn't added there, but the code will still
    # stuff it in under the key "packagegroups". The value at that key is a dict
    # of group ID to a PackageGroup instance (v1 model).

    # Idempotency: The simplest way to handle this is to pre-load the set of
    # repo ID/group ID tuples into memory and verify each group found in each
    # v1 repo against that to determine if it has successfully been added or
    # not. The nice part about this over letting the uniqueness checks in mongo
    # itself is that we can batch the group inserts.

    v2_coll = v2_database.units_package_group

    # Tuple of repo ID and group ID
    already_added_tuples = [ (x['repo_id'], x['id']) for x in
                             v2_coll.find({}, {'repo_id' : 1, 'id' : 1}) ]

    v1_repos = v1_database.repos.find({}, {'id' : 1, 'packagegroups' : 1})
    for v1_repo in v1_repos:

        new_groups = [] # add the groups to the DB on a per repo basis
        for group_id in v1_repo.get('packagegroups', {}).keys():

            # Idempotency check
            if (v1_repo['id'], group_id) in already_added_tuples:
                continue

            v1_group = v1_repo['packagegroups'][group_id]
            new_group = {
                '_id' : ObjectId(),
                '_storage_path' : None,
                '_content_type_id' : 'package_group',
                'conditional_package_names' : v1_group['conditional_package_names'],
                'default' : v1_group['default'],
                'default_package_names' : v1_group['default_package_names'],
                'description' : v1_group['description'],
                'display_order' : v1_group['display_order'],
                'id' : v1_group['id'],
                'langonly' : v1_group['langonly'],
                'mandatory_package_names' : v1_group['mandatory_package_names'],
                'name' : v1_group['name'],
                'optional_package_names' : v1_group['optional_package_names'],
                'repo_id' : v1_repo['id'],
                'translated_description' : v1_group['translated_description'],
                'translated_name' : v1_group['translated_name'],
                'user_visible' : v1_group['user_visible'],
            }
            new_groups.append(new_group)

        if new_groups:
            v2_coll.insert(new_groups, safe=True)

    return True


def _package_group_categories(v1_database, v2_database, report):

    # These act nearly identically to groups, so see the comments in there
    # for more information.

    # Idempotency: As with groups, pre-load the tuples of repo ID to category
    # ID into memory and use that to check for the category's existed before
    # inserting.

    v2_coll = v2_database.units_package_category

    # Tuple of repo ID and group ID
    already_added_tuples = [ (x['repo_id'], x['id']) for x in
                             v2_coll.find({}, {'repo_id' : 1, 'id' : 1}) ]

    v1_repos = v1_database.repos.find({}, {'id' : 1, 'packagegroupcategories' : 1})
    for v1_repo in v1_repos:

        new_categories = [] # add the categories to the DB on a per repo basis
        for category_id in v1_repo.get('packagegroupcategories', {}).keys():

            # Idempotency check
            if (v1_repo['id'], category_id) in already_added_tuples:
                continue

            v1_category = v1_repo['packagegroupcategories'][category_id]
            new_category = {
                '_id' : ObjectId(),
                '_storage_path' : None,
                '_content_type_id' : 'package_category',
                'description' : v1_category['description'],
                'display_order' : v1_category['display_order'],
                'id' : v1_category['id'],
                'name' : v1_category['name'],
                'packagegroupids' : v1_category['packagegroupids'],
                'repo_id' : v1_repo['id'],
                'translated_description' : v1_category['translated_description'],
                'translated_name' : v1_category['translated_name'],
            }

            # As with groups, the database doesn't reflect the model.

            new_categories.append(new_category)

        if new_categories:
            v2_coll.insert(new_categories, safe=True)

    return True

# -- really private -----------------------------------------------------------

def _units_collection_name(type_id):
    # Again, the pulp.server code for generating this isn't used to prevent
    # issues if this scheme changes in the future (such a change will be applied
    # later in a migration script).

    return 'units_%s' % type_id

# -- point in time data -------------------------------------------------------

# Values for all type definitions at the point in Pulp's release cycle where
# the upgrade is expected to move to. Any changes that occur after that point
# will be handled by the pulp-manage-db script.
TYPE_DEFS = [
    {
        'id' : 'distribution',
        'display_name' : 'Distribution',
        'description' : 'Kickstart trees and all accompanying files',
        'unit_key' : ['id',  'family', 'variant', 'version', 'arch'],
        'search_indexes' : ['id', 'family', 'variant', 'version', 'arch'],
        'referenced_types' : [],
        },

    {
        'id' : 'drpm',
        'display_name' : 'DRPM',
        'description' : 'DRPM',
        'unit_key' :
            ['epoch',  'version', 'release', 'filename', 'checksumtype', 'checksum'],
        'search_indexes' :
            ['epoch',  'version', 'release', 'checksum', 'filename'],
        'referenced_types' : [],
    },

    {
        'id' : 'erratum',
        'display_name' : 'Erratum',
        'description' : 'Erratum advisory information',
        'unit_key' :
            ['id'],
        'search_indexes' : [
            'id', 'title', 'version', 'release', 'type',
            'status', 'updated', 'issued', 'severity', 'references'
        ],
        'referenced_types' : ['rpm'],
    },

    {
        'id' : 'package_group',
        'display_name' : 'Package Group',
        'description' : 'Yum Package group information',
        'unit_key' :
            ['id', 'repo_id'],
        'search_indexes' :
            ['id', 'repo_id', 'name', 'mandatory_package_names', 'conditional_package_names',
             'optional_package_names', 'default_package_names'],
        'referenced_types' : [],
    },

    {
        'id' : 'package_category',
        'display_name' : 'Package Category',
        'description' : 'Yum Package category information',
        'unit_key' :
            ['id', 'repo_id'],
        'search_indexes' :
            ['id', 'repo_id', 'name', 'packagegroupids'],
        'referenced_types' : [],
    },

    {
        'id' : 'rpm',
        'display_name' : 'RPM',
        'description' : 'RPM',
        'unit_key' :
            ['name', 'epoch', 'version', 'release', 'arch', 'checksumtype', 'checksum'],
        'search_indexes' :
            ['name', 'epoch', 'version', 'release', 'arch', 'filename', 'checksum', 'checksumtype'],
        'referenced_types' : ['erratum']
    },

    {
        'id' : 'srpm',
        'display_name' : 'SRPM',
        'description' : 'SRPM',
        'unit_key' :
            ['name', 'epoch', 'version', 'release', 'arch', 'checksumtype', 'checksum'],
        'search_indexes' :
            ['name', 'epoch', 'version', 'release', 'arch', 'filename', 'checksum', 'checksumtype'],
        'referenced_types' : [],
    },
]
