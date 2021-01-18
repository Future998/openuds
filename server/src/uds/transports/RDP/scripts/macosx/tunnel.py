# This is a template
# Saved as .py for easier editing
from __future__ import unicode_literals

# pylint: disable=import-error, no-name-in-module, too-many-format-args, undefined-variable, invalid-sequence-index
import subprocess
import shutil
import os

from uds.tunnel import forward  # type: ignore

from uds import tools  # type: ignore

# Inject local passed sp into globals for functions
globals()['sp'] = sp  # type: ignore  # pylint: disable=undefined-variable

def fixResolution():
    import re
    import subprocess
    results = str(subprocess.Popen(['system_profiler SPDisplaysDataType'],stdout=subprocess.PIPE, shell=True).communicate()[0])
    res = re.search(': \d* x \d*', results).group(0).split(' ')
    width, height = str(int(res[1])-4), str(int(int(res[3])-128))  # Width and Height
    return list(map(lambda x: x.replace('#WIDTH#', width).replace('#HEIGHT#', height), sp['as_new_xfreerdp_params']))


msrdc = '/Applications/Microsoft Remote Desktop.app/Contents/MacOS/Microsoft Remote Desktop'
xfreerdp = '/usr/local/bin/xfreerdp'
executable = None

# Check first xfreerdp, allow password redir
if os.path.isfile(xfreerdp):
    executable = xfreerdp
elif os.path.isfile(msrdc) and sp['as_file']:
    executable = msrdc

if executable is None:
    if sp['as_rdp_url']:
        raise Exception('''<p><b>Microsoft Remote Desktop or xfreerdp not found</b></p>
            <p>In order to connect to UDS RDP Sessions, you need to have a<p>
            <ul>
                <li>
                    <p><b>Microsoft Remote Desktop</b> from Apple Store</p>
                </li>
                <li>
                    <p><b>Xfreerdp</b> from homebrew</p>
                </li>
            </ul>
            ''')
    else:
        raise Exception('''<p><b>xfreerdp not found</b></p>
            <p>In order to connect to UDS RDP Sessions, you need to have a<p>
            <ul>
                <li>
                    <p><b>Xfreerdp</b> from homebrew</p>
                    <p>
                        <ul>
                            <li>Install brew (from <a href="https://brew.sh">brew website</a>)</li>
                            <li>Install xquartz<br/>
                                <b>brew cask install xquartz</b></li>
                            <li>Install freerdp<br/>
                                <b>brew install freerdp</b></li>
                            <li>Reboot so xquartz will be automatically started when needed</li>
                        </ul>
                    </p>
                </li>
            </ul>
            ''')

# Open tunnel
fs = forward(remote=(sp['tunHost'], int(sp['tunPort'])), ticket=sp['ticket'], timeout=sp['tunWait'], check_certificate=sp['tunChk'])

# Check that tunnel works..
if fs.check() is False:
    raise Exception('<p>Could not connect to tunnel server.</p><p>Please, check your network settings.</p>')

if executable == msrdc:
    theFile = theFile = sp['as_file'].format(
        address='127.0.0.1:{}'.format(fs.server_address[1])
    )

    filename = tools.saveTempFile(theFile)
    # Rename as .rdp, so open recognizes it
    shutil.move(filename, filename + '.rdp')

    tools.addTaskToWait(subprocess.Popen(['open', filename + '.rdp']))
    tools.addFileToUnlink(filename + '.rdp')
elif executable == xfreerdp:
    # Fix resolution...
    try:
        xfparms = fixResolution()
    except Exception as e:
        xfparms = list(map(lambda x: x.replace('#WIDTH#', '1400').replace('#HEIGHT#', '800'), sp['as_new_xfreerdp_params']))

    params = [executable] + xfparms + ['/v:{}'.format(address)]
    subprocess.Popen(params)

