# This is a template
# Saved as .py for easier editing
from __future__ import unicode_literals

# pylint: disable=import-error, no-name-in-module, too-many-format-args, undefined-variable, invalid-sequence-index
import subprocess
import re
from uds.forward import forward  # @UnresolvedImport

from uds import tools  # @UnresolvedImport

# Inject local passed sp into globals for functions
globals()['sp'] = sp  # type: ignore  # pylint: disable=undefined-variable

def execUdsRdp(udsrdp, port):
    import subprocess  # @Reimport
    params = [udsrdp] + sp['as_new_xfreerdp_params'] + ['/v:127.0.0.1:{}'.format(port)]  # @UndefinedVariable
    tools.addTaskToWait(subprocess.Popen(params))


def execNewXFreeRdp(xfreerdp, port):
    import subprocess  # @Reimport
    params = [xfreerdp] + sp['as_new_xfreerdp_params'] + ['/v:127.0.0.1:{}'.format(port)]  # @UndefinedVariable
    tools.addTaskToWait(subprocess.Popen(params))

# Try to locate a "valid" version of xfreerdp as first option (<1.1 does not allows drive redirections, so it will not be used if found)
xfreerdp = tools.findApp('xfreerdp')
udsrdp = tools.findApp('udsrdp')
fnc, app = None, None

if xfreerdp:
    fnc, app = execNewXFreeRdp, xfreerdp

if udsrdp:
    fnc, app = execUdsRdp, udsrdp

if app is None or fnc is None:
    raise Exception('''<p>You need to have installed xfreerdp (>= 1.1) or rdesktop, and have them in your PATH in order to connect to this UDS service.</p>
    <p>Please, install apropiate package for your system.</p>
    <p>Also note that xfreerdp prior to version 1.1 will not be taken into consideration.</p>
''')
else:
    # Open tunnel
    forwardThread, port = forward(sp['tunHost'], sp['tunPort'], sp['tunUser'], sp['tunPass'], sp['ip'], 3389, waitTime=sp['tunWait'])

    if forwardThread.status == 2:
        raise Exception('Unable to open tunnel')

    fnc(app, port)  # @UndefinedVariable
