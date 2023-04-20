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
import logging.handlers
import typing
import enum

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from django.db.models import Model

logger = logging.getLogger(__name__)
useLogger = logging.getLogger('useLog')

class LogLevel(enum.IntEnum):
    OTHER = 10000
    DEBUG = 20000
    INFO = 30000
    WARNING = 40000
    # Alias WARN
    WARN = 40000
    ERROR = 50000
    CRITICAL = 60000
    # Alias FATAL
    FATAL = 60000

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    @classmethod
    def fromStr(cls: typing.Type['LogLevel'], level: str) -> 'LogLevel':
        try:
            return cls[level.upper()]
        except KeyError:
            return cls.OTHER

    @classmethod
    def fromInt(cls: typing.Type['LogLevel'], level: int) -> 'LogLevel':
        try:
            return cls(level)
        except ValueError:
            return cls.OTHER

class LogSource(enum.StrEnum):
    INTERNAL = 'internal'
    ACTOR = 'actor'
    TRANSPORT = 'transport'
    OSMANAGER = 'osmanager'
    UNKNOWN = 'unknown'
    WEB = 'web'
    ADMIN = 'admin'
    SERVICE = 'service'
    REST = 'rest'

def useLog(
    type_: str,
    serviceUniqueId: str,
    serviceIp: str,
    username: str,
    srcIP: typing.Optional[str] = None,
    srcUser: typing.Optional[str] = None,
    userServiceName: typing.Optional[str] = None,
    poolName: typing.Optional[str] = None,
) -> None:
    """
    Logs an "use service" event (logged from actors)
    :param type_: Type of event (commonly 'login' or 'logout')
    :param serviceUniqueId: Unique id of service
    :param serviceIp: IP Of the service
    :param username: Username notified from service (internal "user service" user name
    :param srcIP: IP of user holding that service at time of event
    :param srcUser: Username holding that service at time of event
    """
    srcIP = 'unknown' if srcIP is None else srcIP
    srcUser = 'unknown' if srcUser is None else srcUser
    userServiceName = 'unknown' if userServiceName is None else userServiceName
    poolName = 'unknown' if poolName is None else poolName

    useLogger.info(
        '|'.join(
            [
                type_,
                serviceUniqueId,
                serviceIp,
                srcIP,
                srcUser,
                username,
                userServiceName,
                poolName,
            ]
        )
    )


def doLog(
    wichObject: typing.Optional['Model'],
    level: LogLevel,
    message: str,
    source: LogSource = LogSource.UNKNOWN,
    avoidDuplicates: bool = True,
) -> None:
    # pylint: disable=import-outside-toplevel
    from uds.core.managers.log import LogManager

    logger.debug('%s %s %s', wichObject, level, message)
    LogManager().doLog(wichObject, level, message, source, avoidDuplicates)


def getLogs(
    wichObject: typing.Optional['Model'], limit: int = -1
) -> typing.List[typing.Dict]:
    """
    Get the logs associated with "wichObject", limiting to "limit" (default is GlobalConfig.MAX_LOGS_PER_ELEMENT)
    """
    # pylint: disable=import-outside-toplevel
    from uds.core.managers.log import LogManager

    return LogManager().getLogs(wichObject, limit)


def clearLogs(wichObject: typing.Optional['Model']) -> None:
    """
    Clears the logs associated with the object using the logManager
    """
    # pylint: disable=import-outside-toplevel
    from uds.core.managers.log import LogManager

    return LogManager().clearLogs(wichObject)


class UDSLogHandler(logging.handlers.RotatingFileHandler):
    """
    Custom log handler that will log to database before calling to RotatingFileHandler
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Currently, simply call to parent
        msg = self.format(record)  # pylint: disable=unused-variable

        # TODO: Log message on database and continue as a RotatingFileHandler
        return super().emit(record)
