import sys
import os.path
import subprocess
import typing

from uds.log import logger
import UDSClient
from UDSLauncherMac import Ui_MacLauncher

from PyQt5 import QtCore, QtWidgets, QtGui

SCRIPT_NAME = 'UDSClientLauncher'

class UdsApplication(QtWidgets.QApplication):
    path: str
    tunnels: typing.List[subprocess.Popen]

    def __init__(self, argv: typing.List[str]) -> None:
        super().__init__(argv)
        self.path = os.path.join(os.path.dirname(sys.argv[0]).replace('Resources', 'MacOS'), SCRIPT_NAME)
        self.tunnels = []
        self.lastWindowClosed.connect(self.closeTunnels)  # type: ignore

    def cleanTunnels(self) -> None:
        def isRunning(p: subprocess.Popen):
            try:
                if p.poll() is None:
                    return True
            except Exception as e:
                logger.debug('Got error polling subprocess: %s', e)
            return False

        for k in [i for i, tunnel in enumerate(self.tunnels) if not isRunning(tunnel)]:
            try:
                del self.tunnels[k]
            except Exception as e:
                logger.debug('Error closing tunnel: %s', e)

    def closeTunnels(self) -> None:
        logger.debug('Closing remaining tunnels')
        for tunnel in self.tunnels:
            logger.debug('Checking %s - "%s"', tunnel, tunnel.poll())
            if tunnel.poll() is None:  # Running
                logger.info('Found running tunnel %s, closing it', tunnel.pid)
                tunnel.kill()

    def event(self, evnt: QtCore.QEvent) -> bool:
        if evnt.type() == QtCore.QEvent.FileOpen:  # type: ignore
            fe = typing.cast(QtGui.QFileOpenEvent, evnt)
            logger.debug('Got url: %s', fe.url().url())
            fe.accept()
            logger.debug('Spawning %s', self.path)
            # First, remove all finished tunnel processed from check queue
            self.cleanTunnels()
            # And now add a new one
            self.tunnels.append(subprocess.Popen([self.path, fe.url().url()]))

        return super().event(evnt)


def main(args: typing.List[str]):
    if len(args) > 1:
        UDSClient.main(args)
    else:
        app = UdsApplication(sys.argv)
        window = QtWidgets.QMainWindow()
        Ui_MacLauncher().setupUi(window)

        window.showMinimized()

        sys.exit(app.exec())

if __name__ == "__main__":
    main(args=sys.argv)

