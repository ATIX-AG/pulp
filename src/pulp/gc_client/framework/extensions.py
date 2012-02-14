# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Classes used in the writing of Pulp client extensions. This includes both
the objects passed into the components during initialization as well as
the base classes that extension components must implement.
"""

from okaara.cli import Section, Command

# -- component initialization -------------------------------------------------

class ClientContext:

    def __init__(self, server, config, logger, cli=None, shell=None):
        self.server = server
        self.config = config
        self.logger = logger

        self.cli = cli
        self.shell = shell

    def server(self):
        return self.server

    def config(self):
        return self.config

    def logger(self):
        return self.logger

# -- cli components -----------------------------------------------------------

class PulpCliSection(Section):
    pass

class PulpCliCommnad(Command):
    pass
