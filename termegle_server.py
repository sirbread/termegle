import asyncio
import asyncssh
from datetime import datetime
from collections import defaultdict
import random

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

#add more? https://patorjk.com/software/taag/#p=display&f=Isometric3&t=TERMEGLE&x=none&v=4&h=4&w=80&we=false
ASCII_ARTS = [
    """
                  ___           ___           ___           ___           ___                         ___     
      ___        /  /\         /  /\         /__/\         /  /\         /  /\                       /  /\    
     /  /\      /  /:/_       /  /::\       |  |::\       /  /:/_       /  /:/_                     /  /:/_   
    /  /:/     /  /:/ /\     /  /:/\:\      |  |:|:\     /  /:/ /\     /  /:/ /\    ___     ___    /  /:/ /\  
   /  /:/     /  /:/ /:/_   /  /:/~/:/    __|__|:|\:\   /  /:/ /:/_   /  /:/_/::\  /__/\   /  /\  /  /:/ /:/_ 
  /  /::\    /__/:/ /:/ /\ /__/:/ /:/___ /__/::::| \:\ /__/:/ /:/ /\ /__/:/__\/\:\ \  \:\ /  /:/ /__/:/ /:/ /
 /__/:/\:\   \  \:\/:/ /:/ \  \:\/:::::/ \  \:\~~\__\/ \  \:\/:/ /:/ \  \:\ /~~/:/  \  \:\  /:/  \  \:\/:/ /:/
 \__\/  \:\   \  \::/ /:/   \  \::/~~~~   \  \:\        \  \::/ /:/   \  \:\  /:/    \  \:\/:/    \  \::/ /:/ 
      \  \:\   \  \:\/:/     \  \:\        \  \:\        \  \:\/:/     \  \:\/:/      \  \::/      \  \:\/:/  
       \__\/    \  \::/       \  \:\        \  \:\        \  \::/       \  \::/        \__\/        \  \::/   
                 \__\/         \__\/         \__\/         \__\/         \__\/                       \__\/    
    """
]

class ChatSession(asyncssh.SSHServerSession):
    def __init__(self):
        self.partner = None
        self.messages = [] 
        self.art = random.choice(ASCII_ARTS)

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self):
        return True

    def _timestamp(self):
        return datetime.now().strftime("[%H:%M]")

    def render(self):
        self._chan.write("\033[2J\033[H")

        self._chan.write("\r\n")
        self._chan.write(self.art)
        self._chan.write("\r\n\r\n\r\n")

        for role, text in self.messages[-20:]:
            ts = self._timestamp()
            if role == "system":
                self._chan.write(f"\033[36m{ts} {text}\033[0m\r\n")
            elif role == "stranger":
                self._chan.write(f"\033[31m{ts} stranger: {text}\033[0m\r\n")
            elif role == "you":
                self._chan.write(f"\033[34m{ts} you: {text}\033[0m\r\n")
        self._chan.write("\r\n> ")

    def session_started(self):
        matchmaker.active_users.add(self)
        online_count = len(matchmaker.active_users)
        self.messages.append(("system", f"{online_count} user{'s' if online_count != 1 else ' (just you...)'} online right now"))
        self.messages.append(("system", "finding you a stranger to chat with..."))
        self.render()
        asyncio.create_task(self.match_user())

    async def match_user(self):
        partner = await matchmaker.find_match(self)
        if partner:
            self.partner = partner
            partner.partner = self

            self.messages.append(("system", "connected to a stranger!"))
            self.render()

            partner.messages.append(("system", "connected to a stranger!"))
            partner.render()

    def data_received(self, data, datatype):
        try:
            msg = data.decode("utf-8", errors="ignore").strip() if isinstance(data, bytes) else str(data).strip()
            if not msg:
                return len(data)

            if msg.lower() == "quit":
                self.messages.append(("system", "cya!"))
                self.render()
                self._chan.close()
                return len(data)

            if msg.lower() == "next":
                if self.partner:
                    self.partner.messages.append(("system", "stranger disconnected. finding you a new stranger..."))
                    self.partner.render()
                    self.partner.partner = None
                    asyncio.create_task(self.partner.match_user())
                self.partner = None
                self.messages.append(("system", "finding a new stranger..."))
                self.render()
                asyncio.create_task(self.match_user())
                return len(data)

            if self.partner:
                self.messages.append(("you", msg))
                self.render()
                self.partner.messages.append(("stranger", msg))
                self.partner.render()
            else:
                self.messages.append(("system", "waiting for connection..."))
                self.render()

        except Exception as e:
            print(f"[{datetime.now()}] error in data_received: {e}")

        return len(data)

    def connection_lost(self, exc):
        print(f"[{datetime.now()}] user disconnected")
        matchmaker.remove(self)
        if self.partner:
            try:
                self.partner.messages.append(("system", "stranger disconnected. finding you a new stranger..."))
                self.partner.render()
                self.partner.partner = None
                asyncio.create_task(self.partner.match_user())
            except Exception:
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
        return False
    
    def public_key_auth_supported(self):
        return False
    
    def password_auth_supported(self):
        return False

    def session_requested(self):
        return ChatSession()

async def start_server():
    print("\n" + "="*50)
    print("  starting termegle ")
    print("="*50)
    
    host_key_path = '/home/sirbread/termegle_host_key'
    
    try:
        print(f"[{datetime.now()}] loading ssh host key...")
        host_key = asyncssh.read_private_key(host_key_path)
        print(f"[{datetime.now()}] loaded existing host key!")
    except:
        print(f"[{datetime.now()}] generating new ssh host key...")
        host_key = asyncssh.generate_private_key('ssh-rsa')
        with open(host_key_path, 'w') as f:
            f.write(host_key.export_private_key().decode())
        print(f"[{datetime.now()}] saved host key to {host_key_path}")

    port = 6767

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
        print(f"  ssh -p {port} termegle.sirbread.dev")
        print(f"  ssh -p {port} 37.27.51.34")
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
