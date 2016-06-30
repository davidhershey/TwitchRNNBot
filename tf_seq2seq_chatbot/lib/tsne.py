import os
import sys
import socket
import re
import numpy as np
# network functions go here

import tensorflow as tf
from time import sleep
import collections
import matplotlib.pyplot as plt

from tf_seq2seq_chatbot.configs.config import FLAGS
from tf_seq2seq_chatbot.lib import data_utils
from tf_seq2seq_chatbot.lib.seq2seq_model_utils import create_model, _get_predicted_sentence

emotes = [":)",":(","4Head","AMPEnergy","AMPEnergyCherry","ANELE","ArgieB8","ArsonNoSexy","AsianGlow","AthenaPMS","BabyRage","BatChest","BCouch","BCWarrior","BibleThump","BiersDerp","BigBrother","BionicBunion","BlargNaut","bleedPurple","BloodTrail","BORT","BrainSlug","BrokeBack","BudBlast","BuddhaBar","BudStar","ChefFrank","cmonBruh","CoolCat","CorgiDerp","CougarHunt","DAESuppy","DalLOVE","DansGame","DatSheffy","DBstyle","deExcite","deIlluminati","DendiFace","DogFace","DOOMGuy","duDudu","EagleEye","EleGiggle","FailFish","FPSMarksman","FrankerZ","FreakinStinkin","FUNgineer","FunRun","FutureMan","FuzzyOtterOO","GingerPower","GrammarKing","HassaanChop","HassanChop","HeyGuys","HotPokket","HumbleLife","ItsBoshyTime","Jebaited","JKanStyle","JonCarnage","KAPOW","Kappa","KappaClaus","KappaPride","KappaRoss","KappaWealth","Keepo","KevinTurtle","Kippa","Kreygasm","Mau5","mcaT","MikeHogu","MingLee","MrDestructoid","MVGame","NinjaTroll","NomNom","NoNoSpot","NotATK","NotLikeThis","OhMyDog","OMGScoots","OneHand","OpieOP","OptimizePrime","OSfrog","OSkomodo","OSsloth","panicBasket","PanicVis","PartyTime","PazPazowitz","PeoplesChamp","PermaSmug","PeteZaroll","PeteZarollTie","PicoMause","PipeHype","PJSalt","PMSTwin","PogChamp","Poooound","PraiseIt","PRChase","PunchTrees","PuppeyFace","RaccAttack","RalpherZ","RedCoat","ResidentSleeper","riPepperonis","RitzMitz","RuleFive","SeemsGood","ShadyLulu","ShazBotstix","ShibeZ","SmoocherZ","SMOrc","SMSkull","SoBayed","SoonerLater","SriHead","SSSsss","StinkyCheese","StoneLightning","StrawBeary","SuperVinlin","SwiftRage","TBCheesePull","TBTacoLeft","TBTacoRight","TF2John","TheRinger","TheTarFu","TheThing","ThunBeast","TinyFace","TooSpicy","TriHard","TTours","twitchRaid","UleetBackup","UncleNox","UnSane","VaultBoy","VoHiYo","Volcania","WholeWheat","WinWaker","WTRuck","WutFace","YouWHY"]

words = ["sad","BibleThump","rekt","PogChamp","GG","Kreygasm","WOW"]

def plot_with_labels(low_dim_embs, labels, filename='tsne.png'):
  assert low_dim_embs.shape[0] >= len(labels), "More labels than embeddings"
  plt.figure(figsize=(18, 18))  #in inches
  for i, label in enumerate(labels):
    x, y = low_dim_embs[i,:]
    plt.scatter(x, y)
    plt.annotate(label.decode('utf-8','ignore'),
                 xy=(x, y),
                 xytext=(5, 2),
                 textcoords='offset points',
                 ha='right',
                 va='bottom')

  plt.savefig(filename)

def tsne():
  with tf.Session() as sess:
    # Create model and load parameters.
    from sklearn import manifold

    vocab_path = os.path.join(FLAGS.data_dir, "vocab%d.in" % FLAGS.vocab_size)

    vocab, rev_vocab = data_utils.initialize_vocabulary(vocab_path)
    # labels = []
    # rows = []
    # for emote in words:
    #     if emote in vocab:
    #         labels.append(emote)
    #         rows.append(vocab[emote])
    rows = [i for i in xrange(500)]
    labels = [rev_vocab[i] for i in xrange(500)]
    # labels = emotes
    tsne = manifold.TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)

    model = create_model(sess, forward_only=True)
    model.batch_size = 1  # We decode one sentence at a time.
    embeddings = tf.get_variable("embedding_attention_seq2seq/embedding_attention_decoder/embedding")
    reduced_embeddings = tf.gather(embeddings,rows)
    num_embeddings = reduced_embeddings.eval()
    print num_embeddings.shape
    low_dim_embs = tsne.fit_transform(num_embeddings)
    plot_with_labels(low_dim_embs, labels)
