#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
from pulp.server.LDAPConnection import LDAPConnection
from logging import INFO, basicConfig

basicConfig(filename='/tmp/populate.log', level=INFO)

class LDAPAttribute:
    def __init__(self):
        self.objectclass = ['top']
        self.cn          = ''
        self.sn          = ''
        self.userid      = ''
        self.userPassword= ''
        self.description = ''
        self.dn = ''
        self.email = ''

    def setObjectclass(self, oclass):
        self.objectclass.append(oclass)

    def setCN(self, cn):
        self.cn = cn

    def setSN(self, sn):
        self.sn = sn

    def setuserId(self, id):
        self.userid = id

    def setuserPassword(self, password):
        self.userPassword = password

    def setDescription(self, description):
        self.description = description

    def setMail(self, email):
        self.email = email

    def setDN(self, dn):
        self.dn = dn

    def buildBody(self):
        attrs = {}
        attrs['objectclass'] = self.objectclass 
        attrs['cn']          = self.cn
        attrs['sn']          = self.sn
        attrs['uid']      = self.userid
        attrs['userPassword'] = self.userPassword
        attrs['description '] = self.description
        attrs['mail'] = self.email
        return attrs, self.dn


def main():
    """
    Populate ldap server with some test data
    """
    print("See populate.log for descriptive output.")
    ldapserv = LDAPConnection('cn=Directory Manager', \
                              'redhat',
                              'ldap://localhost')
    ldapserv.connect()
    for id in range(1,100):
        userid = 'pulpuser%s' % id
        lattr = LDAPAttribute()
        lattr.setObjectclass('Person')
        lattr.setObjectclass('organizationalPerson')
        lattr.setObjectclass('inetorgperson')
        lattr.setCN(userid)
        lattr.setSN(userid)
        lattr.setuserId(userid)
        lattr.setuserPassword('redhat')
        lattr.setDescription('pulp ldap test user')
        lattr.setMail('%s@redhat.com' % userid)
        lattr.setDN("uid=%s,dc=rdu,dc=redhat,dc=com" % userid)
        attr, dn = lattr.buildBody()
        ldapserv.add_users(dn, attrs=attr)
    ldapserv.lookup_user("dc=rdu,dc=redhat,dc=com", "pulpuser1")
    ldapserv.authenticate_user("dc=rdu,dc=redhat,dc=com", "pulpuser1", "redhat")
    ldapserv.disconnect()

if __name__ == '__main__':
    main()
