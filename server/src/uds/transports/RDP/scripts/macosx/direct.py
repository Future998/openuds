# This is a template
# Saved as .py for easier editing
from __future__ import unicode_literals

# pylint: disable=import-error, no-name-in-module, too-many-format-args, undefined-variable, invalid-sequence-index
import subprocess
import shutil
import os

from uds import tools  # @UnresolvedImport

# Inject local passed sp into globals for functions
globals()['sp'] = sp  # type: ignore  # pylint: disable=undefined-variable

msrdc = '/Applications/Microsoft Remote Desktop.app/Contents/MacOS/Microsoft Remote Desktop'
xfreerdp = '/usr/local/bin/xfreerdp'
executable = None

def fixResolution():
    import re
    import subprocess
    results = str(subprocess.Popen(['system_profiler SPDisplaysDataType'],stdout=subprocess.PIPE, shell=True).communicate()[0])
    res = re.search(': \d* x \d*', results).group(0).split(' ')
    width, height = str(int(res[1])-4), str(int(int(res[3])-128))  # Width and Height
    return list(map(lambda x: x.replace('#WIDTH#', width).replace('#HEIGHT#', height), sp['as_new_xfreerdp_params']))

# Check first xfreerdp, allow password redir
if os.path.isfile(xfreerdp):
    executable = xfreerdp
elif os.path.isfile(msrdc) and sp['as_file']:
    executable = msrdc

if executable is None:
    if sp['as_file']:
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
elif executable == msrdc:
    theFile = sp['as_file']
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

    params = [executable] + xfparms + ['/v:{}'.format(sp['address'])]  # @UndefinedVariable
    subprocess.Popen(params)

