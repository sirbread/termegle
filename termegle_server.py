import asyncio
import asyncssh
from datetime import datetime
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.connections = defaultdict(list)

    def check_rate_limit(self, ip):
        now = datetime.now()
        self.connections[ip] = [
            time for time in self.connections[ip]
            if (now - time).total_seconds() < 60
        ]
        if len(self.connections[ip]) >= 5:
            return False
        self.connections[ip].append(now)
        return True

rate_limiter = RateLimiter()

class Matchmaker:
    def __init__(self):
        self.waiting = []
        self.active_users = set()

    async def find_match(self, session):
        if self.waiting:
            partner = self.waiting.pop(0)
            print(f"[{datetime.now()}]  matched two users! active: {len(self.active_users)}")
            return partner
        else:
            self.waiting.append(session)
            print(f"[{datetime.now()}]  user waiting... ({len(self.waiting)} in queue)")
            return None

    def remove(self, session):
        if session in self.waiting:
            self.waiting.remove(session)
        if session in self.active_users:
            self.active_users.remove(session)

matchmaker = Matchmaker()

class ChatSession(asyncssh.SSHServerSession):
    def __init__(self):
        self.partner = None

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self):
        return True

    def session_started(self):
        online_count = len(matchmaker.active_users) + 1
        self._chan.write("\r\n")
        self._chan.write("═══════════════════════════════════════\r\n")
        self._chan.write("     welcome to termegle!\r\n")
        self._chan.write("     anon terminal chat\r\n")
        self._chan.write("═══════════════════════════════════════\r\n")
        self._chan.write(f"  {online_count} user{'s' if online_count != 1 else ' (just you...)'} online right now\r\n")
        self._chan.write("\r\n")
        self._chan.write("finding you a stranger to chat with...\r\n")
        self._chan.write("\r\n")
        matchmaker.active_users.add(self)
        asyncio.create_task(self.match_user())

    async def match_user(self):
        partner = await matchmaker.find_match(self)
        if partner:
            self.partner = partner
            partner.partner = self
            self._chan.write("─────────────────────────────────────\r\n")
            self._chan.write("  connected to a stranger!\r\n")
            self._chan.write("─────────────────────────────────────\r\n")
            self._chan.write("\r\ncommands:\r\n")
            self._chan.write("   type to chat\r\n")
            self._chan.write("   'next' - find a new stranger\r\n")
            self._chan.write("   'quit' - exit\r\n\r\n")
            
            partner._chan.write("─────────────────────────────────────\r\n")
            partner._chan.write("  connected to a stranger!\r\n")
            partner._chan.write("─────────────────────────────────────\r\n")
            partner._chan.write("\r\ncommands:\r\n")
            partner._chan.write("   type to chat\r\n")
            partner._chan.write("   'next' - find a new stranger\r\n")
            partner._chan.write("   'quit' - exit\r\n\r\n")

    def data_received(self, data, datatype):
        try:
            if isinstance(data, bytes):
                msg = data.decode('utf-8', errors='ignore').strip()
            else:
                msg = str(data).strip()

            if msg.lower() == 'quit':
                self._chan.write("\r\ncya!\r\n")
                self._chan.close()
                return len(data) if isinstance(data, bytes) else len(str(data))

            if msg.lower() == 'next':
                if self.partner:
                    self.partner._chan.write("\r\n stranger disconnected.\r\n")
                    self.partner._chan.write("finding you a new stranger...\r\n\r\n")
                    self.partner.partner = None
                    asyncio.create_task(self.partner.match_user())
                self.partner = None
                self._chan.write("\r\nfinding a new stranger...\r\n\r\n")
                asyncio.create_task(self.match_user())
                return len(data) if isinstance(data, bytes) else len(str(data))

            if self.partner and msg:
                self.partner._chan.write(f"stranger: {msg}\r\n")
            elif not self.partner and msg:
                self._chan.write(" waiting for connection...\r\n")
        except Exception as e:
            print(f"[{datetime.now()}]  error in data_received: {e}")

        return len(data) if isinstance(data, bytes) else len(str(data))

    def connection_lost(self, exc):
        print(f"[{datetime.now()}]  user disconnected")
        matchmaker.remove(self)
        if self.partner:
            try:
                self.partner._chan.write("\r\n stranger disconnected.\r\n")
                self.partner._chan.write("finding you a new stranger...\r\n\r\n")
                self.partner.partner = None
                asyncio.create_task(self.partner.match_user())
            except:
                pass

class TermegleServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        peer = conn.get_extra_info('peername')
        ip = peer[0] if peer else 'unknown'

        if not rate_limiter.check_rate_limit(ip):
            print(f"[{datetime.now()}]   this guy aint slick, rate limit exceeded for {ip}")
            conn.close()
            return

        print(f"[{datetime.now()}]  new connection from {ip} (active: {len(matchmaker.active_users)})")

    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        print(f"[{datetime.now()}]  login: {username}")
        return True

    def session_requested(self):
        return ChatSession()

async def start_server():
    print("\n" + "="*50)
    print("  starting termegle ")
    print("="*50)
    print(f"[{datetime.now()}] generating ssh host key...")

    host_key = asyncssh.generate_private_key('ssh-rsa')
    port = 8022

    print(f"[{datetime.now()}] starting server on port {port}...")

    try:
        await asyncssh.create_server(
            TermegleServer,
            '0.0.0.0',
            port,
            server_host_keys=[host_key]
        )

        print(f"\n server is running on port {port}!")
        print("\nusers can connect with:")
        print(f"  ssh -p {port} chat@termegle.sirbread.dev") #not implemented yet!!!!
        print(f"  ssh -p {port} chat@37.27.51.34") #nest server
        print("\npress ctrl+c to stop")
        print("="*50 + "\n")

        await asyncio.Event().wait()

    except Exception as e:
        print(f"\n error starting server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\n\n" + "="*50)
        print("  server stopped ")
        print("="*50)
