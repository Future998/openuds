# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2021 Virtual Cable S.L.U.
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

"""
Created on Jul 29, 2011

@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import random
import string
import logging
import typing

from django.utils.translation import ugettext_noop as _, ugettext_lazy

from uds.core.managers.user_preferences import CommonPrefs
from uds.core.ui import gui
from uds.core import transports
from uds.models import TicketStore
from uds.core.util import os_detector as OsDetector

from .nxfile import NXFile
from .nxbase import BaseNXTransport


logger = logging.getLogger(__name__)

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from uds.core import Module
    from uds import models
    from django.http import HttpRequest  # pylint: disable=ungrouped-imports


class TSNXTransport(BaseNXTransport):
    """
    Provides access via NX to service.
    This transport can use an domain. If username processed by authenticator contains '@', it will split it and left-@-part will be username, and right password
    """

    typeName = _('NX v3.5 (DEPRECATED)')
    typeType = 'TSNXTransport'
    typeDescription = _('NX protocol v3.5. Tunneled connection.')
    iconFile = 'nx.png'
    protocol = transports.protocols.NX
    group = transports.TUNNELED_GROUP

    tunnelServer = gui.TextField(
        label=_('Tunnel server'),
        order=1,
        tooltip=_(
            'IP or Hostname of tunnel server sent to client device ("public" ip) and port. (use HOST:PORT format)'
        ),
        tab=gui.TUNNEL_TAB,
    )

    tunnelWait = gui.NumericField(
        length=3,
        label=_('Tunnel wait time'),
        defvalue='30',
        minValue=5,
        maxValue=65536,
        order=2,
        tooltip=_('Maximum time to wait before closing the tunnel listener'),
        required=True,
        tab=gui.TUNNEL_TAB,
    )

    ticketValidity = gui.NumericField(
        length=3,
        label=_('Tunnel ticket validity time (seconds)'),
        defvalue='7200',
        minValue=60,          # One minute as min
        maxValue=7*60*60*24,  # one week as max
        order=3,
        tooltip=_('Maximum validity time for user ticket to allow reconnection'),
        required=True,
        tab=gui.TUNNEL_TAB,
    )

    verifyCertificate = gui.CheckBoxField(
        label=_('Force SSL certificate verification'),
        order=23,
        tooltip=_('If enabled, the certificate of tunnel server will be verified (recommended).'),
        defvalue=gui.TRUE,
        tab=gui.TUNNEL_TAB
    )


    useEmptyCreds = gui.CheckBoxField(
        label=_('Empty creds'),
        order=3,
        tooltip=_('If checked, the credentials used to connect will be emtpy'),
        tab=gui.CREDENTIALS_TAB,
    )
    fixedName = gui.TextField(
        label=_('Username'),
        order=4,
        tooltip=_('If not empty, this username will be always used as credential'),
        tab=gui.CREDENTIALS_TAB,
    )
    fixedPassword = gui.PasswordField(
        label=_('Password'),
        order=5,
        tooltip=_('If not empty, this password will be always used as credential'),
        tab=gui.CREDENTIALS_TAB,
    )
    listenPort = gui.NumericField(
        label=_('Listening port'),
        length=5,
        order=6,
        tooltip=_('Listening port of NX (ssh) at client machine'),
        defvalue='22',
    )
    connection = gui.ChoiceField(
        label=_('Connection'),
        order=7,
        tooltip=_('Connection speed for this transport (quality)'),
        values=[
            {'id': 'modem', 'text': 'modem'},
            {'id': 'isdn', 'text': 'isdn'},
            {'id': 'adsl', 'text': 'adsl'},
            {'id': 'wan', 'text': 'wan'},
            {'id': 'lan', 'text': 'lan'},
        ],
        tab=gui.PARAMETERS_TAB,
    )
    session = gui.ChoiceField(
        label=_('Session'),
        order=8,
        tooltip=_('Desktop session'),
        values=[
            {'id': 'gnome', 'text': 'gnome'},
            {'id': 'kde', 'text': 'kde'},
            {'id': 'cde', 'text': 'cde'},
        ],
        tab=gui.PARAMETERS_TAB,
    )
    cacheDisk = gui.ChoiceField(
        label=_('Disk Cache'),
        order=9,
        tooltip=_('Cache size en Mb stored at disk'),
        values=[
            {'id': '0', 'text': '0 Mb'},
            {'id': '32', 'text': '32 Mb'},
            {'id': '64', 'text': '64 Mb'},
            {'id': '128', 'text': '128 Mb'},
            {'id': '256', 'text': '256 Mb'},
            {'id': '512', 'text': '512 Mb'},
        ],
        tab=gui.PARAMETERS_TAB,
    )
    cacheMem = gui.ChoiceField(
        label=_('Memory Cache'),
        order=10,
        tooltip=_('Cache size en Mb kept at memory'),
        values=[
            {'id': '4', 'text': '4 Mb'},
            {'id': '8', 'text': '8 Mb'},
            {'id': '16', 'text': '16 Mb'},
            {'id': '32', 'text': '32 Mb'},
            {'id': '64', 'text': '64 Mb'},
            {'id': '128', 'text': '128 Mb'},
        ],
        tab=gui.PARAMETERS_TAB,
    )
    screenSize = gui.ChoiceField(
        label=_('Screen size'),
        order=10,
        tooltip=_('Screen size'),
        defvalue=CommonPrefs.SZ_FULLSCREEN,
        values=[
            {'id': CommonPrefs.SZ_640x480, 'text': '640x480'},
            {'id': CommonPrefs.SZ_800x600, 'text': '800x600'},
            {'id': CommonPrefs.SZ_1024x768, 'text': '1024x768'},
            {'id': CommonPrefs.SZ_1366x768, 'text': '1366x768'},
            {'id': CommonPrefs.SZ_1920x1080, 'text': '1920x1080'},
            {'id': CommonPrefs.SZ_FULLSCREEN, 'text': ugettext_lazy('Full Screen')},
        ],
        tab=gui.PARAMETERS_TAB,
    )

    _tunnelServer: str = ''
    _tunnelCheckServer: str = ''
    _useEmptyCreds: bool = False
    _fixedName: str = ''
    _fixedPassword: str = ''
    _listenPort: str = ''
    _connection: str = ''
    _session: str = ''
    _cacheDisk: str = ''
    _cacheMem: str = ''
    _screenSize: str = ''
    _tunnelWait: int = 30
    _ticketValidity: int = 60
    _verifyCertificate: bool = False

    def initialize(self, values: 'Module.ValuesType'):
        if values:
            if values['tunnelServer'].find(':') == -1:
                raise transports.Transport.ValidationException(
                    _('Must use HOST:PORT in Tunnel Server Field')
                )
            self._tunnelServer = values['tunnelServer']
            self._tunnelWait = int(values['tunnelWait'])
            self._ticketValidity = int(values['ticketValidity'])
            self._verifyCertificate = gui.strToBool(values['verifyCertificate'])
            self._tunnelCheckServer = ''
            self._useEmptyCreds = gui.strToBool(values['useEmptyCreds'])
            self._fixedName = values['fixedName']
            self._fixedPassword = values['fixedPassword']
            self._listenPort = values['listenPort']
            self._connection = values['connection']
            self._session = values['session']
            self._cacheDisk = values['cacheDisk']
            self._cacheMem = values['cacheMem']
            self._screenSize = values['screenSize']
            

    def marshal(self) -> bytes:
        """
        Serializes the transport data so we can store it in database
        """
        val = str.join(
            '\t',
            [
                'v3',
                gui.boolToStr(self._useEmptyCreds),
                self._fixedName,
                self._fixedPassword,
                self._listenPort,
                self._connection,
                self._session,
                self._cacheDisk,
                self._cacheMem,
                self._tunnelServer,
                self._tunnelCheckServer,
                self._screenSize,
                str(self._tunnelWait),
                str(self._ticketValidity),
                gui.boolToStr(self._verifyCertificate),
            ],
        )
        logger.debug('Values: %s', val)
        return val.encode('utf8')

    def unmarshal(self, data: bytes) -> None:
        values = data.decode('utf8').split('\t')
        if values[0] in ('v1', 'v2', 'v3'):
            self._useEmptyCreds = gui.strToBool(values[1])
            (
                self._fixedName,
                self._fixedPassword,
                self._listenPort,
                self._connection,
                self._session,
                self._cacheDisk,
                self._cacheMem,
                self._tunnelServer,
                self._tunnelCheckServer,
            ) = values[2:11]
            self._screenSize = (
                values[11] if values[0] == 'v2' else CommonPrefs.SZ_FULLSCREEN
            )
            if values[0] == 'v3':
                self._tunnelWait, self._ticketValidity, self._verifyCertificate = (
                    int(values[12]),
                    int(values[13]),
                    gui.strToBool(values[14])
                )

    def valuesDict(self) -> gui.ValuesDictType:
        return {
            'useEmptyCreds': gui.boolToStr(self._useEmptyCreds),
            'fixedName': self._fixedName,
            'fixedPassword': self._fixedPassword,
            'listenPort': self._listenPort,
            'connection': self._connection,
            'session': self._session,
            'cacheDisk': self._cacheDisk,
            'cacheMem': self._cacheMem,
            'tunnelServer': self._tunnelServer,
            'tunnelWait': str(self._tunnelWait),
            'ticketValidity': str(self._ticketValidity),
            'verifyCertificate': gui.boolToStr(self._verifyCertificate),
        }

    def getUDSTransportScript(  # pylint: disable=too-many-locals
        self,
        userService: 'models.UserService',
        transport: 'models.Transport',
        ip: str,
        os: typing.Dict[str, str],
        user: 'models.User',
        password: str,
        request: 'HttpRequest',
    ) -> typing.Tuple[str, str, typing.Dict[str, typing.Any]]:
        prefs = self.screenSize.value

        username = user.getUsernameForAuth()
        proc = username.split('@')
        username = proc[0]
        if self._fixedName is not '':
            username = self._fixedName
        if self._fixedPassword is not '':
            password = self._fixedPassword
        if self._useEmptyCreds is True:
            usernamsizerd = '', ''

        ticket = TicketStore.create_for_tunnel(
            userService=userService,
            port=3389,
            validity=self.ticketValidity.num()
        )

        tunHost, tunPort = self.tunnelServer.value.split(':')

        width, height = CommonPrefs.getWidthHeight(prefs)
        # Fix username/password acording to os manager
        username, password = userService.processUserPassword(username, password)

        r = NXFile(username=username, password=password, width=width, height=height)
        r.host = '{address}'
        r.port = '{port}'
        r.linkSpeed = self._connection
        r.desktop = self._session
        r.cachedisk = self._cacheDisk
        r.cachemem = self._cacheMem

        osName = {
            OsDetector.Windows: 'windows',
            OsDetector.Linux: 'linux',
            OsDetector.Macintosh: 'macosx',
        }.get(os['OS'])

        if osName is None:
            return super().getUDSTransportScript(
                userService, transport, ip, os, user, password, request
            )

        sp = {
            'ip': ip,
            'tunHost': tunHost,
            'tunPort': tunPort,
            'tunWait': self.tunnelWait.num(),
            'tunChk': self.verifyCertificate.isTrue(),
            'ticket': ticket,
            'port': self._listenPort,
            'as_file_for_format': r.as_file_for_format,
        }

        return self.getScript('scripts/{}/tunnel.py', osName, sp)
