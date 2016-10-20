# -*- coding: utf-8 -*-

#
# Copyright (c) 2016 Virtual Cable S.L.
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

from django.utils.translation import ugettext_noop as _
from uds.core.managers.UserPrefsManager import CommonPrefs
from uds.core.ui.UserInterface import gui
from uds.core.transports.BaseTransport import Transport
from uds.core.transports import protocols
from uds.core.util import OsDetector

# This transport is specific for oVirt, so we need to point to it

import paramiko
import six
import os
import logging

__updated__ = '2016-10-20'


logger = logging.getLogger(__name__)

READY_CACHE_TIMEOUT = 30
SSH_KEY_LENGTH = 1024

class BaseX2GOTransport(Transport):
    '''
    Provides access via RDP to service.
    This transport can use an domain. If username processed by authenticator contains '@', it will split it and left-@-part will be username, and right password
    '''
    iconFile = 'x2go.png'
    protocol = protocols.X2GO
    supportedOss = OsDetector.Linux

    useEmptyCreds = gui.CheckBoxField(
        order=1,
        label=_('Empty credentials'),
        tooltip=_('If checked, the credentials used to connect will be emtpy'),
        tab=gui.CREDENTIALS_TAB
    )
    fixedName = gui.TextField(
        order=2,
        label=_('Username'),
        tooltip=_('If not empty, this username will be always used as credential'),
        tab=gui.CREDENTIALS_TAB
    )
    fixedPassword = gui.PasswordField(
        order=3,
        label=_('Password'),
        tooltip=_('If not empty, this password will be always used as credential'),
        tab=gui.CREDENTIALS_TAB
    )

    fullScreen = gui.CheckBoxField(
        order=10,
        label=_('Show fullscreen'),
        tooltip=_('If checked, viewer will be shown on fullscreen mode-'),
        tab=gui.PARAMETERS_TAB
    )

    desktopType = gui.ChoiceField(label=_('Desktop'), order=11, tooltip=_('Desktop session'),
                              values=[
                                  {'id': 'XFCE', 'text': 'Xfce'},
                                  {'id': 'MATE', 'text': 'Mate'},
                                  {'id': 'LXDE', 'text': 'Lxde'},
                                  {'id': 'GNOME', 'text': 'Gnome (see docs)'},
                                  {'id': 'KDE', 'text': 'Kde (see docs)'},
                                  # {'id': 'UNITY', 'text': 'Unity (see docs)'},
                                  {'id': 'gnome-session-cinnamon', 'text': 'Cinnamon 1.4 (see docs)'},
                                  {'id': 'gnome-session-cinnamon2d', 'text': 'Cinnamon 2.2 (see docs)'},
    ], tab=gui.PARAMETERS_TAB)

    keyboardLayout = gui.TextField(label=_('Keyboard'), order=12, tooltip=_('Keyboard layout (es, us, fr, ...). Empty value means autodetect.'),
        default='',
        tab=gui.ADVANCED_TAB
    )



    def isAvailableFor(self, userService, ip):
        '''
        Checks if the transport is available for the requested destination ip
        Override this in yours transports
        '''
        logger.debug('Checking availability for {0}'.format(ip))
        return True  # Spice is available, no matter what IP machine has (even if it does not have one)

    def processedUser(self, userService, userName):
        v = self.processUserPassword(userService, userName, '')
        return v['username']

    def processUserPassword(self, service, user, password):
        username = user.getUsernameForAuth()

        if self.fixedName.value != '':
            username = self.fixedName.value

        if self.fixedPassword.value != '':
            password = self.fixedPassword.value
        if self.useEmptyCreds.isTrue():
            username, password = '', '', ''

        # Fix username/password acording to os manager
        username, password = service.processUserPassword(username, password)

        return {'protocol': self.protocol, 'username': username, 'password': password}

    def getConnectionInfo(self, service, user, password):
        return self.processUserPassword(service, user, password)

    def genKeyPairForSsh(self):
        '''
        Generates a key pair for use with x2go
        The private part is used by client
        the public part must be "appended" to authorized_keys if it is not already added.
        If .ssh folder does not exists, it must be created
        if authorized_keys does not exists, it must be created
        On key adition, we can look for every key that has a "UDS@X2GOCLIENT" as comment, so we can remove them before adding new ones

        Windows (tested):
            C:\Program Files (x86)\x2goclient>x2goclient.exe --session-conf=c:/temp/sessions --session=UDS/test-session --close-disconnect --hide --no-menu
        Linux (tested):
            HOME=[temporal folder, where we create a .x2goclient folder and a sessions inside] pyhoca-cli -P UDS/test-session
        '''
        key = paramiko.RSAKey.generate(SSH_KEY_LENGTH)
        privFile = six.StringIO()
        key.write_private_key(privFile)
        priv = privFile.getvalue()

        pub = key.get_base64()  # 'ssh-rsa {} UDS@X2GOCLIENT'.format(key.get_base64())
        return (priv, pub)

    def getAuthorizeScript(self, user, pubKey):
        return self.getScript('scripts/authorize.py'.format(user=user, key=pubKey))

    def getScript(self, script):
        with open(os.path.join(os.path.dirname(__file__), script)) as f:
            data = f.read()
        return data
