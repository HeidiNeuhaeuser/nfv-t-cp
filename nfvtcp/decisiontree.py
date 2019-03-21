import logging
import os
import numpy as np
import random
import heapq

LOG = logging.getLogger(os.path.basename(__file__))


class Node:
    """
    Base Class for Decision Tree Nodes.
    """

    def __init__(self, params, features, target, depth):
        # Todo: Delete feature/target/params if node is no leaf no save memory? (Can be recalculated for pruning)

        self.parameters = params  # list of dicts with values a vnf can have
        self.features = features  # configuration values
        self.target = target  # performance values
        self.left = None
        self.right = None
        self.depth = depth
        self.split_feature_index = None
        self.split_feature_cut_val = None
        self.split_improvement = 0.0
        self.pred_value = np.mean(target)
        self.error = None  # deviation from prediction. Smaller = better
        self.partition_size = None  # number of configs in partition
        self.score = None

    def calculate_partition_size(self):
        p = self.parameters
        res = 1
        for dict in p:
            for key in dict.keys():
                res *= len(dict.get(key))

        self.partition_size = res

    def set_error(self, h):
        self.error = h

    def calculate_score(self, weight_size):
        # (re)calculate parition size, adjusted after sampling
        self.calculate_partition_size()
        # Todo: should be relative, i.e. error/max_error, size/max_size or config space size?
        weight_error = 1 - weight_size
        self.score = weight_error * self.error + weight_size * self.partition_size


