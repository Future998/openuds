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
Author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import time
import logging
import hashlib
import typing
import random
import json

from django.middleware import csrf
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.utils.translation import gettext as _

from django.views.decorators.cache import never_cache

from uds.core.util.request import ExtendedHttpRequest, ExtendedHttpRequestWithUser
from uds.core.auths import auth, exceptions
from uds.core.managers import cryptoManager
from uds.web.util import errors
from uds.web.forms.LoginForm import LoginForm
from uds.web.forms.MFAForm import MFAForm
from uds.web.util.authentication import checkLogin
from uds.web.util.services import getServicesData
from uds.web.util import configjs
from uds.core import mfas
from uds import models



logger = logging.getLogger(__name__)

CSRF_FIELD = 'csrfmiddlewaretoken'
MFA_COOKIE_NAME = 'mfa_status'

if typing.TYPE_CHECKING:
    pass

@never_cache
def index(request: HttpRequest) -> HttpResponse:
    # Gets csrf token
    csrf_token = csrf.get_token(request)
    if csrf_token is not None:
        csrf_token = str(csrf_token)

    response = render(
        request,
        'uds/modern/index.html',
        {'csrf_field': CSRF_FIELD, 'csrf_token': csrf_token},
    )

    # Ensure UDS cookie is present
    auth.getUDSCookie(request, response)

    return response


# Includes a request.session ticket, indicating that
@never_cache
def ticketLauncher(request: HttpRequest) -> HttpResponse:
    request.session['restricted'] = True  # Access is from ticket
    return index(request)


# Basically, the original /login method, but fixed for modern interface
@never_cache
def login(
    request: ExtendedHttpRequest, tag: typing.Optional[str] = None
) -> HttpResponse:
    # Default empty form
    logger.debug('Tag: %s', tag)
    response: typing.Optional[HttpResponse] = None
    if request.method == 'POST':
        request.session['restricted'] = False  # Access is from login
        request.authorized = (
            False  # Ensure that on login page, user is unauthorized first
        )

        form = LoginForm(request.POST, tag=tag)
        loginResult = checkLogin(request, form, tag)
        if loginResult.user:
            response = HttpResponseRedirect(reverse('page.index'))
            # save tag, weblogin will clear session
            tag = request.session.get('tag')
            auth.webLogin(request, response, loginResult.user, loginResult.password)  # data is user password here
            # And restore tag
            request.session['tag'] = tag

            # If MFA is provided, we need to redirect to MFA page
            request.authorized = True
            if loginResult.user.manager.getType().providesMfa() and loginResult.user.manager.mfa:
                authInstance = loginResult.user.manager.getInstance()
                request.authorized = False
                response = HttpResponseRedirect(reverse('page.mfa'))

        else:
            # If redirection on login failure is found, honor it
            if loginResult.url:  # Redirection
                return HttpResponseRedirect(loginResult.url)

            if request.ip not in ('127.0.0.1', '::1'):  # If not localhost, wait a bit
                time.sleep(random.SystemRandom().randint(1600, 2400) / 1000)  # On failure, wait a bit if not localhost (random wait)
            # If error is numeric, redirect...
            if loginResult.errid:
                return errors.errorView(request, loginResult.errid)

            # Error, set error on session for process for js
            request.session['errors'] = [loginResult.errstr]
    else:
        request.session['tag'] = tag

    return response or index(request)


@never_cache
@auth.webLoginRequired(admin=False)
def logout(request: ExtendedHttpRequestWithUser) -> HttpResponse:
    auth.authLogLogout(request)
    request.session['restricted'] = False  # Remove restricted
    request.authorized = False
    logoutResponse = request.user.logout(request)
    return auth.webLogout(
        request, logoutResponse.url or request.session.get('logouturl', None)
    )


@never_cache
def js(request: ExtendedHttpRequest) -> HttpResponse:
    return HttpResponse(
        content=configjs.udsJs(request), content_type='application/javascript'
    )


@never_cache
@auth.denyNonAuthenticated  # webLoginRequired not used here because this is not a web page, but js
def servicesData(request: ExtendedHttpRequestWithUser) -> HttpResponse:
    return JsonResponse(getServicesData(request))


