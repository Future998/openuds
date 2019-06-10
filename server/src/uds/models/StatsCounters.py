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
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
import typing
import logging
from collections.abc import Iterable

from django.db import models

from uds.models.Util import NEVER_UNIX
from uds.models.Util import getSqlDatetime
from uds.models.Util import getSqlFnc


logger = logging.getLogger(__name__)


class StatsCounters(models.Model):
    """
    Counter statistocs mpdes the counter statistics
    """

    owner_id = models.IntegerField(db_index=True, default=0)
    owner_type = models.SmallIntegerField(db_index=True, default=0)
    counter_type = models.SmallIntegerField(db_index=True, default=0)
    stamp = models.IntegerField(db_index=True, default=0)
    value = models.IntegerField(db_index=True, default=0)

    class Meta:
        """
        Meta class to declare db table
        """
        db_table = 'uds_stats_c'
        app_label = 'uds'

    @staticmethod
    def get_grouped(owner_type: typing.Union[str, typing.Iterable[str]], counter_type: str, **kwargs):  # pylint: disable=too-many-locals
        """
        Returns the average stats grouped by interval for owner_type and owner_id (optional)

        Note: if someone cant get this more optimized, please, contribute it!
        """

        filt = 'owner_type'
        if isinstance(owner_type, Iterable):
            filt += ' in (' + ','.join((str(x) for x in owner_type)) + ')'
        else:
            filt += '=' + str(owner_type)

        owner_id = kwargs.get('owner_id', None)
        if owner_id is not None:
            filt += ' AND OWNER_ID'
            if isinstance(owner_id, Iterable):
                filt += ' in (' + ','.join(str(x) for x in owner_id) + ')'
            else:
                filt += '=' + str(owner_id)

        filt += ' AND counter_type=' + str(counter_type)

        since = kwargs.get('since', None)
        to = kwargs.get('to', None)

        since = int(since) if since else NEVER_UNIX
        to = int(to) if to else getSqlDatetime(True)

        interval = 600  # By default, group items in ten minutes interval (600 seconds)

        elements = kwargs.get('limit', None)

        if elements:
            # Protect against division by "elements-1" a few lines below
            elements = int(elements) if int(elements) > 1 else 2

            if owner_id is None:
                q = StatsCounters.objects.filter(stamp__gte=since, stamp__lte=to)
            else:
                if isinstance(owner_id, Iterable):
                    q = StatsCounters.objects.filter(owner_id__in=owner_id, stamp__gte=since, stamp__lte=to)
                else:
                    q = StatsCounters.objects.filter(owner_id=owner_id, stamp__gte=since, stamp__lte=to)

            if isinstance(owner_type, Iterable):
                q = q.filter(owner_type__in=owner_type)
            else:
                q = q.filter(owner_type=owner_type)

            if q.count() > elements:
                first = q.order_by('stamp')[0].stamp
                last = q.order_by('stamp').reverse()[0].stamp
                interval = int((last - first) / (elements - 1))

        stampValue = '{ceil}(stamp/{interval})'.format(ceil=getSqlFnc('CEIL'), interval=interval)
        filt += ' AND stamp>={0} AND stamp<={1} GROUP BY {2} ORDER BY stamp'.format(since, to, stampValue)

        fnc = getSqlFnc('MAX' if kwargs.get('use_max', False) else 'AVG')

        query = (
            'SELECT -1 as id,-1 as owner_id,-1 as owner_type,-1 as counter_type, ' + stampValue + '*{}'.format(interval) + ' AS stamp,' +
            getSqlFnc('CEIL') + '({0}(value)) AS value '
            'FROM {1} WHERE {2}'
        ).format(fnc, StatsCounters._meta.db_table, filt)

        logger.debug('Stats query: %s', query)

        # We use result as an iterator
        return StatsCounters.objects.raw(query)

    def __str__(self):
        return u"Counter of {}({}): {} - {} - {}".format(self.owner_type, self.owner_id, self.stamp, self.counter_type, self.value)
