# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Virtual Cable S.L.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Virtual Cable S.L. nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''

from __future__ import unicode_literals

from django.utils.translation import ugettext_noop as _, ugettext
from uds.core.ui.UserInterface import gui
from uds.core.util.Cache import Cache
from uds.core.util import net
from uds.core.transports.BaseTransport import Transport
from uds.core.transports import protocols
from uds.core.util import connection
from uds.core.util import OsDetector

import uuid
import logging

logger = logging.getLogger(__name__)

READY_CACHE_TIMEOUT = 30


class HTML5RDPTransport(Transport):
    '''
    Provides access via RDP to service.
    This transport can use an domain. If username processed by authenticator contains '@', it will split it and left-@-part will be username, and right password
    '''
    typeName = _('HTML5 RDP Transport')
    typeType = 'HTML5RDPTransport'
    typeDescription = _('RDP Transport using HTML5 client')
    iconFile = 'rdp.png'
    needsJava = False  # If this transport needs java for rendering
    supportedOss = OsDetector.allOss
    protocol = protocols.RDP

    guacamoleServer = gui.TextField(label=_('Tunnel Server'), order=1, tooltip=_('Host of the tunnel server (use http/https & port if needed) as accesible from users'), defvalue='https://', length=64, required=True)
    useEmptyCreds = gui.CheckBoxField(label=_('Empty creds'), order=2, tooltip=_('If checked, the credentials used to connect will be emtpy'))
    fixedName = gui.TextField(label=_('Username'), order=3, tooltip=_('If not empty, this username will be always used as credential'))
    fixedPassword = gui.PasswordField(label=_('Password'), order=4, tooltip=_('If not empty, this password will be always used as credential'))
    withoutDomain = gui.CheckBoxField(label=_('Without Domain'), order=5, tooltip=_('If checked, the domain part will always be emptied (to connecto to xrdp for example is needed)'))
    fixedDomain = gui.TextField(label=_('Domain'), order=6, tooltip=_('If not empty, this domain will be always used as credential (used as DOMAIN\\user)'))
    enableAudio = gui.CheckBoxField(label=_('Enable Audio'), order=7, tooltip=_('If checked, the audio will be redirected to client (if client browser supports it)'))
    enablePrinting = gui.CheckBoxField(label=_('Enable Printing'), order=8, tooltip=_('If checked, the printing will be redirected to client (if client browser supports it)'))

    def initialize(self, values):
        if values is None:
            return
        if self.guacamoleServer.value[0:4] != 'http':
            raise Transport.ValidationException(_('The server must be http or https'))

    # Same check as normal RDP transport
    def isAvailableFor(self, ip):
        '''
        Checks if the transport is available for the requested destination ip
        Override this in yours transports
        '''
        logger.debug('Checking availability for {0}'.format(ip))
        ready = self.cache().get(ip)
        if ready is None:
            # Check again for readyness
            if connection.testServer(ip, '3389') is True:
                self.cache().put(ip, 'Y', READY_CACHE_TIMEOUT)
                return True
            else:
                self.cache().put(ip, 'N', READY_CACHE_TIMEOUT)
        return ready == 'Y'

    def processedUser(self, userService, userName):
        v = self.processUserPassword(userService, userName, '')
        return v['username']

    def processUserPassword(self, service, user, password):
        username = user.getUsernameForAuth()

        if self.fixedName.value is not '':
            username = self.fixedName.value

        proc = username.split('@')
        if len(proc) > 1:
            domain = proc[1]
        else:
            domain = ''
        username = proc[0]

        if self.fixedPassword.value is not '':
            password = self.fixedPassword.value
        if self.fixedDomain.value is not '':
            domain = self.fixedDomain.value
        if self.useEmptyCreds.isTrue():
            username, password, domain = '', '', ''

        if self.withoutDomain.isTrue():
            domain = ''

        if '.' in domain:  # Dotter domain form
            username = username + '@' + domain
            domain = ''

        # Fix username/password acording to os manager
        username, password = service.processUserPassword(username, password)

        return {'protocol': self.protocol, 'username': username, 'password': password, 'domain': domain}

    def renderForHtml(self, userService, transport, ip, os, user, password):
        ci = self.processUserPassword(userService, user, password)
        username, password, domain = ci['username'], ci['password'], ci['domain']

        if domain != '':
            username = domain + '\\' + username

        # Build params dict
        params = {
            'protocol': 'rdp',
            'hostname': ip,
            'username': username,
            'password': password,
            'ignore-cert': 'true'
        }

        if self.enableAudio.isTrue() is False:
            params['disable-audio'] = 'true'

        if self.enablePrinting.isTrue() is True:
            params['enable-printing'] = 'true'

        logger.debug('RDP Params: {0}'.format(params))

        cache = Cache('guacamole')
        key = uuid.uuid4().hex
        cache.put(key, params)

        url = "{0}/transport/?{1}".format(self.guacamoleServer.value, key)
        return '''
        <script type="text/javascript">
        $(document).ready(function() {{
            var url = "{0}&" + window.location.protocol + "//" + window.location.host + "/";
            window.location = url;
        }})
        </script>
        <div>{1}...</div>
        '''.format(url, ugettext('Launching HTML5 RDP connection'))

