# -*- coding: utf-8 -*-

#
# Copyright (c) 2015 Virtual Cable S.L.
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
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
'''
from __future__ import unicode_literals

from django.utils.translation import ugettext, ugettext_noop as _

from uds.core.ui.UserInterface import UserInterface

import logging

logger = logging.getLogger(__name__)

__updated__ = '2015-04-28'


class Report(UserInterface):
    mime_type = 'application/pdf'  # Report returns pdfs by default, but could be anything else
    name = _('Base Report')  # Report name
    description = _('Base report')  # Report description
    group = ''  # So we can "group" reports by kind?
    uuid = None

    @classmethod
    def translated_name(cls):
        '''
        Helper to return translated report name
        '''
        return ugettext(cls.name)

    @classmethod
    def translated_description(cls):
        '''
        Helper to return translated report description
        '''
        return ugettext(cls.description)

    @classmethod
    def translated_group(cls):
        '''
        Helper to return translated report description
        '''
        return ugettext(cls.group)

    @classmethod
    def getUuid(cls):
        if cls.uuid is None:
            raise Exception('Class does not includes an uuid!!!: {}'.format(cls))
        return cls.uuid

    def __init__(self, values=None):
        '''
        Do not forget to invoke this in your derived class using
        "super(self.__class__, self).__init__(values)".

        The values parameter is passed directly to UserInterface base.

        Values are passed to __initialize__ method. It this is not None,
        the values contains a dictionary of values received from administration gui,
        that contains the form data requested from user.

        If you override marshal, unmarshal and inherited UserInterface method
        valuesDict, you must also take account of values (dict) provided at the
        __init__ method of your class.
        '''
        #
        UserInterface.__init__(self, values)
        self.initialize()

    def initialize(self):
        pass

    def genReport(self):
        return ''

    def __str__(self):
        return "Base Report"
