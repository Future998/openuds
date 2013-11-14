# -*- coding: utf-8 -*-

#
# Copyright (c) 2014 Virtual Cable S.L.
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
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''
from __future__ import unicode_literals

from django.utils.translation import ugettext as _

import logging

logger = logging.getLogger(__name__)

class ModelHandlerMixin(object):
    '''
    Basic Handler for a model
    Basically we will need same operations for all models, so we can
    take advantage of this fact to not repeat same code again and again... 
    '''
    authenticated = True
    needs_staff = True
    
    model = None
    
    def item_as_dict(self, item):
        pass
    
    def getItems(self, *args, **kwargs):
        for item in self.model.objects.filter(*args, **kwargs):
            yield self.item_as_dict(item)
        
    def get(self):
        logger.debug('methot GET for {0}'.format(self.__class__.__name__))
        if len(self._args) == 0:
            return list(self.getItems())
        try:
            return list(self.getItems(pk=self._args[0]))[0]
        except:
            return {'error': 'not found' }
        
class ModelTypeHandlerMixin(object):
    '''
    As With models, a lot of UDS model contains info about its class.
    We take advantage of this for not repeating same code (as with ModelHandlerMixin)
    '''
    authenticated = True
    needs_staff = True
    model = None
    
    def enum_types(self):
        pass
    
    def type_as_dict(self, type_):
        return { 'name' : _(type_.name()), 
                 'type' : type_.type(), 
                 'description' : _(type_.description()), 
                 'icon' : type_.icon().replace('\n', '') 
        }
            
    def getTypes(self, *args, **kwargs):
        for type_ in self.enum_types():
            yield self.type_as_dict(type_)
            
    def get(self):
        return list(self.getTypes())
    
class ModelTableHandlerMixin(object):
    authenticated = True
    needs_staff = True
    
    # Fields should have id of the field, type and length 
    # All options can be ommited
    # Sample fields:
    #    fields = [
    #        { 'name': {'title': _('Name')} },
    #        { 'comments': {'title':  _('Comments')}},
    #        { 'services_count': {'title': _('Services'), 'type': 'numeric', 'width': '5em'}}
    #]

    fields = []
    title = ''
    
    def get(self):
        # Convert to unicode fields (ugettext_lazy needs to be rendered before passing it to Json
        fields = [ { 'id' : {'visible': False } } ] # Always add id column as invisible 
        for f in self.fields:
            for k1, v1 in f.iteritems():
                dct = {}
                for k2, v2 in v1.iteritems():
                    if type(v2) in (bool, int, long, float, unicode):
                        dct[k2] = v2
                    else:
                        dct[k2] = unicode(v2)
                fields.append({k1: dct})
        return { 'title': unicode(self.title),  'fields': fields };
    
