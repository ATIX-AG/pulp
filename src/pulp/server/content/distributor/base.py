# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class Distributor(object):
    """
    Base class for distributor plugin development.
    """

    @classmethod
    def metadata(cls):
        return {}

    def publish_repo(self, repo_data, publish_conduit, distributor_config=None, repo_config=None):
        """
        Publish a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param publish_conduit: api instance that provides limited pulp functionality
        @type publish_conduit: L{PluginAPI} instance
        @param distributor_config: configuration for distributor instance
        @type distributor_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        raise NotImplementedError()

    def unpublish_repo(self, repo_data, unpublish_conduit, distributor_config=None, repo_config=None):
        """
        Unpublish a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param unpublish_conduit: api instance that provides limited pulp functionality
        @type unpublish_conduit: L{ContentPluginHook} instance
        @param distributor_config: configuration for distributor instance
        @type distributor_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        raise NotImplementedError()
