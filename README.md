# termegle
run `ssh -p 6767 termegle.sirbread.dev` <br>
you'll see a security prompt, which is normal, type in yes <br>
if you see a "HOST KEY CHANGED" warning in big scary letters, this means the server restarted, run this first: `ssh-keygen -R "[37.27.51.34]:8022"` <br>

## todo
- interest tags (STRICTLY to match interests, not to be displayed, after match, say what the common insterest is)
- inactive user timeout
- connection stats (You've chatted with {self.chat_count} strangers this session!) type
- "stranger saved the chat" being seen after any stranger saves, on both ends in cyan
- ~~colors~~
- ~~timestamps~~
- ~~user count display~~
- ~~save chat histroy~~
- ~~ascii art~~
- ~~appending "you" to the start of every message you send~~