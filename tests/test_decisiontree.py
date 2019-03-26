"""
Copyright (c) 2019 Heidi Neuhäuser
ALL RIGHTS RESERVED.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import unittest
import numpy as np
from nfvtcp.decisiontree import DecisionTree, Node


class TestNode(unittest.TestCase):

    def test_initialize(self):
        params = [{"a": [1, 2, 3], "b": [32, 64, 256]}, {"a": [1, 2], "b": [8, 16, 32, 64, 256]}]
        features = np.array([[1, 32, 1, 16], [1, 32, 1, 64], [2, 64, 2, 64], [3, 32, 1, 8]])
        target = np.array([0.61, 0.55, 0.32, 0.91])
        d = 4

        node = Node(params, features, target, d)

        self.assertEqual(node.parameters, params)
        self.assertTrue((node.features == features).all())
        self.assertTrue((node.target == target).all())
        self.assertEqual(node.depth, d)
        self.assertEqual(Node._config_size, 0)

        node.set_config_size(1024)
        self.assertEqual(Node._config_size, 1024)
        node.set_config_size(0)
        node = None

    def test_calc_partition_size(self):
        params = [{"a": [1, 2, 3], "b": [32]}, {"a": [1, 2], "b": [8]}]

        node = Node(params, None, None, 0)
        node.calculate_partition_size()
        self.assertEqual(node.partition_size, 6)

        node.parameters = [{"a": [1, 2], "b": [32]}, {"a": [1, 2], "b": [8]}]
        node.calculate_partition_size()
        self.assertEqual(node.partition_size, 4)
        node = None

    def test_calc_score(self):
        params = [{"a": [1, 2, 3], "b": [32]}, {"a": [1, 2], "b": [8]}]

        node = Node(params, None, None, 0)
        node.set_config_size(1000)
        node.error = 0.25
        node.calculate_score(0.5)

        score = (-1) * (0.5 * 0.25 + 0.5 * (6 / 1000))

        self.assertEqual(node.score, score)
        node.set_config_size(0)
        node = None


class TestDecisionTree(unittest.TestCase):
    # Todo

    def test_initialize(self):
        params = {"a": [1, 2, 3], "b": [32, 64, 256]}
        features = [[1, 32, 1, 16], [1, 32, 1, 64], [2, 64, 2, 64], [3, 32, 1, 8]]
        target = [0.61, 0.55, 0.32, 0.91]

        dtree = DecisionTree(params, features, target)
        root = dtree.get_tree()

        self.assertEqual(root.parameters, [dict(params), dict(params)])
        self.assertTrue((root.features == features).all())
        self.assertTrue((root.target == target).all())
        self.assertEqual(dtree.vnf_count, 2)
        self.assertEqual(dtree._depth, 1)
        self.assertNotEqual(Node._config_size, 0)

    def test_calc_new_params(self):
        params = {"a": [1, 2, 3], "b": [32, 64, 256]}
        features = [[1, 32, 1, 16], [1, 32, 1, 64], [2, 64, 2, 64], [3, 32, 1, 8]]
        target = [0.61, 0.55, 0.32, 0.91]

        dtree = DecisionTree(params, features, target)
        root = dtree.get_tree()
        p_left, p_right = dtree._calculate_new_parameters(root.parameters, 1, 100)

        self.assertEqual(len(dtree.feature_idx_to_name), 4)
        # Todo: check new parameters


    def test_split_node(self):
        params = {"a": [1, 2, 3], "b": [32, 64, 256]}
        features = [[1, 32, 1, 16], [1, 32, 1, 64], [2, 64, 2, 64], [3, 32, 1, 8]]
        target = [0.61, 0.55, 0.32, 0.91]

        dtree = DecisionTree(params, features, target)
        root = dtree.get_tree()
        root.split_feature_index = 3
        root.split_feature_cut_val = 50
        root.error = 0.25

        root.calculate_partition_size()
        root.set_config_size(root.partition_size)

        self.assertEqual(dtree._depth, 1)
        self.assertEqual(len(dtree.leaf_nodes), 0)
        print("root:\n{}".format(str(root)))

        dtree._split_node(root)

        self.assertEqual(dtree._depth, 2)
        self.assertEqual(len(dtree.leaf_nodes), 2)
        print("left child:\n{}".format(str(root.left)))
        print("right child:\n{}".format(str(root.right)))

        dtree = None
