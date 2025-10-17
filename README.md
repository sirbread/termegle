<div align="center">
  <img width="883" height="272" alt="image" src="https://github.com/user-attachments/assets/568d518a-7b0a-445b-a45c-d5c34410e2df" />
</div>
<br>
<br>
talk to strangers, in the terminal!  <br>
<br>
to run the current instance that's live right now, run this:  
`ssh -p 6767 termegle.sirbread.dev`  
and you're in! no downloading any binary required since it's an SSH server.  

## features
- tui based
- anon chat with strangers :)
- ssh into the server, no downloads needed
- interest tags: enter your interests on startup (comma-separated) for better matches
- - chat saving
- - but also save snitching
- colored messages (cyan for system, yellow for connections, red for strangers, blue for you)
- user count of how many are online
- see how many people you talked with
- rate limiting/idle kicking
- absolutley NO lazy loading (there's full screen refreshes every screen update)

## run ts
1. clone thy repo
2. install requirements.txt
3. run the python file with:  
   `python3 termegle_server.py`
4. in another terminal, SSH into localhost:  
   `ssh -p 6767 localhost`  
   and you're in!

## boring stuff
### credits
- omegle, of course, for the base idea
- myself for the idea of shoving it into a tui
- @csd4ni3l for convincing me not to scrap the project

### other 
ai was used _just a tiny bit_ in the `Matchmaker` class to sort out stranger priority systems

