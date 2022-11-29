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
#    * Neither the name of Virtual Cable S.L.U. nor the names of its contributors
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
import typing
import logging


from ...utils.test import UDSTestCase

from uds.core.util import net

logger = logging.getLogger(__name__)


class NetTest(UDSTestCase):
    def testNetworkFromStringIPv4(self):
        for n in (
            ('*', 0, 4294967295),
            ('192.168.0.1', 3232235521, 3232235521),
            ('192.168.0.*', 3232235520, 3232235775),
            ('192.168.*.*', 3232235520, 3232301055),
            ('192.168.*', 3232235520, 3232301055),
            ('192.*.*.*', 3221225472, 3238002687),
            ('192.*.*', 3221225472, 3238002687),
            ('192.*', 3221225472, 3238002687),
            ('192.168.0.1 netmask 255.255.255.0', 3232235520, 3232235775),
            ('192.168.0.1/8', 3221225472, 3238002687),
            ('192.168.0.1/28', 3232235520, 3232235535),
            ('192.168.0.1-192.168.0.87', 3232235521, 3232235607),
            ('192.168.0.1 netmask 255.255.255.0', 3232235520, 3232235775),
        ):
            try:
                multiple_net: typing.List[net.NetworkType] = net.networksFromString(
                    n[0]
                )
                self.assertEqual(
                    len(multiple_net),
                    1,
                    'Incorrect number of network returned from {0}'.format(n[0]),
                )
                self.assertEqual(
                    multiple_net[0][0],
                    n[1],
                    'Incorrect network start value for {0}'.format(n[0]),
                )
                self.assertEqual(
                    multiple_net[0][1],
                    n[2],
                    'Incorrect network end value for {0}'.format(n[0]),
                )

                single_net: net.NetworkType = net.networkFromString(n[0])
                self.assertEqual(
                    len(single_net),
                    3,
                    'Incorrect number of network returned from {0}'.format(n[0]),
                )
                self.assertEqual(
                    single_net[0],
                    n[1],
                    'Incorrect network start value for {0}'.format(n[0]),
                )
                self.assertEqual(
                    single_net[1],
                    n[2],
                    'Incorrect network end value for {0}'.format(n[0]),
                )
            except Exception as e:
                logger.exception('Running test')
                raise Exception('Value Error: {}. Input string: {}'.format(e, n[0]))

        for n in ('192.168.0', '192.168.0.5-192.168.0.3', 'no net'):
            with self.assertRaises(ValueError):
                net.networksFromString(n)

        self.assertEqual(net.ipToLong('192.168.0.5').ip, 3232235525)
        self.assertEqual(net.longToIp(3232235525, 4), '192.168.0.5')
        for n in range(0, 255):
            self.assertTrue(net.ipInNetwork('192.168.0.{}'.format(n), '192.168.0.0/24'))

        for n in range(4294):
            self.assertTrue(
                net.ipInNetwork(n * 1000, [net.NetworkType(0, 4294967295, 4)])
            )
            self.assertTrue(
                net.ipInNetwork(n * 1000, net.NetworkType(0, 4294967295, 4))
            )

    def testNetworkFromStringIPv6(self):
        # IPv6 only support standard notation, and '*', but not "netmask" or "range"
        for n in (
            (
                '*',
                0,
                2**128 - 1,
            ),  # This could be confused with ipv4 *, so we take care
            (
                '2001:db8::1',
                42540766411282592856903984951653826561,
                42540766411282592856903984951653826561,
            ),
            (
                '2001:db8::1/64',
                42540766411282592856903984951653826560,
                42540766411282592875350729025363378175,
            ),
            (
                '2001:db8::1/28',
                42540765777457292742789284203302223872,
                42540767045107892971018685700005429247,
            ),
            (
                '2222:3333:4444:5555:6666:7777:8888:9999/64',
                45371328414530988873481865147602436096,
                45371328414530988891928609221311987711,
            ),
            (
                'fe80::/10',
                33828852492726108965401889684134769408,
                33828852492726108965401889684134769408 + 2**118 - 1,
            ),
        ):
            try:
                multiple_net: typing.List[net.NetworkType] = net.networksFromString(
                    n[0], version=(6 if n[0] == '*' else 0)
                )
                self.assertEqual(
                    len(multiple_net),
                    1,
                    'Incorrect number of network returned from {0}'.format(n[0]),
                )
                self.assertEqual(
                    multiple_net[0][0],
                    n[1],
                    'Incorrect network start value for {0}'.format(n[0]),
                )
                self.assertEqual(
                    multiple_net[0][1],
                    n[2],
                    'Incorrect network end value for {0}'.format(n[0]),
                )

                single_net: net.NetworkType = net.networkFromString(
                    n[0], version=(6 if n[0] == '*' else 0)
                )
                self.assertEqual(
                    len(single_net),
                    3,
                    'Incorrect number of network returned from {0}'.format(n[0]),
                )
                self.assertEqual(
                    single_net[0],
                    n[1],
                    'Incorrect network start value for {0}'.format(n[0]),
                )
                self.assertEqual(
                    single_net[1],
                    n[2],
                    'Incorrect network end value for {0}'.format(n[0]),
                )
            except Exception as e:
                logger.exception('Running test')
                raise Exception('Value Error: {}. Input string: {}'.format(e, n[0]))
