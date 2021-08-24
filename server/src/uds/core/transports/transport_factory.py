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
import logging
import typing

if typing.TYPE_CHECKING:
    from .transport import Transport


logger = logging.getLogger(__name__)


class TransportsFactory:
    _factory: typing.Optional['TransportsFactory'] = None
    _transports: typing.Dict[str, typing.Type['Transport']]

    def __init__(self):
        self._transports = {}

    @staticmethod
    def factory() -> 'TransportsFactory':
        if TransportsFactory._factory is None:
            TransportsFactory._factory = TransportsFactory()
        return TransportsFactory._factory

    def providers(self) -> typing.Dict[str, typing.Type['Transport']]:
        return self._transports

    def insert(self, type_: typing.Type['Transport']) -> None:
        logger.debug('Adding transport %s as %s', type_.type(), type_)
        typeName = type_.type().lower()
        self._transports[typeName] = type_

    def lookup(self, typeName: str) -> typing.Optional[typing.Type['Transport']]:
        return self._transports.get(typeName.lower(), None)
