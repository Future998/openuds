# -*- coding: utf-8 -*-

# Model based on https://github.com/llazzaro/django-scheduler
#
# Copyright (c) 2016-2020 Virtual Cable S.L.U.
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
import codecs
import logging

from django.db import models

from .uuid_model import UUIDModel

logger = logging.getLogger(__name__)


class DBFile(UUIDModel):

    # Not indexed, used for cleanups only
    owner = models.CharField(max_length=32, default='')
    name = models.CharField(max_length=255, primary_key=True)
    content = models.TextField(blank=True)
    size = models.IntegerField(default=0)
    created = models.DateTimeField()
    modified = models.DateTimeField()

    # "fake" declarations for type checking
    objects: 'models.manager.Manager[DBFile]'

    @property
    def data(self) -> bytes:
        try:
            return codecs.decode(codecs.decode(self.content.encode(), 'base64'), 'zip')
        except Exception:
            logger.error('DBFile %s has errors and cannot be used', self.name)
            try:
                self.delete()  # Autodelete, invalid...
            except Exception:
                logger.error('Could not even delete %s!!', self.name)

            return b''

    @data.setter
    def data(self, value: bytes):
        self.size = len(value)
        self.content = codecs.encode(codecs.encode(value, 'zip'), 'base64').decode()

    def __str__(self) -> str:
        return 'File: {} {} {} {}'.format(
            self.name, self.size, self.created, self.modified
        )
