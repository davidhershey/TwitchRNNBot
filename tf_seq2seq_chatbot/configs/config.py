import tensorflow as tf

TEST_DATASET_PATH = 'data/test/test_set.txt'
SAVE_DATA_DIR = 'saved_model/'

tf.app.flags.DEFINE_string('data_dir', SAVE_DATA_DIR + 'data', 'Data directory')
tf.app.flags.DEFINE_string('model_dir', SAVE_DATA_DIR + 'nn_models', 'Train directory')
tf.app.flags.DEFINE_string('summary_dir', SAVE_DATA_DIR + 'logs', 'Train directory')
tf.app.flags.DEFINE_string('results_dir', SAVE_DATA_DIR + 'results', 'Train directory')

tf.app.flags.DEFINE_float('learning_rate', 0.5, 'Learning rate.')
tf.app.flags.DEFINE_float('learning_rate_decay_factor', 0.99, 'Learning rate decays by this much.')
tf.app.flags.DEFINE_float('max_gradient_norm', 5.0, 'Clip gradients to this norm.')
tf.app.flags.DEFINE_integer('batch_size', 128, 'Batch size to use during training.')
tf.app.flags.DEFINE_float('temperature',10.0,'Temperature')

tf.app.flags.DEFINE_integer('vocab_size', 80000, 'Dialog vocabulary size.')
tf.app.flags.DEFINE_integer('size', 2048, 'Size of each model layer.')
tf.app.flags.DEFINE_integer('num_layers', 4, 'Number of layers in the model.')

tf.app.flags.DEFINE_integer('max_train_data_size', 0, 'Limit on the size of training data (0: no limit).')
tf.app.flags.DEFINE_integer('steps_per_checkpoint', 100, 'How many training steps to do per checkpoint.')

FLAGS = tf.app.flags.FLAGS

# We use a number of buckets and pad to the closest one for efficiency.
# See seq2seq_model.Seq2SeqModel for details of how they work.
BUCKETS = [(15, 20), (40, 25), (100, 50), (140, 80)]