# The MFA page does not needs CRF token, so we disable it
@csrf_exempt
def mfa(request: ExtendedHttpRequest) -> HttpResponse:
    if (
        not request.user or request.authorized
    ):  # If no user, or user is already authorized, redirect to index
        return HttpResponseRedirect(reverse('page.index'))  # No user, no MFA

    mfaProvider: typing.Optional['models.MFA'] = request.user.manager.mfa
    if not mfaProvider:
        return HttpResponseRedirect(reverse('page.index'))

    userHashValue: str = hashlib.sha3_256(
        (request.user.name + (request.user.uuid or '') + mfaProvider.uuid + request.ip).encode()
    ).hexdigest()

    # Try to get cookie anc check it
    mfaCookie = request.COOKIES.get(MFA_COOKIE_NAME, None)
    if mfaCookie == userHashValue:  # Cookie is valid, skip MFA setting authorization
        request.authorized = True
        return HttpResponseRedirect(reverse('page.index'))

    # Obtain MFA data
    authInstance = request.user.manager.getInstance()
    mfaInstance = mfaProvider.getInstance()

    # Get validity duration
    validity = min(mfaInstance.validity(), mfaProvider.validity) * 60
    start_time = request.session.get('mfa_start_time', time.time())

    # If mfa process timed out, we need to start login again
    if validity > 0 and time.time() - start_time > validity:
        request.session.flush()  # Clear session, and redirect to login
        return HttpResponseRedirect(reverse('page.login'))

    mfaIdentifier = authInstance.mfaIdentifier(request.user.name)
    label = mfaInstance.label()

    if not mfaIdentifier:
        if mfaInstance.emptyIndentifierAllowedToLogin(request):
            # Allow login
            request.authorized = True
            return HttpResponseRedirect(reverse('page.index'))
        # Not allowed to login, redirect to login error page
        logger.warning(
            'MFA identifier not found for user %s on authenticator %s. It is required by MFA %s',
            request.user.name,
            request.user.manager.name,
            mfaProvider.name,
        )
        return errors.errorView(request, errors.ACCESS_DENIED)

    if request.method == 'POST':  # User has provided MFA code
        form = MFAForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                mfaInstance.validate(
                    request,
                    userHashValue,
                    request.user.name,
                    mfaIdentifier,
                    code,
                    validity=validity,
                )
                request.authorized = True
                # Remove mfa_start_time from session
                if 'mfa_start_time' in request.session:
                    del request.session['mfa_start_time']

                response = HttpResponseRedirect(reverse('page.index'))
                # If mfaProvider requests to keep MFA code on client, create a mfacookie for this user
                if (
                    mfaProvider.remember_device > 0
                    and form.cleaned_data['remember'] is True
                ):
                    response.set_cookie(
                        MFA_COOKIE_NAME,
                        userHashValue,
                        max_age=mfaProvider.remember_device * 60 * 60,
                    )

                return response
            except exceptions.MFAError as e:
                logger.error('MFA error: %s', e)
                return errors.errorView(request, errors.INVALID_MFA_CODE)
        else:
            pass  # Will render again the page
    else:
        # Make MFA send a code
        try:
            result = mfaInstance.process(
                request,
                userHashValue,
                request.user.name,
                mfaIdentifier,
                validity=validity,
            )
            if result == mfas.MFA.RESULT.ALLOWED:
                # MFA not needed, redirect to index after authorization of the user
                request.authorized = True
                return HttpResponseRedirect(reverse('page.index'))

            # store on session the start time of the MFA process if not already stored
            if 'mfa_start_time' not in request.session:
                request.session['mfa_start_time'] = time.time()
        except Exception as e:
            logger.error('Error processing MFA: %s', e)
            return errors.errorView(request, errors.UNKNOWN_ERROR)

    # Compose a nice "XX years, XX months, XX days, XX hours, XX minutes" string from mfaProvider.remember_device
    remember_device = ''
    # Remember_device is in hours
    if mfaProvider.remember_device > 0:
        # if more than a day, we show days only
        if mfaProvider.remember_device >= 24:
            remember_device = _('{} days').format(mfaProvider.remember_device // 24)
        else:
            remember_device = _('{} hours').format(mfaProvider.remember_device)

    # Html from MFA provider
    mfaHtml = mfaInstance.html(request)

    # Redirect to index, but with MFA data
    request.session['mfa'] = {
        'label': label or _('MFA Code'),
        'validity': validity if validity >= 0 else 0,
        'remember_device': remember_device,
        'html': mfaHtml,
    }
    return index(request)  # Render index with MFA data

@csrf_exempt
@auth.denyNonAuthenticated
def update_transport_ticket(request: ExtendedHttpRequestWithUser, idTicket: str, scrambler: str) -> HttpResponse:
    try:
        if request.method == 'POST':
            # Get request body as json
            data = json.loads(request.body)

            # Update username andd password in ticket
            username = data.get('username', None) or None # None if not present
            password = data.get('password', None) or None # If password is empty, set it to None
            domain = data.get('domain', None) or None  # If empty string, set to None

            if password:
                password = cryptoManager().symCrypt(password, scrambler)

            def checkValidTicket(data: typing.Mapping[str, typing.Any]) -> bool:
                if 'ticket-info' not in data:
                    return True
                try:
                    user = models.User.objects.get(uuid=data['ticket-info'].get('user', None))
                    if request.user == user:
                        return True
                except models.User.DoesNotExist:
                    pass
                return False
                

            models.TicketStore.update(
                uuid=idTicket,
                checkFnc=checkValidTicket,
                username=username,
                password=password,
                domain=domain,
            )
            return HttpResponse('{"status": "OK"}', status=200, content_type='application/json')
    except Exception as e:
        # fallback to error
        logger.warning('Error updating ticket: %s', e)

    # Invalid request
    return HttpResponse('{"status": "Invalid Request"}', status=400, content_type='application/json')
