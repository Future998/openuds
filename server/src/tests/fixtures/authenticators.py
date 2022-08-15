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

from uds import models
from uds.core.util import states
from uds.core.managers.crypto import CryptoManager

# Counters so we can reinvoke the same method and generate new data
glob = {
    'user_id': 0,
    'group_id': 0
}

def createAuthenticator(
    authenticator: typing.Optional[models.Authenticator] = None,
) -> models.Authenticator:
    """
    Creates a testing authenticator
    """
    if authenticator is None:
        from uds.auths.InternalDB.authenticator import InternalDBAuth

        authenticator = models.Authenticator()
        authenticator.name = 'Testing authenticator'
        authenticator.comments = 'Tesging authenticator'
        authenticator.data_type = InternalDBAuth.typeType
        authenticator.data = authenticator.getInstance().serialize()
        authenticator.save()

    return authenticator


def createUsers(
    authenticator: models.Authenticator,
    number_of_users: int = 1,
    is_staff: bool = False,
    is_admin: bool = False,
    enabled: bool = True,
) -> typing.List[models.User]:
    """
    Creates some ramdon users
    password is same as username
    """
    users = [
        authenticator.users.create(
            name='user{}'.format(i),
            password=CryptoManager().hash('user{}'.format(i)),
            real_name='Real name {}'.format(i),
            comments='User {}'.format(i),
            staff_member=is_staff or is_admin,
            is_admin=is_admin,
            state=states.common.ACTIVE if enabled else states.common.BLOCKED,
        )
        for i in range(glob['user_id'], glob['user_id'] + number_of_users)
    ]
    glob['user_id'] += number_of_users

    return users


def createGroups(
    authenticator: models.Authenticator, number_of_groups: int = 1
) -> typing.List[models.Group]:
    """
    Creates a testing authenticator
    """
    groups = [
        authenticator.groups.create(
            name='Group {}'.format(i),
            comments='Group {}'.format(i),
            is_meta=False,
        )
        for i in range(glob['group_id'], glob['group_id'] + number_of_groups)
    ]

    glob['group_id'] += number_of_groups

    return groups


def createMetaGroups(
    authenticator: models.Authenticator, number_of_meta: int = 1
) -> typing.List[models.Group]:
    """
    Creates a testing authenticator
    """
    meta_groups = [
        authenticator.groups.create(
            name='Meta group {}'.format(i),
            comments='Meta group {}'.format(i),
            is_meta=True,
            meta_if_any=i % 2 == 0,
        )
        for i in range(glob['group_id'], glob['group_id'] + number_of_meta)
    ]

    glob['group_id'] += number_of_meta

    return meta_groups
