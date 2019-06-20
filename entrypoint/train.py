import pickle

import tensorflow as tf
from p2m.models.gcn import GCN
import numpy as np

# Set random seed
from p2m.utils import construct_feed_dict


if __name__ == "__main__":
    seed = 1024
    np.random.seed(seed)
    tf.set_random_seed(seed)

    # Define placeholders(dict) and model
    num_blocks = 3
    num_supports = 2
    placeholders = {
        'features': tf.placeholder(tf.float32, shape=(None, 3)),
        'img_inp': tf.placeholder(tf.float32, shape=(224, 224, 3)),
        'labels': tf.placeholder(tf.float32, shape=(None, 6)),
        'support1': [tf.sparse_placeholder(tf.float32) for _ in range(num_supports)],
        'support2': [tf.sparse_placeholder(tf.float32) for _ in range(num_supports)],
        'support3': [tf.sparse_placeholder(tf.float32) for _ in range(num_supports)],
        'faces': [tf.placeholder(tf.int32, shape=(None, 4)) for _ in range(num_blocks)],  # for face loss, not used.
        'edges': [tf.placeholder(tf.int32, shape=(None, 2)) for _ in range(num_blocks)],
        'lape_idx': [tf.placeholder(tf.int32, shape=(None, 10)) for _ in range(num_blocks)],  # for laplace term
        'pool_idx': [tf.placeholder(tf.int32, shape=(None, 2)) for _ in range(num_blocks - 1)]  # for unpooling
    }
    model = GCN(placeholders, logging=True)

    # Load data, initialize session
    data = DataFetcher(FLAGS.data_list)
    data.setDaemon(True)  ####
    data.start()
    config = tf.ConfigProto()
    # config.gpu_options.allow_growth=True
    config.allow_soft_placement = True
    sess = tf.Session(config=config)
    sess.run(tf.global_variables_initializer())
    # model.load(sess)

    # Train graph model
    train_loss = open('record_train_loss.txt', 'a')
    train_loss.write('Start training, lr =  %f\n' % (FLAGS.learning_rate))
    with open('Data/ellipsoid/info_ellipsoid.dat', 'rb') as info_ellipsoid:
        pkl = pickle.load(info_ellipsoid)
    feed_dict = construct_feed_dict(pkl, placeholders)

    train_number = data.number
    for epoch in range(FLAGS.epochs):
        all_loss = np.zeros(train_number, dtype='float32')
        print("Epoch %d, expected total iters = %d" % (epoch + 1, train_number))
        for iters in range(train_number):
            # Fetch training data
            img_inp, y_train, data_id = data.fetch()
            feed_dict.update({placeholders['img_inp']: img_inp})
            feed_dict.update({placeholders['labels']: y_train})

            # Training step
            _, dists, out1, out2, out3 = sess.run([model.opt_op, model.loss, model.output1, model.output2, model.output3],
                                                  feed_dict=feed_dict)
            all_loss[iters] = dists
            mean_loss = np.mean(all_loss[np.where(all_loss)])
            if (iters + 1) % 128 == 0:
                print('Epoch %d, Iteration %d' % (epoch + 1, iters + 1))
                print('Mean loss = %f, iter loss = %f, %d' % (mean_loss, dists, data.queue.qsize()))
                sys.stdout.flush()
        # Save model
        model.save(sess)
        train_loss.write('Epoch %d, loss %f\n' % (epoch + 1, mean_loss))
        train_loss.flush()

    data.shutdown()
    print('Training Finished!')