class DecisionTree:
    """
    Decision Tree Base Class.
    """

    def __init__(self, configs, parameters, features, target, regression='default', error_metric='mse',
                 min_error_gain=0.05, max_depth=None, weight_size=0.3, min_samples_split=2, max_features_split=1.0):

        self.vnf_count = None
        self.feature_idx_to_name = {}
        self._root = None
        self._depth = 1
        self.leaf_nodes = []  # needed for selection of node to sample, heapq heap of node scores
        self.max_depth = ((2 ** 31) - 1 if max_depth is None else max_depth)
        self.regression = regression  # default DT, oblique, svm?
        self.error_metric = error_metric
        self.config_space = configs  # should also be flat
        self.min_samples_split = min_samples_split  # minimum number of samples a node needs to have for split
        self.min_error_gain = min_error_gain  # minimum improvement to do a split
        self.regression = regression
        self.min_samples_leaf = 1   # minimum required number of samples within one leaf
        self.max_features_split = max_features_split # consider only 30-40% of features for split search?
        self.weight_size = weight_size
        self.last_sampled_node = None

        self._prepare_tree(parameters, features, target)

    def _prepare_tree(self, parameters, features, target):
        """
        Set root node, VNF count and Feature-index-to-name dictionary.
        """
        self.vnf_count = features.shape[1] // len(parameters)

        params = [parameters]
        if self.vnf_count != len(params):
            # if vnf_count is bigger than 1, append parameter dictionary for each vnf
            for vnf in range(1, self.vnf_count):
                params.append(parameters)

        index = 0
        for vnf in range(len(params)):
            for key in params[vnf].keys():
                self.feature_idx_to_name[index] = (vnf, key)
                index += 1

        self._root = Node(params, features, target, depth=1)
        LOG.info("Decision Tree Model initialized.")

    def _grow_tree_at_node(self, node):
        """
        Grow (sub)tree until defined termination definition is reached. Initially called for root node
        """
        if node.depth == self.max_depth or len(node.target) < self.min_samples_split:
            return  # stop growing

        if self.regression == 'default':
            self._determine_best_split_of_node(node)
        elif self.regression == 'oblique':
            # Todo: simulated annealing? (statt x < 2, e.g. 2x + y > 3)
            LOG.error("DT Regression technique '{}‘ not yet supported.".format(str(self.regression)))
            LOG.error("Exit!")
            exit(1)
        else:
            # Todo: support more regression= split ways, e.g. svm?
            LOG.error("DT Regression technique '{}‘ not supported.".format(str(self.regression)))
            LOG.error("Exit!")
            exit(1)

        if node.split_improvement < self.min_error_gain:
            return  # stop growing

        self._split_node(node)

        # depth first approach, does it matter?
        self._grow_tree_at_node(node.left)
        self._grow_tree_at_node(node.right)

    def _determine_best_split_of_node(self, node):
        """
        Given a node, determine the best feature and the best feature value to split the node.
        Error improvement, best feature and split value are set in the node object.
        """
        if node.error is None:
            node.set_error(self._calculate_node_error(node.target))
        feature_count = node.features.shape[1]
        sample_count = node.features.shape[0]

        # Todo: only evaluate 40% of features?
        for col in range(feature_count):
            # get all unique values for this feature in current node
            feature_vals = np.unique(node.features[:, col])
            # get all possible cuts for that feature (mean of two possible values) - assumes that features are sorted!
            cuts = (feature_vals[:-1] + feature_vals[1:]) / 2.0

            for cut in cuts:
                target_left_partition = node.target[node.features[:, col] <= cut]
                target_right_partition = node.target[node.features[:, col] > cut]

                error_left_partition = self._calculate_node_error(target_left_partition)
                error_right_partition = self._calculate_node_error(target_right_partition)

                left_percentage = float(target_left_partition.shape[0]) / sample_count
                right_percentage = 1 - left_percentage

                error_split = left_percentage * error_left_partition + right_percentage * error_right_partition
                error_improvement = node.error - error_split
                if error_improvement > node.split_improvement:
                    node.split_improvement = error_improvement
                    node.split_feature_index = col
                    node.split_feature_cut_val = cut

    def _split_node(self, node):
        """
        Split tree at given (leaf) node according to its defined split-feature und split-threshold value.
        Create two new leaf nodes with adjusted parameter, feature and target values.
        """
        # get all rows where the split value is less or equal than threshold and grow left node
        left_features = node.features[node.features[:, node.split_feature_index] <= node.split_feature_cut_val]
        left_target = node.target[node.features[:, node.split_feature_index] <= node.split_feature_cut_val]
        node.left = Node(None, left_features, left_target, node.depth + 1)

        # get all rows where the split value is greater than threshold and grow right node
        right_features = node.features[node.features[:, node.split_feature_index] > node.split_feature_cut_val]
        right_target = node.target[node.features[:, node.split_feature_index] > node.split_feature_cut_val]
        node.right = Node(None, right_features, right_target, node.depth + 1)
        # Todo: recalculate param intervals, divide by vnf_count

        if node.depth + 1 > self._depth:
            self._depth = node.depth + 1

        # unset leaf node flag
        node.set_decision_node()

        # calculate error for child nodes
        node.left.set_error(self._calculate_node_error(node.left.target))
        node.right.set_error(self._calculate_node_error(node.right.target))

        # calculate score for child nodes
        node.left.calculate_score(self.weight_size)
        node.right.calculate_score(self.weight_size)

        # add child nodes to leaf-node heap
        heapq.heappush(self.leaf_nodes, (node.left.score, node.left))
        heapq.heappush(self.leaf_nodes, (node.right.score, node.right))

    def _adjust_parameters(self, params, param_index, cut_value):
        """
        Return two adjusted parameter arrays that remove parameter values below/above cut_value.
        """
        # Todo: check jupyter
        pass

    def _calculate_node_error(self, target):
        """
        Calculate the error value of a given node according to homogeneity metric (self.homog_metric)
        """
        # Todo: more? Std deviation?
        if self.error_metric == 'var-reduction':  # same as mse? Lowest value = best
            # for each target in node, calculate error value from predicted node
            return np.mean((target - np.mean(target)) ** 2.0)

    def _determine_node_to_sample(self):
        # Todo: find node with lowest accuracy/homogeneity and biggest partition size and not at max-depth! --> heapq aber *(-1) da min heap
        if not self.leaf_nodes:
            LOG.error("Decision Tree model has no leaf nodes to sample.")
            LOG.error("Exit programme!")
            exit(1)

        # remove node from heap, will be split (push new score necessary?) upon call of "adapt_tree"
        next_node = heapq.heappop(self.leaf_nodes)[1]
        while self.leaf_nodes and (next_node.split_feature_index is not None or next_node.depth == self.max_depth):
            next_node = heapq.heappop(self.leaf_nodes)[1]

        if next_node.split_feature_index is not None or next_node.depth == self.max_depth:
            LOG.debug("Decision Tree has reached its maximum depth.")

        self.last_sampled_node = next_node
        return next_node

    def _get_config_from_partition(self, node):
        """
        Given the node to sample from, randomly select a configuration from the node's partition.
        Selection done by randomly choosing parameter values within the node's parameter thresholds.

        Config format should be: ({'c1': 1, 'c2': 1, 'c3': 1}, {'c1': 1, 'c2': 1, 'c3': 1})
        """
        c = []
        for dict in node.parameters:
            vnf = {}
            for param in dict.keys():
                vnf[param] = random.choice(dict.get(param))
            c.append(vnf)

        return tuple(c)

    def select_next(self):
        """
        Return next configuration to be profiled.
        """
        next_node = self._determine_node_to_sample()
        config = self._get_config_from_partition(next_node)
        return config

    def build_tree(self):
        """
        Build tree initially.
        """
        self._grow_tree_at_node(self._root)

    def adapt_tree(self, sample):
        """
        self.last_sampled_node is set to the node that the sample belongs to.
        Add new sample values (config and performance) to feature/target of it and grow at that node.
        Re-Calculate nodes error value.

        :param sample: A tuple of a flat config (np.array) and a target value.
        """
        curr_node = self.last_sampled_node
        f, t = sample[0], sample[1]

        # Todo: append sample f and t to curr_node
        curr_node.error = self._calculate_node_error(curr_node.target)
        self._grow_tree_at_node(curr_node)

    def prune_tree(self):
        # Todo: Prune tree, called afterwards?
        pass

    def get_tree(self):
        """
        If tree is used again after initial selection process.

        :return: Decision Tree Model.
        """
        return self._root

    def print_tree(self, node, condition=""):
        """
        Print tree to STDOUT.
        """
        base = "   " * node.depth + condition
        if node.split_feature_index is not None:
            print("%s if X[%s] <= %s" % (base, node.split_feature_index, node.split_feature_cut_val))
            self.print_tree(node.left, "then")
            self.print_tree(node.right, "else")

        else:
            print("%s {value: %s, samples: %s}" % (base, node.pred_value, node.partition_size))

