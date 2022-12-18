# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Virtual Cable S.L.U.
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
Author: Adolfo Gómez, dkmaster at dkmon dot com
'''
import asyncio
import contextlib
import io
import logging
import socket
import ssl
import tempfile
import threading
import random
import typing
from unittest import mock
import multiprocessing

import udstunnel
from uds_tunnel import consts, tunnel, stats

from . import certs, conf, fixtures, tools

if typing.TYPE_CHECKING:
    from uds_tunnel import config
    from multiprocessing.connection import Connection


logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def create_tunnel_proc(
    listen_host: str,
    listen_port: int,
    remote_host: str,
    remote_port: int,
    *,
    workers: int = 1
) -> typing.AsyncGenerator['config.ConfigurationType', None]:
    # Create the ssl cert
    cert, key, password = certs.selfSignedCert(listen_host, use_password=False)
    # Create the certificate file on /tmp
    cert_file = '/tmp/tunnel_full_cert.pem'
    with open(cert_file, 'w') as f:
        f.write(key)
        f.write(cert)

    # Config file for the tunnel, ignore readed
    values, cfg = fixtures.get_config(
        address=listen_host,
        port=listen_port,
        ipv6=':' in listen_host,
        ssl_certificate=cert_file,
        ssl_certificate_key='',
        ssl_password=password,
        ssl_ciphers='',
        ssl_dhparam='',
        workers=workers,
    )
    args = mock.MagicMock()
    args.config = io.StringIO(fixtures.TEST_CONFIG.format(**values))
    args.ipv6 = ':' in listen_host

    with mock.patch(
        'uds_tunnel.tunnel.TunnelProtocol._readFromUDS',
        new_callable=tools.AsyncMock,
    ) as m:
        m.return_value = conf.UDS_GET_TICKET_RESPONSE(remote_host, remote_port)

        # Stats collector
        gs = stats.GlobalStats()
        # Pipe to send data to tunnel
        own_end, other_end = multiprocessing.Pipe()

        # Set running flag
        udstunnel.running.set()

        # Create the tunnel task
        task = asyncio.create_task(udstunnel.tunnel_proc_async(other_end, cfg, gs.ns))

        # Create a small asyncio server that reads the handshake,
        # and sends the socket to the tunnel_proc_async using the pipe
        # the pipe message will be typing.Tuple[socket.socket, typing.Tuple[str, int]]
        # socket and address
        async def client_connected_db(reader, writer):
            # Read the handshake
            data = await reader.read(1024)
            # For testing, we ignore the handshake value
            # Send the socket to the tunnel
            own_end.send(
                (
                    writer.get_extra_info('socket').dup(),
                    writer.get_extra_info('peername'),
                )
            )
            # Close the socket
            writer.close()

        server = await asyncio.start_server(
            client_connected_db,
            listen_host,
            listen_port,
        )
        try:
            yield cfg
        finally:
            # Close the pipe (both ends)
            own_end.close()

            task.cancel()
            # wait for the task to finish
            await task

            server.close()
            await server.wait_closed()
            logger.info('Server closed')


async def create_tunnel_server(
    cfg: 'config.ConfigurationType', context: 'ssl.SSLContext'
) -> 'asyncio.Server':
    # Create fake proxy
    proxy = mock.MagicMock()
    proxy.cfg = cfg
    proxy.ns = mock.MagicMock()
    proxy.ns.current = 0
    proxy.ns.total = 0
    proxy.ns.sent = 0
    proxy.ns.recv = 0
    proxy.counter = 0

    loop = asyncio.get_running_loop()

    # Create an asyncio listen socket on cfg.listen_host:cfg.listen_port
    return await loop.create_server(
        lambda: tunnel.TunnelProtocol(proxy),
        cfg.listen_address,
        cfg.listen_port,
        ssl=context,
        family=socket.AF_INET6
        if cfg.ipv6 or ':' in cfg.listen_address
        else socket.AF_INET,
    )


@contextlib.asynccontextmanager
async def create_test_tunnel(
    *, callback: typing.Callable[[bytes], None]
) -> typing.AsyncGenerator['config.ConfigurationType', None]:
    # Generate a listening server for testing tunnel
    # Prepare the end of the tunnel
    async with tools.AsyncTCPServer(port=54876, callback=callback) as server:
        # Create a tunnel to localhost 13579
        # SSl cert for tunnel server
        with certs.ssl_context(server.host) as (ssl_ctx, _):
            _, cfg = fixtures.get_config(
                address=server.host,
                port=7777,
                ipv6=':' in server.host,
            )
            with mock.patch(
                'uds_tunnel.tunnel.TunnelProtocol._readFromUDS',
                new_callable=tools.AsyncMock,
            ) as m:
                m.return_value = conf.UDS_GET_TICKET_RESPONSE(server.host, server.port)

                tunnel_server = await create_tunnel_server(cfg, ssl_ctx)
                try:
                    yield cfg
                finally:
                    tunnel_server.close()
                    await tunnel_server.wait_closed()


@contextlib.asynccontextmanager
async def open_tunnel_client(
    cfg: 'config.ConfigurationType',
    use_tunnel_handshake: bool = False,
) -> typing.AsyncGenerator[
    typing.Tuple[asyncio.StreamReader, asyncio.StreamWriter], None
]:
    """opens an ssl socket to the tunnel server"""
    loop = asyncio.get_running_loop()
    family = socket.AF_INET6 if cfg.ipv6 or ':' in cfg.listen_address else socket.AF_INET
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    if not use_tunnel_handshake:
        reader, writer = await asyncio.open_connection(
            cfg.listen_address, cfg.listen_port, ssl=context, family=family
        )
    else:
        # Open the socket, send handshake and then upgrade to ssl, non blocking
        sock = socket.socket(family, socket.SOCK_STREAM)
        # Set socket to non blocking
        sock.setblocking(False)
        await loop.sock_connect(sock, (cfg.listen_address, cfg.listen_port))
        await loop.sock_sendall(sock, consts.HANDSHAKE_V1)
        # upgrade to ssl
        reader, writer = await asyncio.open_connection(
            sock=sock, ssl=context, server_hostname=cfg.listen_address
        )
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()
