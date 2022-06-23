# -*- coding: utf-8 -*-
#
# Copyright (c) 2018-2019 Virtual Cable S.L.
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
@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import time
import logging
import typing

from django.middleware import csrf
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse

from uds.core.util.request import ExtendedHttpRequest, ExtendedHttpRequestWithUser
from django.views.decorators.cache import never_cache

from uds.core.auths import auth, exceptions
from uds.web.util import errors
from uds.web.forms.LoginForm import LoginForm
from uds.web.forms.MFAForm import MFAForm
from uds.web.util.authentication import checkLogin
from uds.web.util.services import getServicesData
from uds.web.util import configjs

logger = logging.getLogger(__name__)

CSRF_FIELD = 'csrfmiddlewaretoken'

if typing.TYPE_CHECKING:
    from uds import models


@never_cache
def index(request: HttpRequest) -> HttpResponse:
    # Gets csrf token
    csrf_token = csrf.get_token(request)
    if csrf_token is not None:
        csrf_token = str(csrf_token)

    response = render(request, 'uds/modern/index.html', {'csrf_field': CSRF_FIELD, 'csrf_token': csrf_token})

    # Ensure UDS cookie is present
    auth.getUDSCookie(request, response)

    return response


# Includes a request.session ticket, indicating that
def ticketLauncher(request: HttpRequest) -> HttpResponse:
    request.session['restricted'] = True  # Access is from ticket
    return index(request)


# Basically, the original /login method, but fixed for modern interface
def login(
    request: ExtendedHttpRequest, tag: typing.Optional[str] = None
) -> HttpResponse:
    # Default empty form
    logger.debug('Tag: %s', tag)
    
    if request.method == 'POST':
        request.session['restricted'] = False  # Access is from login
        request.authorized = False  # Ensure that on login page, user is unauthorized first

        form = LoginForm(request.POST, tag=tag)
        user, data = checkLogin(request, form, tag)
        if isinstance(user, str):
            return HttpResponseRedirect(user)

        if user:
            # Initial redirect page
            response = HttpResponseRedirect(reverse('page.index'))
            # save tag, weblogin will clear session
            tag = request.session.get('tag')
            auth.webLogin(request, response, user, data)  # data is user password here
            # And restore tag
            request.session['tag'] = tag

            # If MFA is provided, we need to redirect to MFA page
            request.authorized = True
            if user.manager.getType().providesMfa() and user.manager.mfa:
                authInstance = user.manager.getInstance()
                if authInstance.mfaIdentifier():
                    request.authorized = False   # We can ask for MFA so first disauthorize user
                    response = HttpResponseRedirect(
                        reverse('page.mfa')
                    )

        else:
            # If error is numeric, redirect...
            # Error, set error on session for process for js
            time.sleep(2)  # On failure, wait a bit...
            if isinstance(data, int):
                return errors.errorView(request, data)

            request.session['errors'] = [data]
            return index(request)
    else:
        request.session['tag'] = tag
        response = index(request)

    return response


@auth.webLoginRequired(admin=False)
def logout(request: ExtendedHttpRequestWithUser) -> HttpResponse:
    auth.authLogLogout(request)
    request.session['restricted'] = False  # Remove restricted
    try:
        logoutUrl = request.user.logout()
        if logoutUrl is None:
            logoutUrl = request.session.get('logouturl', None)
        return auth.webLogout(request, logoutUrl)
    except exceptions.Redirect as e:
        return HttpResponseRedirect(
            request.build_absolute_uri(str(e)) if e.args and e.args[0] else '/'
        )
    except Exception as e:
        logger.exception('Error logging out user')
        return auth.webLogout(request, None)


def js(request: ExtendedHttpRequest) -> HttpResponse:
    return HttpResponse(
        content=configjs.udsJs(request), content_type='application/javascript'
    )


@auth.denyNonAuthenticated
def servicesData(request: ExtendedHttpRequestWithUser) -> HttpResponse:
    return JsonResponse(getServicesData(request))

# The MFA page does not needs CRF token, so we disable it
@csrf_exempt
def mfa(request: ExtendedHttpRequest) -> HttpResponse:
    if not request.user:
        return HttpResponseRedirect(reverse('page.index'))  # No user, no MFA

    mfaProvider: 'models.MFA' = request.user.manager.mfa
    if not mfaProvider:
        return HttpResponseRedirect(reverse('page.index'))

    # Obtain MFA data
    authInstance = request.user.manager.getInstance()
    mfaInstance = mfaProvider.getInstance()

    mfaIdentifier = authInstance.mfaIdentifier()
    label = mfaInstance.label()

    if request.method == 'POST':  # User has provided MFA code
        form = MFAForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                mfaInstance.validate(str(request.user.pk), mfaIdentifier, code)
                request.authorized = True
                return HttpResponseRedirect(reverse('page.index'))
            except exceptions.MFAError as e:
                logger.error('MFA error: %s', e)
                return errors.errorView(request, errors.INVALID_MFA_CODE)
        else:
            pass  # Will render again the page
    else:
        # Make MFA send a code
        mfaInstance.process(str(request.user.pk), mfaIdentifier)

    # Redirect to index, but with MFA data
    request.session['mfa'] = {
        'label': label,
        'validity': mfaInstance.validity(),
    }
    return index(request)  # Render index with MFA data