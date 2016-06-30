#Much code directly from Google's TensorFlow


"""Library for creating sequence-to-sequence models."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf
import inspect


from rnn_enhancement import linear_enhanced as linear

# from tensorflow.models.rnn import rnn
# from tensorflow.models.rnn import rnn_cell

from rnn_enhancement import rnn_enhanced as rnn
from rnn_enhancement import rnn_cell_enhanced as rnn_cell

#Warning commenting the two lines below out allows it to work!
from rnn_enhancement import linear_functions_enhanced as lfe
from rnn_enhancement import decoding_enhanced


def average_hidden_states(decoder_states, average_hidden_state_influence = 0.5, name = None):
  print('WARNING YOU ARE USING HIDDEN STATES')
  with tf.op_scope(decoder_states + average_hidden_state_influence, name, "average_hidden_states"):
    mean_decoder_states = tf.reduce_mean(decoder_states, 0) #nick double check the axis is right!
    final_decoder_state = tf.add((1 - average_hidden_state_influence) * decoder_states[-1], average_hidden_state_influence*mean_decoder_states)
  return final_decoder_state




def attention_decoder(decoder_inputs, initial_state, attention_states, cell,
                      output_size=None, num_heads=1, loop_function=None,
                      dtype=tf.float32, scope=None, average_states = False, average_hidden_state_influence = 0.5,
                      temperature_decode = False, temperature = 1.0):
  """RNN decoder with attention for the sequence-to-sequence model.

  Args:
    decoder_inputs: a list of 2D Tensors [batch_size x cell.input_size].
    initial_state: 2D Tensor [batch_size x cell.state_size].
    attention_states: 3D Tensor [batch_size x attn_length x attn_size].
    cell: rnn_cell.RNNCell defining the cell function and size.
    output_size: size of the output vectors; if None, we use cell.output_size.
    num_heads: number of attention heads that read from attention_states.
    loop_function: if not None, this function will be applied to i-th output
      in order to generate i+1-th input, and decoder_inputs will be ignored,
      except for the first element ("GO" symbol). This can be used for decoding,
      but also for training to emulate http://arxiv.org/pdf/1506.03099v2.pdf.
      Signature -- loop_function(prev, i) = next
        * prev is a 2D Tensor of shape [batch_size x cell.output_size],
        * i is an integer, the step number (when advanced control is needed),
        * next is a 2D Tensor of shape [batch_size x cell.input_size].
    dtype: The dtype to use for the RNN initial state (default: tf.float32).
    scope: VariableScope for the created subgraph; default: "attention_decoder".

  Returns:
    outputs: A list of the same length as decoder_inputs of 2D Tensors of shape
      [batch_size x output_size]. These represent the generated outputs.
      Output i is computed from input i (which is either i-th decoder_inputs or
      loop_function(output {i-1}, i)) as follows. First, we run the cell
      on a combination of the input and previous attention masks:
        cell_output, new_state = cell(linear(input, prev_attn), prev_state)
      Then, we calculate new attention masks:
        new_attn = softmax(V^T * tanh(W * attention_states + U * new_state))
      and then we calculate the output:
        output = linear(cell_output, new_attn).
    states: The state of each decoder cell in each time-step. This is a list
      with length len(decoder_inputs) -- one item for each time-step.
      Each item is a 2D Tensor of shape [batch_size x cell.state_size].

  Raises:
    ValueError: when num_heads is not positive, there are no inputs, or shapes
      of attention_states are not set.
  """
  if not decoder_inputs:
    raise ValueError("Must provide at least 1 input to attention decoder.")
  if num_heads < 1:
    raise ValueError("With less than 1 heads, use a non-attention decoder.")
  if not attention_states.get_shape()[1:2].is_fully_defined():
    raise ValueError("Shape[1] and [2] of attention_states must be known: %s"
                     % attention_states.get_shape())
  if output_size is None:
    output_size = cell.output_size

  with tf.variable_scope(scope or "attention_decoder"):
    batch_size = tf.shape(decoder_inputs[0])[0]  # Needed for reshaping.
    attn_length = attention_states.get_shape()[1].value
    attn_size = attention_states.get_shape()[2].value

    # To calculate W1 * h_t we use a 1-by-1 convolution, need to reshape before.
    hidden = tf.reshape(attention_states, [-1, attn_length, 1, attn_size])
    hidden_features = []
    v = []
    attention_vec_size = attn_size  # Size of query vectors for attention.
    for a in xrange(num_heads):
      k = tf.get_variable("AttnW_%d" % a, [1, 1, attn_size, attention_vec_size])
      hidden_features.append(tf.nn.conv2d(hidden, k, [1, 1, 1, 1], "SAME"))
      v.append(tf.get_variable("AttnV_%d" % a, [attention_vec_size]))

    states = [initial_state]

    def attention(query): #this is part of the attention_decoder. It is placed outside to avoid re-compile time.
      """Put attention masks on hidden using hidden_features and query."""
      ds = []  # Results of attention reads will be stored here.
      for a in xrange(num_heads):
        with tf.variable_scope("Attention_%d" % a):
          y = linear.linear(query, attention_vec_size, True)
          y = tf.reshape(y, [-1, 1, 1, attention_vec_size])
          # Attention mask is a softmax of v^T * tanh(...).
          s = tf.reduce_sum(v[a] * tf.tanh(hidden_features[a] + y), [2, 3])
          a = tf.nn.softmax(s)
          # Now calculate the attention-weighted vector d.
          d = tf.reduce_sum(tf.reshape(a, [-1, attn_length, 1, 1]) * hidden,
                            [1, 2])
          ds.append(tf.reshape(d, [-1, attn_size]))
      return ds

    outputs = []
    wids = []
    prev = None
    batch_attn_size = tf.pack([batch_size, attn_size])
    attns = [tf.zeros(batch_attn_size, dtype=dtype)
             for _ in xrange(num_heads)]
    for a in attns:  # Ensure the second shape of attention vectors is set.
      a.set_shape([None, attn_size])
    for i in xrange(len(decoder_inputs)): #RIGHT HERE! THIS IS A LIST OF DECODING TIMESTEPS! WHAAAAHOOOOO!!!!
      if i > 0:
        tf.get_variable_scope().reuse_variables()
      inp = decoder_inputs[i]

      '''nick, you can implement sampling here by changing the input here! also curriculum learning too!'''
      # If loop_function is set, we use it instead of decoder_inputs.
      if loop_function is not None and prev is not None:
        with tf.variable_scope("loop_function", reuse=True):
          inp,wid = loop_function(prev, i, temperature_decode = temperature_decode,
                      temperature = temperature) #basically, stop_gradient doesn't allow inputs to be taken into account
          wids.append(wid)

      #this will make an input that is combined with attention


      # Merge input and previous attentions into one vector of the right size.
      x = linear.linear([inp] + attns, cell.input_size, True)


      hidden_state_input = states[-1]
      if average_states:
        '''implement averaging of states'''
        print('WARNING YOU HAVE OPTED TO USE THE AVERAGING OF STATES!')
        hidden_state_input = average_hidden_states(states, average_hidden_state_influence)

      # Run the RNN.

      #right here, you could potentially make the skip-connections? I think you would have to
      #you would have to save the output part here, and then transfer it to the next part.
      cell_output, new_state = cell(x, hidden_state_input) #nick, changed this to your hidden state input
      states.append(new_state)



      # Run the attention mechanism.
      attns = attention(new_state)
      with tf.variable_scope("AttnOutputProjection"):
        output = linear.linear([cell_output] + attns, output_size, True)
      if loop_function is not None:
        # We do not propagate gradients over the loop function.
        prev = tf.stop_gradient(output)
      outputs.append(output)


  return outputs, states,wids


def embedding_attention_decoder(decoder_inputs, initial_state, attention_states,
                                cell, num_symbols, num_heads=1,
                                output_size=None, output_projection=None,
                                feed_previous=False, dtype=tf.float32,
                                scope=None, average_states = False, average_hidden_state_influence = 0.5,
                                temperature_decode = False, temperature = 1.0):
  """RNN decoder with embedding and attention and a pure-decoding option.

  Args:
    decoder_inputs: a list of 1D batch-sized int32-Tensors (decoder inputs).
    initial_state: 2D Tensor [batch_size x cell.state_size].
    attention_states: 3D Tensor [batch_size x attn_length x attn_size].
    cell: rnn_cell.RNNCell defining the cell function.
    num_symbols: integer, how many symbols come into the embedding.
    num_heads: number of attention heads that read from attention_states.
    output_size: size of the output vectors; if None, use cell.output_size.
    output_projection: None or a pair (W, B) of output projection weights and
      biases; W has shape [output_size x num_symbols] and B has shape
      [num_symbols]; if provided and feed_previous=True, each fed previous
      output will first be multiplied by W and added B.
    feed_previous: Boolean; if True, only the first of decoder_inputs will be
      used (the "GO" symbol), and all other decoder inputs will be generated by:
        next = embedding_lookup(embedding, argmax(previous_output)),
      In effect, this implements a greedy decoder. It can also be used
      during training to emulate http://arxiv.org/pdf/1506.03099v2.pdf.
      If False, decoder_inputs are used as given (the standard decoder case).
    dtype: The dtype to use for the RNN initial states (default: tf.float32).
    scope: VariableScope for the created subgraph; defaults to
      "embedding_attention_decoder".

  Returns:
    outputs: A list of the same length as decoder_inputs of 2D Tensors with
      shape [batch_size x output_size] containing the generated outputs.
    states: The state of each decoder cell in each time-step. This is a list
      with length len(decoder_inputs) -- one item for each time-step.
      Each item is a 2D Tensor of shape [batch_size x cell.state_size].

  Raises:
    ValueError: when output_projection has the wrong shape.
  """
  if output_size is None:
    output_size = cell.output_size
  if output_projection is not None:
    proj_weights = tf.convert_to_tensor(output_projection[0], dtype=dtype)
    proj_weights.get_shape().assert_is_compatible_with([cell.output_size,
                                                        num_symbols])
    proj_biases = tf.convert_to_tensor(output_projection[1], dtype=dtype)
    proj_biases.get_shape().assert_is_compatible_with([num_symbols])

  with tf.variable_scope(scope or "embedding_attention_decoder"):
    with tf.device("/cpu:0"):
      embedding = tf.get_variable("embedding", [num_symbols, cell.input_size])




    loop_function = None
    if feed_previous:
      def extract_argmax_and_embed(prev, _, temperature_decode = False, temperature = 1.0): #placing this function here avoids re-compile time during training!
        """Loop_function that extracts the symbol from prev and embeds it."""
        if output_projection is not None:
          prev = tf.nn.xw_plus_b(prev, output_projection[0], output_projection[1])
        '''output prev of xw_plus_b is [batch_size x out_units]'''
        #this might be where you gotta do the sampling with temperature during decoding
        if temperature_decode:
          print('YOU ARE USING TEMPERATURE DECODING WARNING --- {}'.format(temperature))
          prev_symbol = tf.stop_gradient(decoding_enhanced.batch_sample_with_temperature(prev, temperature))
        else:
          prev_symbol = tf.stop_gradient(tf.argmax(prev, 1))
        #be careful of batch sizing here nick!
        emb_prev = tf.nn.embedding_lookup(embedding, prev_symbol) #this reconverts it to the embedding I believe
        return emb_prev,prev_symbol

      loop_function = extract_argmax_and_embed #oh wow they are literally passing a function right here....

    emb_inp = [tf.nn.embedding_lookup(embedding, i) for i in decoder_inputs]

    #this is making a list of all the embedded inputs

    return attention_decoder(
      emb_inp, initial_state, attention_states, cell, output_size=output_size,
      num_heads=num_heads, loop_function=loop_function, average_states = average_states,
      average_hidden_state_influence = average_hidden_state_influence, temperature_decode = temperature_decode,
      temperature = temperature)


def embedding_attention_seq2seq(encoder_inputs, decoder_inputs, cell,
                                num_encoder_symbols, num_decoder_symbols,
                                num_heads=1, output_projection=None,
                                feed_previous=False, dtype=tf.float32,
                                scope=None, average_states = False,
                                average_hidden_state_influence = 0.5, temperature_decode = False,
                                temperature = 1.0):
  """Embedding sequence-to-sequence model with attention.

  This model first embeds encoder_inputs by a newly created embedding (of shape
  [num_encoder_symbols x cell.input_size]). Then it runs an RNN to encode
  embedded encoder_inputs into a state vector. It keeps the outputs of this
  RNN at every step to use for attention later. Next, it embeds decoder_inputs
  by another newly created embedding (of shape [num_decoder_symbols x
  cell.input_size]). Then it runs attention decoder, initialized with the last
  encoder state, on embedded decoder_inputs and attending to encoder outputs.

  Args:
    encoder_inputs: a list of 2D Tensors [batch_size x cell.input_size].
    decoder_inputs: a list of 2D Tensors [batch_size x cell.input_size].
    cell: rnn_cell.RNNCell defining the cell function and size.
    num_encoder_symbols: integer; number of symbols on the encoder side.
    num_decoder_symbols: integer; number of symbols on the decoder side.
    num_heads: number of attention heads that read from attention_states.
    output_projection: None or a pair (W, B) of output projection weights and
      biases; W has shape [cell.output_size x num_decoder_symbols] and B has
      shape [num_decoder_symbols]; if provided and feed_previous=True, each
      fed previous output will first be multiplied by W and added B.
    feed_previous: Boolean or scalar Boolean Tensor; if True, only the first
      of decoder_inputs will be used (the "GO" symbol), and all other decoder
      inputs will be taken from previous outputs (as in embedding_rnn_decoder).
      If False, decoder_inputs are used as given (the standard decoder case).
    dtype: The dtype of the initial RNN state (default: tf.float32).
    scope: VariableScope for the created subgraph; defaults to
      "embedding_attention_seq2seq".

  Returns:
    outputs: A list of the same length as decoder_inputs of 2D Tensors with
      shape [batch_size x num_decoder_symbols] containing the generated outputs.

      notice nick, the list is the sequence length!!!!!!!

      so outputs is a 3d tensor total -- and it has te outputs batch size x 512


    states: The state of each decoder cell in each time-step. This is a list
      with length len(decoder_inputs) -- one item for each time-step.
      Each item is a 2D Tensor of shape [batch_size x cell.state_size].

      #definitely look at this -- this is also a 3d tensor
      each item has a 2d tensor and its shape is batch size
      times the state size of the cell -- so you're doing all the
      batches at once...okay...
  """
  with tf.variable_scope(scope or "embedding_attention_seq2seq"):
    # Encoder.
    encoder_cell = rnn_cell.EmbeddingWrapper(cell, num_encoder_symbols)
    encoder_outputs, encoder_states = rnn.rnn(
        encoder_cell, encoder_inputs, dtype=dtype)

    # First calculate a concatenation of encoder outputs to put attention on.
    top_states = [tf.reshape(e, [-1, 1, cell.output_size])
                  for e in encoder_outputs]
    attention_states = tf.concat(1, top_states)

    # Decoder.
    output_size = None
    if output_projection is None:
      #right here they modify the outputprojectionwrapper
      cell = rnn_cell.OutputProjectionWrapper(cell, num_decoder_symbols)
      output_size = num_decoder_symbols

    if isinstance(feed_previous, bool): #this is saying you are decoding, feed-forward network
      '''nick, right here, you will find a broad if statement'''

      return embedding_attention_decoder(
          decoder_inputs, encoder_states[-1], attention_states, cell,
          num_decoder_symbols, num_heads, output_size, output_projection,
          feed_previous, average_states = average_states, average_hidden_state_influence = average_hidden_state_influence,
          temperature_decode = temperature_decode, temperature = temperature)

    else:  # If feed_previous is a Tensor, we construct 2 graphs and use cond.
      '''nick, right here, you modify by doing a broad if statement'''


      outputs1, states1,wids = embedding_attention_decoder(
          decoder_inputs, encoder_states[-1], attention_states, cell,
          num_decoder_symbols, num_heads, output_size, output_projection, True,
          average_states = average_states,
          average_hidden_state_influence = average_hidden_state_influence,
          temperature_decode = temperature_decode, temperature = temperature)
      tf.get_variable_scope().reuse_variables()
      outputs2, states2,wids = embedding_attention_decoder(
          decoder_inputs, encoder_states[-1], attention_states, cell,
          num_decoder_symbols, num_heads, output_size, output_projection, False,
          average_states = average_states,
          average_hidden_state_influence = average_hidden_state_influence,
          temperature_decode = temperature_decode, temperature = temperature)

      outputs = tf.control_flow_ops.cond(feed_previous,
                                         lambda: outputs1, lambda: outputs2)
      states = tf.control_flow_ops.cond(feed_previous,
                                      lambda: states1, lambda: states2)


      return outputs, states,wids


def sequence_loss_by_example(logits, targets, weights, num_decoder_symbols,
                             average_across_timesteps=True,
                             softmax_loss_function=None, name=None):
  """Weighted cross-entropy loss for a sequence of logits (per example).

  Args:
    logits: list of 2D Tensors of shape [batch_size x num_decoder_symbols]. nick logits are 2d tensors
    targets: list of 1D batch-sized int32-Tensors of the same length as logits.
    weights: list of 1D batch-sized float-Tensors of the same length as logits.
    num_decoder_symbols: integer, number of decoder symbols (output classes).
    average_across_timesteps: If set, divide the returned cost by the total
      label weight.
    softmax_loss_function: function (inputs-batch, labels-batch) -> loss-batch
      to be used instead of the standard softmax (the default if this is None).
    name: optional name for this operation, default: "sequence_loss_by_example".

  Returns:
    1D batch-sized float Tensor: the log-perplexity for each sequence.
    notice here they take the ln(perplexity) -- which is why you get loss as you do

  Raises:
    ValueError: if len(logits) is different from len(targets) or len(weights).
  """
  if len(targets) != len(logits) or len(weights) != len(logits):
    raise ValueError("Lengths of logits, weights, and targets must be the same "
                     "%d, %d, %d." % (len(logits), len(weights), len(targets)))
  with tf.op_scope(logits + targets + weights, name,
                   "sequence_loss_by_example"):
    batch_size = tf.shape(targets[0])[0]
    log_perp_list = []
    length = batch_size * num_decoder_symbols #this represents the batch size x vocab size
    for i in xrange(len(logits)):
      if softmax_loss_function is None:
        # TODO(lukaszkaiser): There is no SparseCrossEntropy in TensorFlow, so
        # we need to first cast targets into a dense representation, and as
        # SparseToDense does not accept batched inputs, we need to do this by
        # re-indexing and re-sizing. When TensorFlow adds SparseCrossEntropy,
        # rewrite this method.
        indices = targets[i] + num_decoder_symbols * tf.range(batch_size)
        with tf.device("/cpu:0"):  # Sparse-to-dense must happen on CPU for now.
          dense = tf.sparse_to_dense(indices, tf.expand_dims(length, 0), 1.0,
                                     0.0)
        target = tf.reshape(dense, [-1, num_decoder_symbols])
        crossent = tf.nn.softmax_cross_entropy_with_logits(
            logits[i], target, name="SequenceLoss/CrossEntropy{0}".format(i))
      else:
        crossent = softmax_loss_function(logits[i], targets[i])

      log_perp_list.append(crossent * weights[i]) #this determines the cost I think?

    log_perps = tf.add_n(log_perp_list) #this adds all the elements in the tensor together
    if average_across_timesteps:
      total_size = tf.add_n(weights) #nick, this adds element wise all the of weights -- this produces just one number!
      total_size += 1e-12  # Just to avoid division by 0 for all-0 weights. This is adding it to just one number! total_size = total_size + 1e-12
      log_perps /= total_size #one number is produced here! this is equivalent to log_perps = log_perps/total_size
  return log_perps #this is the natural log of your perplexity


def sequence_loss(logits, targets, weights, num_decoder_symbols,
                  average_across_timesteps=True, average_across_batch=True,
                  softmax_loss_function=None, name=None):
  """Weighted cross-entropy loss for a sequence of logits, batch-collapsed.

  Args:
    logits: list of 2D Tensors os shape [batch_size x num_decoder_symbols].
    targets: list of 1D batch-sized int32-Tensors of the same length as logits.
    weights: list of 1D batch-sized float-Tensors of the same length as logits.
    num_decoder_symbols: integer, number of decoder symbols (output classes).
    average_across_timesteps: If set, divide the returned cost by the total
      label weight.
    average_across_batch: If set, divide the returned cost by the batch size.
    softmax_loss_function: function (inputs-batch, labels-batch) -> loss-batch
      to be used instead of the standard softmax (the default if this is None).
    name: optional name for this operation, defaults to "sequence_loss".

  Returns:
    A scalar float Tensor: the average log-perplexity per symbol (weighted).

  Raises:
    ValueError: if len(logits) is different from len(targets) or len(weights).
  """
  with tf.op_scope(logits + targets + weights, name, "sequence_loss"): #notice how they make a list for values
  #this basically assures that entire operature occurs as one point in the graph -- really useful.
    '''reduce sum adds all of the elements in tensor to a single value'''
    cost = tf.reduce_sum(sequence_loss_by_example(
          logits, targets, weights, num_decoder_symbols,
          average_across_timesteps=average_across_timesteps,
          softmax_loss_function=softmax_loss_function))

    if average_across_batch:
      batch_size = tf.shape(targets[0])[0]
      return cost / tf.cast(batch_size, tf.float32) #cast makes the numbers in a certain formats.
    else:
      return cost


def norm_stabilizer_loss(logits_to_normalize, norm_regularizer_factor = 50, name = None):


  print('WARNING ------YOU HAVE OPTED TO USE NORM STABILIZER LOSS -------------------------------')
  '''Will add a Norm Stabilizer Loss

    Args:
  logits_to_normalize:This can be output logits or hidden states. The state of each decoder cell in each time-step. This is a list
    with length len(decoder_inputs) -- one item for each time-step.
    Each item is a 2D Tensor of shape [batch_size x cell.state_size] (or it can be [batch_size x output_logits])

  norm_regularizer_factor: The factor required to apply norm stabilization. Keep
    in mind that a larger factor will allow you to achieve a lower loss, but it will take
    many more epochs to do so!

    Returns:
  final_reg_loss: One Scalar Value representing the loss averaged across the batch'''

  with tf.op_scope(logits_to_normalize, name, "norm_stabilizer_loss"): #need to have this for tf to work
    batch_size = tf.shape(logits_to_normalize[0])[0] #you choose the batch size number -- this makes a tensor

    squared_sum = tf.zeros_like(batch_size,dtype = tf.float32) #batch size in zeros
    for q in xrange(len(logits_to_normalize)-1): #this represents the summation part from t to T
      '''one problem you're having right now is that you can't take the sqrt of negative number...you need to figure this out first

      You need to take the euclidean norm of the value -- can't find how to do this in tf....

      okay so Amn matrix means that the m is going down and n is going horizontal -- so we choose to reduce sum on axis 1 '''
      difference = tf.sub(lfe.frobenius_norm(logits_to_normalize[q+1], reduction_indices = 1),
              lfe.frobenius_norm(logits_to_normalize[q], reduction_indices = 1))

      '''the difference has the dimensions of [batch_size]'''
      squared_sum = tf.add(squared_sum, tf.square(difference))

    #We want to average across batch sizes and divide by T
    batch_size_times_len_logits = len(logits_to_normalize)*tf.to_float(batch_size)


    final_reg_loss = norm_regularizer_factor*(tf.reduce_sum(squared_sum))/batch_size_times_len_logits
    #i think currently the problem right now is that this is returning an array rather than a number scalar
  return final_reg_loss

def l1_orthogonal_regularizer(logits_to_normalize, l1_alpha_loss_factor = 10, name = None):

  '''Motivation from this loss function comes from: https://redd.it/3wx4sr
  Specifically want to thank spurious_recollectio and harponen on reddit for discussing this suggestion to me '''

  '''Will add a L1 Loss linearly to the softmax cost function.


    Returns:
  final_reg_loss: One Scalar Value representing the loss averaged across the batch'''

  '''this is different than unitary because it is an orthongonal matrix approximation -- it will
  suffer from timesteps longer than 500 and will take more computation power of O(n^3)'''

  with tf.op_scope(logits_to_normalize, name, "rnn_l2_loss"): #need to have this for tf to work

    '''the l1 equation is: alpha * T.abs(T.dot(W, W.T) - (1.05) ** 2 * T.identity_like(W))'''
    Weights_for_l1_loss = tf.get_variable("linear")

    matrix_dot_product= tf.matmul(Weights_for_l1_loss, Weights_for_l1_loss, transpose_a = True)

    #we need to check here that we have the right dimension -- should it be 0 or the 1 dim?
    identity_matrix = lfe.identity_like(Weights_for_l1_loss)

    matrix_minus_identity = matrix_dot_product - 2*1.05*identity_matrix

    absolute_cost = tf.abs(matrix_minus_identity)

    final_l1_loss = l1_alpha_loss_factor*(absolute_cost/batch_size)

  return final_l1_loss

def l2_orthogonal_regularizer(logits_to_normalize, l2_alpha_loss_factor = 10, name = None):

  '''Motivation from this loss function comes from: https://www.reddit.com/r/MachineLearning/comments/3uk2q5/151106464_unitary_evolution_recurrent_neural/
  Specifically want to thank spurious_recollectio on reddit for discussing this suggestion to me '''

  '''Will add a L2 Loss linearly to the softmax cost function.


    Returns:
  final_reg_loss: One Scalar Value representing the loss averaged across the batch'''

  '''this is different than unitary because it is an orthongonal matrix approximation -- it will
  suffer from timesteps longer than 500 and will take more computation power of O(n^3)'''

  with tf.op_scope(logits_to_normalize, name, "rnn_l2_loss"): #need to have this for tf to work

    '''somehow we need to get the Weights from the rnns right here....i don't know how! '''
    '''the l1 equation is: alpha * T.abs(T.dot(W, W.T) - (1.05) ** 2 * T.identity_like(W))'''
    '''The Equation of the Cost Is: loss += alpha * T.sum((T.dot(W, W.T) - (1.05)*2 T.identity_like(W)) * 2)'''
    Weights_for_l2_loss = tf.get_variable("linear")

    matrix_dot_product= tf.matmul(Weights_for_l2_loss, Weights_for_l2_loss, transpose_a = True)

    #we need to check here that we have the right dimension -- should it be 0 or the 1 dim?
    identity_matrix = lfe.identity_like(Weights_for_l2_loss)

    matrix_minus_identity = matrix_dot_product - 2*1.05*identity_matrix

    square_the_loss = tf.square(matrix_minus_identity)

    final_l2_loss = l2_alpha_loss_factor*(tf.reduce_sum(square_the_loss)/(batch_size))
  return final_l2_loss


def model_with_buckets(encoder_inputs, decoder_inputs, targets, weights,
                       buckets, num_decoder_symbols, seq2seq,
                       softmax_loss_function=None, name=None, norm_regularize_hidden_states = False,
                       norm_regularize_logits = False, norm_regularizer_factor = 50,
                       apply_l2_loss = False, l2_loss_factor = 5):
  """Create a sequence-to-sequence model with support for bucketing.

  The seq2seq argument is a function that defines a sequence-to-sequence model,
  e.g., seq2seq = lambda x, y: basic_rnn_seq2seq(x, y, rnn_cell.GRUCell(24))

  Args:
    encoder_inputs: a list of Tensors to feed the encoder; first seq2seq input.
    decoder_inputs: a list of Tensors to feed the decoder; second seq2seq input.
    targets: a list of 1D batch-sized int32-Tensors (desired output sequence).
    weights: list of 1D batch-sized float-Tensors to weight the targets.
    buckets: a list of pairs of (input size, output size) for each bucket.
    num_decoder_symbols: integer, number of decoder symbols (output classes).
    seq2seq: a sequence-to-sequence model function; it takes 2 input that
      agree with encoder_inputs and decoder_inputs, and returns a pair
      consisting of outputs and states (as, e.g., basic_rnn_seq2seq).
    softmax_loss_function: function (inputs-batch, labels-batch) -> loss-batch
      to be used instead of the standard softmax (the default if this is None).
    name: optional name for this operation, defaults to "model_with_buckets".

  Returns:
    outputs: The outputs for each bucket. Its j'th element consists of a list
      of 2D Tensors of shape [batch_size x num_decoder_symbols] (j'th outputs).
    losses: List of scalar Tensors, representing losses for each bucket.
  Raises:
    ValueError: if length of encoder_inputsut, targets, or weights is smaller
      than the largest (last) bucket.
  """
  if len(encoder_inputs) < buckets[-1][0]:
    raise ValueError("Length of encoder_inputs (%d) must be at least that of la"
                     "st bucket (%d)." % (len(encoder_inputs), buckets[-1][0]))
  if len(targets) < buckets[-1][1]:
    raise ValueError("Length of targets (%d) must be at least that of last"
                     "bucket (%d)." % (len(targets), buckets[-1][1]))
  if len(weights) < buckets[-1][1]:
    raise ValueError("Length of weights (%d) must be at least that of last"
                     "bucket (%d)." % (len(weights), buckets[-1][1]))

  all_inputs = encoder_inputs + decoder_inputs + targets + weights
  losses = []
  outputs = []
  wids = []
  out_hidden_states = [] #nick added this
  with tf.op_scope(all_inputs, name, "model_with_buckets"):
    for j in xrange(len(buckets)):
      if j > 0:
        tf.get_variable_scope().reuse_variables()
      bucket_encoder_inputs = [encoder_inputs[i]
                               for i in xrange(buckets[j][0])]
      bucket_decoder_inputs = [decoder_inputs[i]
                               for i in xrange(buckets[j][1])]
      bucket_outputs, bucket_states, bucket_wids= seq2seq(bucket_encoder_inputs,
                                  bucket_decoder_inputs) #nick pay attention here -- you added bucket_states
      outputs.append(bucket_outputs)
      wids.append(bucket_wids)

      bucket_targets = [targets[i] for i in xrange(buckets[j][1])]
      bucket_weights = [weights[i] for i in xrange(buckets[j][1])]


      '''CALCULATE NORM REGULARIZE LOSS HERE'''
      final_reg_loss = 0
      if norm_regularize_hidden_states:
        print('Warning -- You have opted to Use Norm Regularize Hidden States. Your Regularizer factor is:', norm_regularizer_factor)
        final_reg_loss = norm_stabilizer_loss(bucket_states, norm_regularizer_factor = norm_regularizer_factor)
      if norm_regularize_logits:
        final_reg_loss += norm_stabilizer_loss(bucket_outputs, norm_regularizer_factor = norm_regularizer_factor)
        print('Warning -- You have opted to Use Norm Regularize Input Logits. Your Regularizer factor is:', norm_regularizer_factor)
      if apply_l2_loss:
        final_reg_loss += rnn_l2_loss(l2_loss_factor = l2_loss_factor)
        print('Warning -- You have opted to Use RNN L2 Orthongonal Loss, Your Scaling factor is:', l2_loss_factor)


      losses.append(final_reg_loss + sequence_loss(
          outputs[-1], bucket_targets, bucket_weights, num_decoder_symbols,
          softmax_loss_function=softmax_loss_function))

  return outputs, losses,wids

  #THE LOSSES is just for bucket listing! so you can add the losses together

  '''outputs are considered logits, and the -1 gives a list of logits for that one bucket!'''
