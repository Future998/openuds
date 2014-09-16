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
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
'''

from __future__ import unicode_literals

__updated__ = '2014-09-16'

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.db import IntegrityError
from django.db.models import signals

from uds.core.Environment import Environment
from uds.core.util.model import generateUuid

import logging

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class OSManager(models.Model):
    '''
    An OS Manager represents a manager for responding requests for agents inside services.
    '''
    # pylint: disable=model-missing-unicode
    uuid = models.CharField(max_length=50, default=None, null=True, unique=True)
    name = models.CharField(max_length=128, unique=True)
    data_type = models.CharField(max_length=128)
    data = models.TextField(default='')
    comments = models.CharField(max_length=256)

    class Meta:
        '''
        Meta class to declare default order
        '''
        ordering = ('name',)
        app_label = 'uds'

    # Override default save to add uuid
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.uuid is None:
            self.uuid = generateUuid()
        return models.Model.save(self, force_insert=force_insert,
                                 force_update=force_update, using=using,
                                 update_fields=update_fields)

    def getEnvironment(self):
        '''
        Returns an environment valid for the record this object represents
        '''
        return Environment.getEnvForTableElement(self._meta.verbose_name, self.id)

    def getInstance(self, values=None):
        '''
        Instantiates the object this record contains.

        Every single record of Provider model, represents an object.

        Args:
           values (list): Values to pass to constructor. If no values are especified,
                          the object is instantiated empty and them de-serialized from stored data.

        Returns:
            The instance Instance of the class this provider represents

        Raises:
        '''
        osType = self.getType()
        env = self.getEnvironment()
        os = osType(env, values)
        # Only unserializes if this is not initialized via user interface and
        # data contains something
        if values == None and self.data != None and self.data != '':
            os.unserialize(self.data)
        return os

    def getType(self):
        '''
        Get the type of the object this record represents.

        The type is Python type, it obtains this type from ServiceProviderFactory and associated record field.

        Returns:
            The python type for this record object

        :note: We only need to get info from this, not access specific data (class specific info)
        '''
        # We only need to get info from this, not access specific data (class specific info)
        from uds.core import osmanagers
        return osmanagers.factory().lookup(self.data_type)

    def isOfType(self, type_):
        return self.data_type == type_

    def remove(self):
        '''
        Removes this OS Manager only if there is no associated deployed service using it.

        Returns:
            True if the object has been removed

            False if the object can't be removed because it is being used by some DeployedService

        Raises:
        '''
        if self.deployedServices.all().count() > 0:
            return False
        self.delete()
        return True

    def __str__(self):
        return u"{0} of type {1} (id:{2})".format(self.name, self.data_type, self.id)

    @staticmethod
    def beforeDelete(sender, **kwargs):
        '''
        Used to invoke the Service class "Destroy" before deleting it from database.

        The main purpuse of this hook is to call the "destroy" method of the object to delete and
        to clear related data of the object (environment data such as own storage, cache, etc...

        :note: If destroy raises an exception, the deletion is not taken.
        '''
        toDelete = kwargs['instance']
        if toDelete.deployedServices.count() > 0:
            raise IntegrityError('Can\'t remove os managers with assigned deployed services')
        # Only tries to get instance if data is not empty
        if toDelete.data != '':
            s = toDelete.getInstance()
            s.destroy()
            s.env().clearRelatedData()

        logger.debug('Before delete os manager {}'.format(toDelete))

# : Connects a pre deletion signal to OS Manager
signals.pre_delete.connect(OSManager.beforeDelete, sender=OSManager)
