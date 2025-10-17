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
        self.waiting = {}
        self.active_users = set()

    async def find_match(self, session, interests):
        if session in self.waiting:
            del self.waiting[session]

        #first try to find someone with common interests (prefer who joined first)
        best_match = None
        best_common = set()
        earliest_time = None

        for potential_partner, (partner_interests, join_time) in list(self.waiting.items()):
            if potential_partner is session:
                continue

            common = interests & partner_interests

            if common:
                #if we have common interests, prefer the person whos been waiting longest
                if not best_match or join_time < earliest_time:
                    best_match = potential_partner
                    best_common = common
                    earliest_time = join_time

        #if we found someone with common interests, match with them
        if best_match:
            del self.waiting[best_match]
            print(f"[{datetime.now()}]  matched two users with {len(best_common)} common interest(s)! active: {len(self.active_users)}")
            return best_match, best_common

        #fifo, match with the person whos been waiting the longest 
        if len(self.waiting) > 0:
            oldest_session = None
            oldest_time = None

            for potential_partner, (partner_interests, join_time) in list(self.waiting.items()):
                if potential_partner is session:
                    continue
                if oldest_session is None or join_time < oldest_time:
                    oldest_session = potential_partner
                    oldest_time = join_time
            if oldest_session:
                del self.waiting[oldest_session]
                print(f"[{datetime.now()}]  matched two users (no common interests, FIFO)! active: {len(self.active_users)}")
                return oldest_session, set()

        #no match found add to waiting with current time
        self.waiting[session] = (interests, datetime.now())
        print(f"[{datetime.now()}]  user waiting... ({len(self.waiting)} in queue)")
        return None, set()

    def remove(self, session):
        if session in self.waiting:
            del self.waiting[session]
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
        self.terminal_height = 24
        self.visible_lines = None
        self.save_mode = False
        self.matched = False
        self.last_active = datetime.now()
        self.chat_count = 0
        self.interests = set()
        self.awaiting_interests = True
        self.interest_buffer = ""

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self):
        return True

    def terminal_size_changed(self, width, height, pixwidth, pixheight):
        self.terminal_height = height if height > 0 else 24
        self.visible_lines = max(5, self.terminal_height - 18)
        if not self.save_mode and not self.awaiting_interests:
            self.render()

    def _timestamp(self):
        return datetime.now().strftime("[%H:%M]")

    def render(self):
        self._chan.write("\033[2J\033[H")

        if not self.matched:
            self._chan.write("\r\n")
            self._chan.write(self.art)
            self._chan.write("\r\n\r\n")

        if self.visible_lines is None:
            lines_to_show = 20
        else:
            lines_to_show = self.visible_lines

        if self.matched:
            filtered_messages = []
            for msg in self.messages:
                msg_time, role, text, show_timestamp = msg
                if "online right now" in text or text == "finding you a stranger to chat with..." or text == "stranger disconnected." or text == "the stranger was disconnected for inactivity.":
                    continue
                filtered_messages.append(msg)
        else:
            filtered_messages = self.messages

        recent_messages = filtered_messages[-lines_to_show:] if len(filtered_messages) > lines_to_show else filtered_messages
        
        for msg_time, role, text, show_timestamp in recent_messages:
            if role == "system" and text == "─" * 78 and self.chat_count > 0: #some really reliable code
                self._chan.write(f"\033[36myou've chatted with {self.chat_count} stranger{'s' if self.chat_count != 1 else ''} this session!\033[0m\r\n")
            if role == "system":
                if show_timestamp:
                    self._chan.write(f"\033[36m{msg_time} {text}\033[0m\r\n")
                else:
                    self._chan.write(f"\033[36m{text}\033[0m\r\n")
            elif role == "matched":
                self._chan.write(f"\033[33m{text}\033[0m\r\n")
            elif role == "stranger":
                self._chan.write(f"\033[31m{msg_time} stranger: {text}\033[0m\r\n")
            elif role == "you":
                self._chan.write(f"\033[34m{msg_time} you: {text}\033[0m\r\n")

        self._chan.write("\r\n> ")

    def show_full_chat(self):
        self.save_mode = True

        self._chan.write("\033[2J\033[H")

        self._chan.write("=" * 60 + "\r\n")
        self._chan.write("TERMEGLE CHAT LOG\r\n")
        self._chan.write(f"saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\r\n")
        self._chan.write(f"total messages: {len(self.messages)}\r\n")
        self._chan.write("=" * 60 + "\r\n")
        self._chan.write("\r\n")

        for msg_time, role, text, show_timestamp in self.messages:
            if role == "system" or role == "matched":
                if show_timestamp:
                    self._chan.write(f"{msg_time} [SYSTEM] {text}\r\n")
                else:
                    self._chan.write(f"[SYSTEM] {text}\r\n")
            elif role == "stranger":
                self._chan.write(f"{msg_time} [STRANGER] {text}\r\n")
            elif role == "you":
                self._chan.write(f"{msg_time} [YOU] {text}\r\n")

        self._chan.write("\r\n")
        self._chan.write("=" * 60 + "\r\n")
        self._chan.write("end of chat log - select all and copy to save!\r\n")
        self._chan.write("=" * 60 + "\r\n")
        self._chan.write("\r\n")
        self._chan.write("type 'back' to return to chat, or 'quit' to exit\r\n")
        self._chan.write("> ")

    def add_message(self, role, text, show_timestamp=True):
        timestamp = self._timestamp()
        self.messages.append((timestamp, role, text, show_timestamp))

    def clear_chat_and_reset(self, disconnect_reason=None):

        self.messages = []
        online_count = len(matchmaker.active_users)
        self.add_message("system", f"{online_count} user{'s' if online_count != 1 else ' (just you...)'} online right now", show_timestamp=False)

        if disconnect_reason:
            self.add_message("matched", disconnect_reason, show_timestamp=False)
        else:
            self.add_message("matched", "stranger disconnected.", show_timestamp=False)
        self.add_message("system", "finding you a stranger to chat with...", show_timestamp=False)

        self.add_message("system", "commands: 'save' to view full chat | 'next' for new stranger | 'quit' to exit", show_timestamp=False)
        self.add_message("system", "─" * 78, show_timestamp=False)

    def session_started(self):
        matchmaker.active_users.add(self)

        self._chan.write("\033[2J\033[H")
        self._chan.write("\r\n")
        self._chan.write(self.art)
        self._chan.write("\r\n\r\n")
        self._chan.write("\033[36mwhat are your interests? enter to skip (separate with commas)\033[0m\r\n")
        self._chan.write("\033[36mexample: gaming, sports, pb and j\033[0m\r\n\r\n")
        self._chan.write("> ")

    async def match_user(self):
        if self in [s for s in matchmaker.waiting.keys()]:
            del matchmaker.waiting[self]

        partner, common_interests = await matchmaker.find_match(self, self.interests)

        if partner:
            self.partner = partner
            partner.partner = self

            self.matched = True
            partner.matched = True
            self.chat_count += 1
            partner.chat_count += 1
            self.add_message("matched", "connected to a stranger!", show_timestamp=False)

            if common_interests:
                interests_list = sorted(list(common_interests))
                if len(interests_list) == 1:
                    interests_text = f"you both like {interests_list[0]}."
                elif len(interests_list) == 2:
                    interests_text = f"you both like {interests_list[0]} and {interests_list[1]}."
                else:
                    interests_text = f"you both like {', '.join(interests_list[:-1])}, and {interests_list[-1]}."
                
                self.add_message("matched", interests_text, show_timestamp=False)
                partner.add_message("matched", interests_text, show_timestamp=False)
            
            self.render()

            partner.add_message("matched", "connected to a stranger!", show_timestamp=False)
            partner.render()

    async def goon_sesh(self):
        warned = False
        while True:
            await asyncio.sleep(30)
            if self._chan.is_closing():
                break
            inactive_time = (datetime.now() - self.last_active).total_seconds()
            if inactive_time > 240 and not warned:
                self.add_message("system", "you'll be disconnected in 1 minute due to inactivity.", show_timestamp=False)
                self.render()
                warned = True
            elif inactive_time > 300:
                self.add_message("system", "you were disconnected for being inactive for 5 minutes.", show_timestamp=False)
                self.render()
                self._chan.write("\r\ninactivity timeout - disconnected.\r\n")
                self._chan.close()
                if self.partner:
                    matchmaker.remove(self)
                    self.partner.clear_chat_and_reset(disconnect_reason="the stranger was disconnected for inactivity.")
                    self.partner.partner = None
                    self.partner.matched = False
                    self.partner.render()
                    asyncio.create_task(self.partner.match_user())
                break

    def data_received(self, data, datatype):
        try:
            msg = data.decode("utf-8", errors="ignore").strip() if isinstance(data, bytes) else str(data).strip()
            
            if self.awaiting_interests:
                if msg:
                    raw_interests = [i.strip().lower() for i in msg.split(',')]
                    self.interests = set(i for i in raw_interests if i and len(i) > 0)
                
                self.awaiting_interests = False
                
                online_count = len(matchmaker.active_users)
                self.add_message("system", f"{online_count} user{'s' if online_count != 1 else ' (just you...)'} online right now", show_timestamp=False)
                self.add_message("system", "finding you a stranger to chat with...", show_timestamp=False)
                self.add_message("system", "commands: 'save' to view full chat | 'next' for new stranger | 'quit' to exit", show_timestamp=False)
                self.add_message("system", "" * 78, show_timestamp=False)
                
                self.render()
                asyncio.create_task(self.match_user())
                asyncio.create_task(self.goon_sesh())
                return len(data)
            
            if not msg:
                return len(data)
            self.last_active = datetime.now()
            if msg.lower() == "quit":
                if not self.save_mode:
                    self.add_message("system", "cya!")
                    self.render()
                self._chan.write("\r\ncya!\r\n")
                self._chan.close()
                return len(data)

            if msg.lower() == "back" and self.save_mode:
                self.save_mode = False
                self.render()
                return len(data)

            if msg.lower() == "save" and not self.save_mode:
                self.show_full_chat()
                t = self._timestamp()
                self.add_message("system", f"{t} you saved the chat log. (stranger can see this)", show_timestamp=False)
                if self.partner:
                    self.partner.add_message("system", f"{t} the stranger saved the chat log.", show_timestamp=False)
                    self.partner.render()
                return len(data)

            if self.save_mode:
                self._chan.write("Type 'back' to return to chat, or 'quit' to exit\r\n> ")
                return len(data)

            if msg.lower() == "next":
                if self.partner:
                    self.partner.clear_chat_and_reset()
                    self.partner.partner = None
                    self.partner.matched = False 
                    self.partner.render()
                    asyncio.create_task(self.partner.match_user())
                    
                self.partner = None
                self.matched = False
                self.clear_chat_and_reset()
                self.render()
                asyncio.create_task(self.match_user())
                return len(data)

            if self.partner:
                self.add_message("you", msg)
                self.render()
                self.partner.add_message("stranger", msg)
                self.partner.render()
            else:
                self.add_message("system", "waiting for connection...")
                self.render()

        except Exception as e:
            print(f"[{datetime.now()}] error in data_received: {e}")

        return len(data)

    def connection_lost(self, exc):
        print(f"[{datetime.now()}] user disconnected (had {len(self.messages)} messages)")
        matchmaker.remove(self)
        if self.partner:
            if self.partner.matched:  #only handle if not already handled (like inactivity disconnect) (some great wording)
                try:
                    self.partner.clear_chat_and_reset()
                    self.partner.partner = None
                    self.partner.matched = False
                    self.partner.render()
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
    
    host_key_path = 'termegle_host_key'
    
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
