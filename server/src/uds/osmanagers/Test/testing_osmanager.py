# -*- coding: utf-8 -*-

#
# Copyright (c) 2012-2019 Virtual Cable S.L.
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
@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import logging
import typing

from django.utils.translation import gettext_noop as _, gettext_lazy

from uds.core.services import types as serviceTypes
from uds.core.ui import gui
from uds.core import osmanagers
from uds.core.util.state import State
from uds.core.util import log
from uds.core.managers import userServiceManager

if typing.TYPE_CHECKING:
    from uds.models.user_service import UserService
    from uds.core.module import Module

logger = logging.getLogger(__name__)


class TestOSManager(osmanagers.OSManager):
    typeName = _('Test OS Manager')
    typeType = 'TestOsManager'
    typeDescription = _('Os Manager for testing pourposes')
    iconFile = 'osmanager.png'

    servicesType = serviceTypes.ALL

    onLogout = gui.ChoiceField(
        label=_('Logout Action'),
        order=10,
        rdonly=True,
        tooltip=_('What to do when user logs out from service'),
        values=[
            {'id': 'keep', 'text': gettext_lazy('Keep service assigned')},
            {'id': 'remove', 'text': gettext_lazy('Remove service')},
            {
                'id': 'keep-always',
                'text': gettext_lazy('Keep service assigned even on new publication'),
            },
        ],
        defvalue='keep',
    )

    idle = gui.NumericField(
        label=_("Max.Idle time"),
        length=4,
        defvalue=-1,
        rdonly=False,
        order=11,
        tooltip=_(
            'Maximum idle time (in seconds) before session is automatically closed to the user (<= 0 means no max. idle time)'
        ),
        required=True,
    )

    def initialize(self, values: 'Module.ValuesType'):
        self.processUnusedMachines = True

    def release(self, userService: 'UserService') -> None:
        logger.debug('User service %s released', userService)

    def isRemovableOnLogout(self, userService: 'UserService') -> bool:
        '''
        Says if a machine is removable on logout
        '''
        if not userService.in_use:
            if (self.onLogout.value == 'remove') or (
                not userService.isValidPublication() and self.onLogout.value == 'keep'
            ):
                return True

        return False

    def getName(self, userService: 'UserService') -> str:
        """
        gets name from deployed
        """
        return userService.getName()

    def doLog(self, service, data, origin=log.OSMANAGER):
        # Stores a log associated with this service
        try:
            msg, level = data.split('\t')
            try:
                level = int(level)
            except Exception:
                logger.debug('Do not understand level %s', level)
                level = log.INFO
            log.doLog(service, level, msg, origin)
        except Exception:
            log.doLog(service, log.ERROR, "do not understand {0}".format(data), origin)

    def actorData(
        self, userService: 'UserService'
    ) -> typing.MutableMapping[str, typing.Any]:
        return {'action': 'rename', 'name': userService.getName()}

    def processUnused(self, userService: 'UserService') -> None:
        """
        This will be invoked for every assigned and unused user service that has been in this state at least 1/2 of Globalconfig.CHECK_UNUSED_TIME
        This function can update userService values. Normal operation will be remove machines if this state is not valid
        """
        if self.isRemovableOnLogout(userService):
            log.doLog(
                userService,
                log.INFO,
                'Unused user service for too long. Removing due to OS Manager parameters.',
                log.OSMANAGER,
            )
            userService.remove()

    def isPersistent(self):
        return self.onLogout.value == 'keep-always'

    def checkState(self, userService: 'UserService') -> str:
        logger.debug('Checking state for service %s', userService)
        return State.RUNNING

    def maxIdle(self) -> typing.Optional[int]:
        """
        On production environments, will return no idle for non removable machines
        """
        if (
            self.idle.value <= 0
        ):  # or (settings.DEBUG is False and self._onLogout != 'remove'):
            return None

        return self.idle.value
