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

# pylint: disable=too-many-public-methods

from __future__ import unicode_literals

from django.utils.translation import ugettext as _


from uds.models import CalendarAccess, Calendar
from uds.core.util.State import State
from uds.core.util.model import processUuid
from uds.core.util import log
from uds.REST.model import DetailHandler
from uds.REST import ResponseError
from uds.core.util import permissions



import logging

logger = logging.getLogger(__name__)

ALLOW = 'ALLOW'
DENY = 'DENY'


class AccessCalendars(DetailHandler):
    '''
    Processes the transports detail requests of a Service Pool
    '''
    def getItems(self, parent, item):
        return [{
            'id': i.uuid,
            'name': i.calendar.name,
            'allow': ALLOW if i.allow  else DENY,
            'priority': i.priority,
        } for i in parent.calendaraccess_set.all()]

    def getTitle(self, parent):
        return _('Access restrictions by calendar')

    def getFields(self, parent):
        return [
            {'priority': {'title': _('Priority'), 'type': 'numeric', 'width': '6em'}},
            {'name': {'title': _('Name')}},
            {'allow': {'title': _('Rule')}},
        ]

    def saveItem(self, parent, item):
        # If already exists
        uuid = self._params['id']
        calendar = Calendar.objects.get(uuid=processUuid(self._params['calendarId']))
        allow = self._params['allow'].upper() == ALLOW
        priority = int(self._params['priority'])

        try:
            calAccess = CalendarAccess.objects.get(uuid=uuid)
            calAccess.calendar = calendar
            calAccess.servicePool = parent
            calAccess.allow = allow
            calAccess.priority = priority
            calAccess.save()
        except CalendarAccess.DoesNotExist:
            CalendarAccess.objects.create(uuid=uuid, calendar=calendar, servicePool=parent, allow=allow, priority=priority)

        return self.success()

    def deleteItem(self, parent, item):
        Calendar.objects.get(uuid=processUuid(self._args[0])).delete()

