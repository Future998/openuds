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
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''
import re
import logging

logger = logging.getLogger(__name__)

Linux = 'Linux'
Windows = 'Windows'
Macintosh = 'Macintosh'
Android = 'Android'
iPad = 'iPad'
iPhone = 'iPhone'

knownOss = [ Android, Linux, Windows, Macintosh, iPad, iPhone  ] # Android is linux also, so it is cheched on first place
    
allOss = list(knownOss)
desktopOss = [Linux, Windows, Macintosh]
mobilesODD = list(set(allOss)-set(desktopOss))
    
def getOsFromUA(ua):
    '''
    Basic OS Client detector (very basic indeed :-))
    '''
    res = {'OS' : 'Unknown', 'Version' : 'unused' }
    for os in knownOss:
        try:
            ua.index(os)
            res['OS'] = os
            break
        except Exception:
            pass
    logger.debug('User-Agent: {0}'.format(ua))
    logger.debug('Detected OS: {0}'.format(res))
    return res
    