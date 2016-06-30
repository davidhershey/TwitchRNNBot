# cfg.py
HOST = "irc.twitch.tv"              # the Twitch IRC server
PORT = 6667                         # always use port 6667!
NICK = ""            # your Twitch username, lowercase
PASS = "" # your Twitch OAuth token, eg oauth:xxxxxxxxxxxxxxxxxxxxxxxxx
CHAN = ""                   # the channel you want to join, eg #nl_kripp

if NICK == "" or PASS == "" or CHAN == "":
    print "Please add account and channel info to tf_seq2seq_chatbot/lib/cfg.py"
    exit(-1)
