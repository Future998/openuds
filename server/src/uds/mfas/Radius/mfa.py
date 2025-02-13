# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Virtual Cable S.L.U.
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
@author: Daniel Torregrosa
"""

import typing
import logging

from django.utils.translation import gettext_noop as _, gettext

from uds import models
from uds.core import mfas
from uds.core.ui import gui

from uds.auths.Radius import client
from uds.auths.Radius.client import NOT_CHECKED, INCORRECT, CORRECT, NOT_NEEDED, NEEDED
from uds.core.auths.auth import webPassword
from uds.core.auths import exceptions

if typing.TYPE_CHECKING:
    from uds.core.module import Module
    from uds.core.util.request import ExtendedHttpRequest

logger = logging.getLogger(__name__)


class RadiusOTP(mfas.MFA):
    '''
    Validates OTP challenge against a proper configured Radius Server with OTP
    using 'Access-Challenge' response from Radius Server [RFC2865, RFC5080]
    '''

    typeName = _('Radius OTP Challenge')
    typeType = 'RadiusOTP'
    typeDescription = _('Radius OTP Challenge')
    iconFile = 'radius.png'
    cacheTime = 1  # In this MFA type there are not code generation nor sending... so ? 1 minute or too short ?

    server = gui.TextField(
        length=64,
        label=_('Host'),
        order=1,
        tooltip=_('Radius Server IP or Hostname'),
        required=True,
    )
    port = gui.NumericField(
        length=5,
        label=_('Port'),
        defvalue='1812',
        order=2,
        tooltip=_('Radius authentication port (usually 1812)'),
        required=True,
    )
    secret = gui.TextField(
        length=64,
        label=_('Secret'),
        order=3,
        tooltip=_('Radius client secret'),
        required=True,
    )
    all_users_otp = gui.CheckBoxField(
        label=_('All users must send OTP'),
        order=4,
        defvalue=True,
        tooltip=_(
            'If unchecked, an authentication step is needed in order to know if this user must enter OTP. '
            'If checked, all users must enter OTP, so authentication step is skipped.'
        ),
    )
    nasIdentifier = gui.TextField(
        length=64,
        label=_('NAS Identifier'),
        defvalue='uds-server',
        order=5,
        tooltip=_('NAS Identifier for Radius Server'),
        required=True,
    )

    responseErrorAction = gui.ChoiceField(
        label=_('Radius OTP communication error action'),
        order=31,
        defaultValue='0',
        tooltip=_('Action for OTP server communication error'),
        required=True,
        values={
            '0': _('Allow user login'),
            '1': _('Deny user login'),
            '2': _('Allow user to login if it IP is in the networks list'),
            '3': _('Deny user to login if it IP is in the networks list'),
        },
        tab=_('Config'),
    )

    networks = gui.MultiChoiceField(
        label=_('Radius OTP networks'),
        rdonly=False,
        rows=5,
        order=32,
        tooltip=_('Networks for Radius OTP authentication'),
        required=False,
        tab=_('Config'),
    )

    allowLoginWithoutMFA = gui.ChoiceField(
        label=_('User without defined OTP in server'),
        order=33,
        defaultValue='0',
        tooltip=_('Action for user without defined Radius Challenge'),
        required=True,
        values={
            '0': _('Allow user login'),
            '1': _('Deny user login'),
            '2': _('Allow user to login if it IP is in the networks list'),
            '3': _('Deny user to login if it IP is in the networks list'),
        },
        tab=_('Config'),
    )

    def initialize(self, values: 'Module.ValuesType') -> None:
        return super().initialize(values)

    def initGui(self) -> None:
        # Populate the networks list
        self.networks.setValues(
            [
                gui.choiceItem(v.uuid, v.name)
                for v in models.Network.objects.all().order_by('name')
            ]
        )

    def radiusClient(self) -> client.RadiusClient:
        """Return a new radius client ."""
        return client.RadiusClient(
            self.server.value,
            self.secret.value.encode(),
            authPort=self.port.num(),
            nasIdentifier=self.nasIdentifier.value,
        )

    def checkAction(self, action: str, request: 'ExtendedHttpRequest') -> bool:
        def checkIp() -> bool:
            return any(
                i.contains(request.ip)
                for i in models.Network.objects.filter(uuid__in=self.networks.value)
            )

        if action == '0':
            return True
        elif action == '1':
            return False
        elif action == '2':
            return checkIp()
        elif action == '3':
            return not checkIp()
        else:
            return False

    def checkResult(self, action: str, request: 'ExtendedHttpRequest') -> mfas.MFA.RESULT:
        if self.checkAction(action, request):
            return mfas.MFA.RESULT.OK
        raise Exception('User not allowed to login')

    def emptyIndentifierAllowedToLogin(self, request: 'ExtendedHttpRequest') -> bool:
        return self.checkAction(self.allowLoginWithoutMFA.value, request)

    def label(self) -> str:
        return gettext('OTP Code')

    def html(self, request: 'ExtendedHttpRequest') -> str:
        '''
        ToDo:
        - Maybe create a field in mfa definition to edit from admin panel ?
        - And/or add "Reply-Message" text from Radius Server response
        '''
        return gettext('Please enter OTP')

    def process(
        self,
        request: 'ExtendedHttpRequest',
        userId: str,
        username: str,
        identifier: str,
        validity: typing.Optional[int] = None,
    ) -> 'mfas.MFA.RESULT':
        '''
        check if this user must send OTP
        in order to check this, it is neccesary to first validate password (again) with radius server
        and get also radius State value (otp session)
        '''
        # if we are in a "all-users-otp" policy, avoid this step and go directly to ask for OTP
        if self.all_users_otp.value:
            return mfas.MFA.RESULT.OK

        web_pwd = webPassword(request)
        try:
            connection = self.radiusClient()
            auth_reply = connection.authenticate_challenge(username, password=web_pwd)
        except Exception as e:
            logger.error(
                "Exception found connecting to Radius OTP %s: %s", e.__class__, e
            )
            if not self.checkAction(self.responseErrorAction.value, request):
                raise Exception(_('Radius OTP connection error'))
            logger.warning(
                "Radius OTP connection error: Allowing access to user [%s] from IP [%s] without OTP",
                username,
                request.ip,
            )
            return mfas.MFA.RESULT.ALLOWED

        if auth_reply.pwd == INCORRECT:
            logger.warning(
                "Radius OTP error: User [%s] with invalid password from IP [%s]. Not synchronized password.",
                username,
                request.ip,
            )
            # we should not be here: not synchronized user password between auth server and radius server
            # What do we want to do here ??
            return self.checkResult(self.responseErrorAction.value, request)

        if auth_reply.otp_needed == NOT_NEEDED:
            logger.warning(
                "Radius OTP error: User [%s] without OTP data from IP [%s]",
                username,
                request.ip,
            )
            return self.checkResult(self.allowLoginWithoutMFA.value, request)

        # correct password and otp_needed
        return mfas.MFA.RESULT.OK

    def validate(
        self,
        request: 'ExtendedHttpRequest',
        userId: str,
        username: str,
        identifier: str,
        code: str,
        validity: typing.Optional[int] = None,
    ) -> None:
        '''
        Validate the OTP code

        we could have saved state+replyMessage in ddbb at "process" step and reuse it here
        but finally it is a lot easier to generate new one on each otp try
        otherwise we need to redirect to username/password form in each otp try in order to
        regenerate a new State after a wrong sent OTP code
        slightly less efficient but a lot simpler
        '''

        try:
            err = _('Invalid OTP code')

            web_pwd = webPassword(request)
            try:
                connection = self.radiusClient()
                auth_reply = connection.authenticate_challenge(
                    username, password=web_pwd, otp=code
                )
            except Exception as e:
                logger.error(
                    "Exception found connecting to Radius OTP %s: %s", e.__class__, e
                )
                if not self.checkAction(self.responseErrorAction.value, request):
                    raise Exception(_('Radius OTP connection error'))
                logger.warning(
                    "Radius OTP connection error: Allowing access to user [%s] from IP [%s] without OTP",
                    username,
                    request.ip,
                )
                return

            logger.debug("otp auth_reply: %s", auth_reply)
            if auth_reply.otp == CORRECT:
                logger.warning(
                    "Radius OTP correctly logged in: Allowing access to user [%s] from IP [%s] with correct OTP",
                    username,
                    request.ip,
                )
                return

        except Exception as e:
            # Any error means invalid code
            err = str(e)

        logger.warning(
            "Radius OTP error: Denying access to user [%s] from IP [%s] with incorrect OTP",
            username,
            request.ip,
        )
        raise exceptions.MFAError(err)
