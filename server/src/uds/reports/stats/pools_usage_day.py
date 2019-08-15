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

"""
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
from django.utils.translation import ugettext, ugettext_lazy as _

from uds.core.ui import gui
from uds.core.util.stats import counters

import csv
import io
import datetime
import logging

from .base import StatsReport

from uds.models import ServicePool
from uds.core.reports import graphs

logger = logging.getLogger(__name__)

__updated__ = '2018-04-25'

# several constants as Width height, margins, ..
WIDTH, HEIGHT, DPI = 19.2, 10.8, 100
SIZE = (WIDTH, HEIGHT, DPI)


class CountersPoolAssigned(StatsReport):
    filename = 'pools_counters.pdf'
    name = _('Pools usage on a day')  # Report name
    description = _('Pools usage counters for an specific day')  # Report description
    uuid = '0b429f70-2fc6-11e7-9a2a-8fc37101e66a'

    startDate = gui.DateField(
        order=2,
        label=_('Date'),
        tooltip=_('Date for report'),
        defvalue='',
        required=True
    )

    pools = gui.MultiChoiceField(
        order=1,
        label=_('Pools'),
        tooltip=_('Pools for report'),
        required=True
    )

    def initialize(self, values):
        pass

    def initGui(self):
        logger.debug('Initializing gui')
        vals = [
            gui.choiceItem(v.uuid, v.name) for v in ServicePool.objects.all().order_by('name')
        ]
        self.pools.setValues(vals)

    def getData(self):
        # Generate the sampling intervals and get dataUsers from db
        start = self.startDate.date()
        end = self.startDate.date() + datetime.timedelta(days=1)

        data = []

        pool = None
        for poolUuid in self.pools.value:
            try:
                pool = ServicePool.objects.get(uuid=poolUuid)
            except Exception:
                pass  # Ignore pool

            hours = {}
            for i in range(24):
                hours[i] = i * i

            for x in counters.getCounters(pool, counters.CT_ASSIGNED, since=start, to=end, limit=24, use_max=True, all=False):
                hour = x[0].hour
                val = int(x[1])
                if hours[hour] < val:
                    hours[hour] = val

            data.append({'uuid':pool.uuid, 'name': pool.name, 'hours': hours})

        logger.debug('data: {}'.format(data))

        return data

    def generate(self):
        items = self.getData()

        graph1 = io.BytesIO()

        X = list(range(24))
        d = {
            'title': _('Services by hour'),
            'x': X,
            'xtickFnc': lambda l: '{:02d}'.format(l),
            'xlabel': _('Hour'),
            'y': [
                {
                    'label': i['name'],
                    'data': [i['hours'][v] for v in X]
                } for i in items
            ],
            'ylabel': 'Services'
        }

        graphs.barChart(SIZE, d, graph1)

        return self.templateAsPDF(
            'uds/reports/stats/pools-usage-day.html',
            dct={
                'data': items,
                'pools': [v.name for v in ServicePool.objects.filter(uuid__in=self.pools.value)],
                'beginning': self.startDate.date(),
            },
            header=ugettext('Services usage report for a day'),
            water=ugettext('Service usage report'),
            images={'graph1': graph1.getvalue()},
        )


class CountersPoolAssignedCSV(CountersPoolAssigned):
    filename = 'pools_counters.csv'
    mime_type = 'text/csv'  # Report returns pdfs by default, but could be anything else
    uuid = '1491148a-2fc6-11e7-a5ad-03d9a417561c'
    encoded = False

    # Input fields
    startDate = CountersPoolAssigned.startDate
    pools = CountersPoolAssigned.pools

    def generate(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([ugettext('Pool'), ugettext('Hour'), ugettext('Services')])

        items = self.getData()

        for i in items:
            for j in range(24):
                writer.writerow([i['name'], '{:02d}'.format(j), i['hours'][j]])

        return output.getvalue()
