# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from collections import namedtuple
from gettext import gettext as _

Error = namedtuple('Error', ['code', 'message', 'required_fields'])
"""
The error named tuple has 4 components:
code: The 7 character uniquely identifying code for this error, 3 A-Z identifying the module
      followed by 4 numeric characters for the msg id.  All general pulp server errors start
      with PLP
message: The message that will be printed for this error
required_files: A list of required fields for printing the message
"""

# The PLP0000 error is to wrap non-pulp exceptions
PLP0000 = Error("PLP0000",
                "%(message)s", ['message'])
PLP0001 = Error("PLP0001",
                _("A general pulp exception occurred"), [])
PLP0002 = Error("PLP0002",
                _("Errors occurred updating bindings on consumers for repo %(repo_id)s and "
                "distributor %(distributor_id)s"), ['repo_id', 'distributor_id'])
PLP0003 = Error("PLP0003",
                _("Errors occurred removing bindings on consumers while deleting a distributor for "
                  "repo %(repo_id)s and distributor %(distributor_id)s"),
                ['repo_id', 'distributor_id'])
PLP0004 = Error("PLP0004",
                _("Errors occurred creating bindings for the repository group %(group_id)s.  "
                  "Binding creation was attempted for the repository %(repo_id)s and "
                  "distributor %(distributor_id)s"),
                ['repo_id', 'distributor_id', 'group_id'])

PLP0005 = Error("PLP0005",
                _("Errors occurred deleting bindings for the repository group %(group_id)s.  "
                  "Binding deletion was attempted for the repository %(repo_id)s and "
                  "distributor %(distributor_id)s"),
                ['repo_id', 'distributor_id', 'group_id'])
PLP0006 = Error("PLP0006", _("Errors occurred while updating the distributor configuration for "
                             "repository %(repo_id)s"),
                ['repo_id'])
PLP0007 = Error("PLP0007",
                _("Error occurred while cascading delete of repository %(repo_id)s to distributor "
                  "bindings associated with it."),
                ['repo_id'])
PLP0008 = Error("PLP0008",
                _("Error raising error %(code).  "
                  "The field [%(field)s] was not included in the error_data."),
                ['code', 'field'])
PLP0009 = Error("PLP0009", _("Missing resource(s): %(resources)s"), ['resources'])
PLP0010 = Error("PLP0010", _("Conflicting operation reasons: %(r)s"), ['reasons'])
PLP0011 = Error("PLP0011", _("Operation timed out after: %(timeout)s"), ['timeout'])
PLP0012 = Error("PLP0012", _("Operation postponed"), [])
PLP0014 = Error("PLP0014", _('Operation not implemented: %(operation_name)s'), ['operation_name'])
PLP0015 = Error("PLP0015", _('Invalid properties: %(properties)s'), ['properties'])
PLP0016 = Error("PLP0016", _('Missing values for: %(properties)s'), ['properties'])
PLP0017 = Error("PLP0017", _('Unsupported properties: %(properties)s'), ['properties'])
PLP0018 = Error("PLP0018", _('Duplicate resource: %(resource_id)s'), ['resource_id'])
PLP0019 = Error("PLP0019", _('Pulp only accepts input encoded in UTF-8: %(value)s'), ['value'])
PLP0020 = Error("PLP0020",
                _("Errors occurred installing content for the consumer group %(group_id)s."),
                ['group_id'])
PLP0021 = Error("PLP0021",
                _("Errors occurred updating content for the consumer group %(group_id)s."),
                ['group_id'])
PLP0022 = Error("PLP0022",
                _("Errors occurred uninstalling content for the consumer group %(group_id)s."),
                ['group_id'])
PLP0023 = Error("PLP0023", _("Task is already in a complete state: %(task_id)s"), ['task_id'])

# Create a section for general validation errors (PLP1000 - PLP2999)
# Validation problems should be reported with a general PLP1000 error with a more specific
# error message nested inside of it.
PLP1000 = Error("PLP1000", _("A validation error occurred."), [])
PLP1001 = Error("PLP1001", _("The consumer %(consumer_id)s does not exist."), ['consumer_id'])
PLP1002 = Error("PLP1002", _("The field %(field) must have a value specified."), ['field'])
PLP1003 = Error("PLP1003", _("The value specified for the field %(field) must be made up of letters"
                             ", numbers, underscores, or hyphens with no spaces."), ['field'])
PLP1004 = Error("PLP1004", _("An object of type %(type) already exists in the database with an id of %(object_id)"), ['type', 'object_id'])
PLP1005 = Error("PLP1005", _("The checksum type %(checksum_type)s is unknown."), ['checksum_type'])
