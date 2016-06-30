# bot.py
from tf_seq2seq_chatbot.lib import cfg
import socket

def send_chat(sock, msg):
    """
    Send a chat message to the server.
    Keyword arguments:
    sock -- the socket over which to send the message
    msg  -- the message to be sent
    """
    sock.send("PRIVMSG {} :{}\r\n".format(cfg.CHAN, msg))
