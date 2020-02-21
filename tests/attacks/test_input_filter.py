# MIT License
#
# Copyright (C) IBM Corporation 2018
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import unittest

import numpy as np
import pandas as pd

from art.attacks import ProjectedGradientDescent
from art.classifiers import KerasClassifier

from art.utils import load_dataset, get_labels_np_array, random_targets
from tests.utils_test import get_image_classifier_tf, get_image_classifier_kr, get_image_classifier_pt
from tests.utils_test import get_tabular_classifier_tf, get_tabular_classifier_kr, get_tabular_classifier_pt, master_seed


logger = logging.getLogger(__name__)

BATCH_SIZE = 10
NB_TRAIN = 10
NB_TEST = 11


class TestInputFilter(unittest.TestCase):
    """
    A unittest class for testing the input filtering using
    PGD tests.
    """
    @classmethod
    def setUpClass(cls):
        # MNIST
        (x_train, y_train), (x_test, y_test), _, _ = load_dataset('mnist')
        x_train = list(x_train[:NB_TRAIN])
        y_train = list(y_train[:NB_TRAIN])
        x_test = list(x_test[:NB_TEST])
        y_test = list(y_test[:NB_TEST])
        cls.mnist = (x_train, y_train), (x_test, y_test)

        # Iris
        (x_train, y_train), (x_test, y_test), _, _ = load_dataset('iris')
        x_train = pd.DataFrame(x_train)
        y_train = pd.DataFrame(y_train)
        x_test = pd.DataFrame(x_test)
        y_test = pd.DataFrame(y_test)
        cls.iris = (x_train, y_train), (x_test, y_test)

    def setUp(self):
        master_seed(1234)

    def test_tensorflow_mnist(self):
        (x_train, y_train), (x_test, y_test) = self.mnist
        classifier, sess = get_image_classifier_tf()

        scores = get_labels_np_array(classifier.predict(x_train))
        acc = np.sum(np.argmax(scores, axis=1) == np.argmax(y_train, axis=1)) / len(y_train)
        logger.info('[TF, MNIST] Accuracy on training set: %.2f%%', acc * 100)

        scores = get_labels_np_array(classifier.predict(x_test))
        acc = np.sum(np.argmax(scores, axis=1) == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('[TF, MNIST] Accuracy on test set: %.2f%%', acc * 100)

        self._test_backend_mnist(classifier, x_train, y_train, x_test, y_test)

    def test_pytorch_mnist(self):
        (x_train, y_train), (x_test, y_test) = self.mnist
        x_train = np.swapaxes(x_train, 1, 3).astype(np.float32)
        x_test = np.swapaxes(x_test, 1, 3).astype(np.float32)
        classifier = get_image_classifier_pt()

        scores = get_labels_np_array(classifier.predict(x_train))
        acc = np.sum(np.argmax(scores, axis=1) == np.argmax(y_train, axis=1)) / len(y_train)
        logger.info('[PyTorch, MNIST] Accuracy on training set: %.2f%%', acc * 100)

        scores = get_labels_np_array(classifier.predict(x_test))
        acc = np.sum(np.argmax(scores, axis=1) == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('[PyTorch, MNIST] Accuracy on test set: %.2f%%', acc * 100)

        self._test_backend_mnist(classifier, x_train, y_train, x_test, y_test)

    def _test_backend_mnist(self, classifier, x_train, y_train, x_test, y_test):
        x_test_original = x_test.copy()

        # Test PGD with np.inf norm
        attack = ProjectedGradientDescent(classifier, eps=1, eps_step=0.1, max_iter=5)
        x_train_adv = attack.generate(x_train)
        x_test_adv = attack.generate(x_test)

        self.assertFalse((x_train == x_train_adv).all())
        self.assertFalse((x_test == x_test_adv).all())

        train_y_pred = get_labels_np_array(classifier.predict(x_train_adv))
        test_y_pred = get_labels_np_array(classifier.predict(x_test_adv))

        self.assertFalse((y_train == train_y_pred).all())
        self.assertFalse((y_test == test_y_pred).all())

        acc = np.sum(np.argmax(train_y_pred, axis=1) == np.argmax(y_train, axis=1)) / len(y_train)
        logger.info('Accuracy on adversarial train examples: %.2f%%', acc * 100)

        acc = np.sum(np.argmax(test_y_pred, axis=1) == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('Accuracy on adversarial test examples: %.2f%%', acc * 100)

        # Test PGD with 3 random initialisations
        attack = ProjectedGradientDescent(classifier, num_random_init=3, max_iter=5)
        x_train_adv = attack.generate(x_train)
        x_test_adv = attack.generate(x_test)

        self.assertFalse((x_train == x_train_adv).all())
        self.assertFalse((x_test == x_test_adv).all())

        train_y_pred = get_labels_np_array(classifier.predict(x_train_adv))
        test_y_pred = get_labels_np_array(classifier.predict(x_test_adv))

        self.assertFalse((y_train == train_y_pred).all())
        self.assertFalse((y_test == test_y_pred).all())

        acc = np.sum(np.argmax(train_y_pred, axis=1) == np.argmax(y_train, axis=1)) / len(y_train)
        logger.info('Accuracy on adversarial train examples with 3 random initialisations: %.2f%%', acc * 100)

        acc = np.sum(np.argmax(test_y_pred, axis=1) == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('Accuracy on adversarial test examples with 3 random initialisations: %.2f%%', acc * 100)

        # Check that x_test has not been modified by attack and classifier
        self.assertAlmostEqual(float(np.max(np.abs(np.array(x_test_original) - np.array(x_test)))), 0.0, delta=0.00001)

    def test_classifier_type_check_fail_classifier(self):
        # Use a useless test classifier to test basic classifier properties
        class ClassifierNoAPI:
            pass

        classifier = ClassifierNoAPI
        with self.assertRaises(TypeError) as context:
            _ = ProjectedGradientDescent(classifier=classifier)

        self.assertIn('For `ProjectedGradientDescent` classifier must be an instance of '
                      '`art.classifiers.classifier.Classifier`, the provided classifier is instance of '
                      '(<class \'object\'>,).', str(context.exception))

    def test_classifier_type_check_fail_gradients(self):
        # Use a test classifier not providing gradients required by white-box attack
        from art.classifiers.scikitlearn import ScikitlearnDecisionTreeClassifier
        from sklearn.tree import DecisionTreeClassifier

        classifier = ScikitlearnDecisionTreeClassifier(model=DecisionTreeClassifier())
        with self.assertRaises(TypeError) as context:
            _ = ProjectedGradientDescent(classifier=classifier)

        self.assertIn('For `ProjectedGradientDescent` classifier must be an instance of '
                      '`art.classifiers.classifier.ClassifierGradients`, the provided classifier is instance of '
                      '(<class \'art.classifiers.scikitlearn.ScikitlearnClassifier\'>,).', str(context.exception))

    def test_keras_iris_clipped(self):
        (_, _), (x_test, y_test) = self.iris
        classifier = get_tabular_classifier_kr()

        # Test untargeted attack
        attack = ProjectedGradientDescent(classifier, eps=1, eps_step=0.1, max_iter=5)
        x_test_adv = attack.generate(x_test)
        self.assertFalse((np.array(x_test) == x_test_adv).all())
        self.assertTrue((x_test_adv <= 1).all())
        self.assertTrue((x_test_adv >= 0).all())

        preds_adv = np.argmax(classifier.predict(x_test_adv), axis=1)
        self.assertFalse((np.argmax(np.array(y_test), axis=1) == preds_adv).all())
        acc = np.sum(preds_adv == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('Accuracy on Iris with PGD adversarial examples: %.2f%%', (acc * 100))

    def test_keras_iris_unbounded(self):
        (_, _), (x_test, y_test) = self.iris
        classifier = get_tabular_classifier_kr()

        # Recreate a classifier without clip values
        classifier = KerasClassifier(model=classifier._model, use_logits=False, channel_index=1)
        attack = ProjectedGradientDescent(classifier, eps=1, eps_step=0.2, max_iter=5)
        x_test_adv = attack.generate(x_test)
        self.assertFalse((np.array(x_test) == x_test_adv).all())
        self.assertTrue((x_test_adv > 1).any())
        self.assertTrue((x_test_adv < 0).any())

        preds_adv = np.argmax(classifier.predict(x_test_adv), axis=1)
        self.assertFalse((np.argmax(np.array(y_test), axis=1) == preds_adv).all())
        acc = np.sum(preds_adv == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('Accuracy on Iris with PGD adversarial examples: %.2f%%', (acc * 100))

    def test_tensorflow_iris(self):
        (_, _), (x_test, y_test) = self.iris
        classifier, _ = get_tabular_classifier_tf()

        # Test untargeted attack
        attack = ProjectedGradientDescent(classifier, eps=1, eps_step=0.1, max_iter=5)
        x_test_adv = attack.generate(x_test)
        self.assertFalse((np.array(x_test) == x_test_adv).all())
        self.assertTrue((x_test_adv <= 1).all())
        self.assertTrue((x_test_adv >= 0).all())

        preds_adv = np.argmax(classifier.predict(x_test_adv), axis=1)
        self.assertFalse((np.argmax(np.array(y_test), axis=1) == preds_adv).all())
        acc = np.sum(preds_adv == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('Accuracy on Iris with PGD adversarial examples: %.2f%%', (acc * 100))

    def test_pytorch_iris_pt(self):
        (_, _), (x_test, y_test) = self.iris
        classifier = get_tabular_classifier_pt()

        # Test untargeted attack
        attack = ProjectedGradientDescent(classifier, eps=1, eps_step=0.1, max_iter=5)
        x_test_adv = attack.generate(x_test)
        self.assertFalse((np.array(x_test) == x_test_adv).all())
        self.assertTrue((x_test_adv <= 1).all())
        self.assertTrue((x_test_adv >= 0).all())

        preds_adv = np.argmax(classifier.predict(x_test_adv), axis=1)
        self.assertFalse((np.argmax(np.array(y_test), axis=1) == preds_adv).all())
        acc = np.sum(preds_adv == np.argmax(np.array(y_test), axis=1)) / len(y_test)
        logger.info('Accuracy on Iris with PGD adversarial examples: %.2f%%', (acc * 100))

    def test_scikitlearn(self):
        from sklearn.linear_model import LogisticRegression
        from sklearn.svm import SVC, LinearSVC

        from art.classifiers.scikitlearn import ScikitlearnLogisticRegression, ScikitlearnSVC

        scikitlearn_test_cases = {LogisticRegression: ScikitlearnLogisticRegression,
                                  SVC: ScikitlearnSVC,
                                  LinearSVC: ScikitlearnSVC}

        (_, _), (x_test, y_test) = self.iris
        x_test_original = x_test.copy()

        for (model_class, classifier_class) in scikitlearn_test_cases.items():
            model = model_class()
            classifier = classifier_class(model=model, clip_values=(0, 1))
            classifier.fit(x=x_test, y=y_test)

            # Test untargeted attack
            attack = ProjectedGradientDescent(classifier, eps=1, eps_step=0.1, max_iter=5)
            x_test_adv = attack.generate(x_test)
            self.assertFalse((np.array(x_test) == x_test_adv).all())
            self.assertTrue((x_test_adv <= 1).all())
            self.assertTrue((x_test_adv >= 0).all())

            preds_adv = np.argmax(classifier.predict(x_test_adv), axis=1)
            self.assertFalse((np.argmax(np.array(y_test), axis=1) == preds_adv).all())
            acc = np.sum(preds_adv == np.argmax(np.array(y_test), axis=1)) / len(y_test)
            logger.info('Accuracy of ' + classifier.__class__.__name__ + ' on Iris with PGD adversarial examples: '
                                                                         '%.2f%%', (acc * 100))

if __name__ == '__main__':
    unittest.main()
