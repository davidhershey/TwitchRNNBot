#!/usr/bin/env bash

# create and own the directories to store results locally
save_dir='saved_model/'
sudo mkdir -p $save_dir'/data/'
sudo mkdir -p $save_dir'/nn_models/'
sudo mkdir -p $save_dir'/results/'
sudo chown -R "$USER" $save_dir

# copy train and test data with proper naming
data_dir='tf_seq2seq_chatbot/data/train'
cp $data_dir'/toy.txt' $save_dir'/data/chat.in'
cp $data_dir'/toy_test.txt' $save_dir'/data/chat_test.in'

# build and install the tweaked Seq2Seq_Upgrade_TensorFlow package
cd $save_dir
cd Seq2Seq_Upgrade_TensorFlow
sudo python setup.py build & sudo python setup.py install
