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
import datetime
import typing

from uds import models
from uds.core import environment
from uds.core.util import states

from ..utils import generators

# Counters so we can reinvoke the same method and generate new data
glob = {
    'provider_id': 1,
    'service_id': 1,
    'osmanager_id': 1,
    'transport_id': 1,
    'service_pool_id': 1,
    'user_service_id': 1,
}


def createProvider() -> models.Provider:
    from uds.services.Test.provider import TestProvider

    provider = models.Provider()
    provider.name = 'Testing provider {}'.format(glob['provider_id'])
    provider.comments = 'Tesging provider comment {}'.format(glob['provider_id'])
    provider.data_type = TestProvider.typeType
    provider.data = provider.getInstance().serialize()
    provider.save()
    glob['provider_id'] += 1

    return provider


def createSingleTestingUserServiceStructure(
    provider: 'models.Provider',
    user: 'models.User',
    groups: typing.List['models.Group'],
    type_: typing.Union[typing.Literal['managed'], typing.Literal['unmanaged']],
) -> 'models.UserService':

    from uds.services.Test.service import ServiceTestCache, ServiceTestNoCache
    from uds.osmanagers.Test import TestOSManager
    from uds.transports.Test import TestTransport

    service: 'models.Service' = provider.services.create(
        name='Service {}'.format(glob['service_id']),
        data_type=ServiceTestCache.typeType,
        data=ServiceTestCache(
            environment.Environment(str(glob['service_id'])), provider.getInstance()
        ).serialize(),
        token=generators.random_string(16) + str(glob['service_id']),
    )
    glob['service_id'] += 1  # In case we generate a some more services elsewhere

    """
    Creates several testing OS Managers
    """

    values: typing.Dict[str, typing.Any] = {
        'onLogout': 'remove',
        'idle': 300,
    }
    osmanager: typing.Optional['models.OSManager'] = None
    if type_ == 'managed':
        osmanager = models.OSManager.objects.create(
            name='OS Manager %d' % (glob['osmanager_id']),
            comments='Comment for OS Manager %d' % (glob['osmanager_id']),
            data_type=TestOSManager.typeType,
            data=TestOSManager(
                environment.Environment(str(glob['osmanager_id'])), values
            ).serialize(),
        )
        glob['osmanager_id'] += 1

    service_pool: 'models.ServicePool' = service.deployedServices.create(
        name='Service pool %d' % (glob['service_pool_id']),
        short_name='pool%d' % (glob['service_pool_id']),
        comments='Comment for service pool %d' % (glob['service_pool_id']),
        osmanager=osmanager,
    )

    publication: 'models.ServicePoolPublication' = service_pool.publications.create(
        publish_date=datetime.datetime.now(),
        state=states.publication.USABLE,
        state_date=datetime.datetime.now(),
        # Rest of fields are left as default
    )
    glob['service_pool_id'] += 1

    values = {
        'testURL': 'http://www.udsenterprise.com',
        'forceNewWindow': True,
    }
    transport: 'models.Transport' = models.Transport.objects.create(
        name='Transport %d' % (glob['transport_id']),
        comments='Comment for Trnasport %d' % (glob['transport_id']),
        data_type=TestTransport.typeType,
        data=TestTransport(
            environment.Environment(str(glob['transport_id'])), values
        ).serialize(),
    )
    glob['transport_id'] += 1

    service_pool.publications.add(publication)
    for g in groups:
        service_pool.assignedGroups.add(g)
    service_pool.transports.add(transport)

    service_pool.transports.add(transport)

    user_service: 'models.UserService' = service_pool.userServices.create(
        friendly_name='user-service-{}'.format(glob['user_service_id']),
        publication=publication,
        unique_id=generators.random_mac(),
        state=states.userService.USABLE,
        os_state=states.userService.USABLE,
        state_date=datetime.datetime.now(),
        creation_date=datetime.datetime.now() - datetime.timedelta(minutes=30),
        user=user,
        src_hostname=generators.random_string(32),
        src_ip=generators.random_ip(),
    )

    return user_service
