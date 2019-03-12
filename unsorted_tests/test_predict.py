# Copyright 2016 the GPflow authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tensorflow as tf
import numpy as np

import gpflow
from gpflow.kernels import Matern32
import pytest


rng = np.random.RandomState(0)

@pytest.mark.parametrize('Ntrain, Ntest, D', [[100, 10, 2]])
def test_gaussian_mean_and_variance(Ntrain, Ntest, D):
    X, Y = rng.randn(Ntrain, D), rng.randn(Ntrain, 1)
    Xtest, Ytest = rng.randn(Ntest, D), rng.randn(Ntest, 1)
    kern = Matern32() + gpflow.kernels.White()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu_f, var_f = model_gp.predict_f(Xtest)
    mu_y, var_y = model_gp.predict_y(Xtest)

    assert np.allclose(mu_f, mu_y)
    assert np.allclose(var_f, var_y - 1.)

@pytest.mark.parametrize('Ntrain, Ntest, D', [[100, 10, 2]])
def test_gaussian_log_density(Ntrain, Ntest, D):
    X, Y = rng.randn(Ntrain, D), rng.randn(Ntrain, 1)
    Xtest, Ytest = rng.randn(Ntest, D), rng.randn(Ntest, 1)
    kern = Matern32() + gpflow.kernels.White()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu_y, var_y = model_gp.predict_y(Xtest)
    log_density = model_gp.predict_log_density(Xtest, Ytest)
    log_density_hand = (-0.5 * np.log(2 * np.pi) -
                0.5 * np.log(var_y) -
                0.5 * np.square(mu_y - Ytest) / var_y)

    assert np.allclose(log_density_hand, log_density)


@pytest.mark.parametrize('Ntrain, Ntest, D', [[100, 10, 2]])
def test_gaussian_recompile(Ntrain, Ntest, D):
    X, Y = rng.randn(Ntrain, D), rng.randn(Ntrain, 1)
    Xtest, Ytest = rng.randn(Ntest, D), rng.randn(Ntest, 1)
    kern = Matern32() + gpflow.kernels.White()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu_f, var_f = model_gp.predict_f(Xtest)
    mu_y, var_y = model_gp.predict_y(Xtest)
    log_density = model_gp.predict_log_density(Xtest, Ytest)

    # change a fix and see if these things still compile
    model_gp.likelihood.variance.assign(0.2)
    model_gp.likelihood.variance.trainable = False

    # this will fail unless a recompile has been triggered
    mu_f, var_f = model_gp.predict_f(Xtest)
    mu_y, var_y = model_gp.predict_y(Xtest)
    log_density = model_gp.predict_log_density(Xtest, Ytest)


@pytest.mark.parametrize('input_dim, output_dim, N, Ntest, M', [
    [3, 2, 20, 30, 5]
])
def test_gaussian_full_cov(input_dim, output_dim, N, Ntest, M):
    covar_shape = (output_dim, Ntest, Ntest)
    X, Y, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    kern = Matern32()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu1, var = model_gp.predict_f(Xtest, full_cov=False)
    mu2, covar = model_gp.predict_f(Xtest, full_cov=True)

    assert np.allclose(mu1, mu2, atol=1.e-10)
    assert covar.shape == covar_shape
    assert var.shape == (Ntest, output_dim)
    for i in range(output_dim):
        assert np.allclose(var[:, i], np.diag(covar[i, :, :]))


@pytest.mark.parametrize('input_dim, output_dim, N, Ntest, M, num_samples', [
    [3, 2, 20, 30, 5, 5]
])
def test_gaussian_full_cov_samples(input_dim, output_dim, N, Ntest, M, num_samples):
    samples_shape = (num_samples, Ntest, output_dim)
    X, Y, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    kern = Matern32()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    samples = model_gp.predict_f_samples(Xtest, num_samples)
    assert samples.shape == samples_shape


# TODO(@sergio.pasc) As model classes are updated to TF2.0, prepare tests accordingly

class ModelSetup:
    def __init__(self, model_class, kernel=Matern32(), likelihood=gpflow.likelihoods.Gaussian(),
                 whiten=None, q_diag=None, requires_Z_as_input = True):
        self.model_class = model_class
        self.kernel = kernel
        self.likelihood = likelihood
        self.whiten = whiten
        self.q_diag = q_diag
        self.requires_Z_as_input = requires_Z_as_input

    def get_model(self, Z):
        if self.whiten is not None and self.q_diag is not None:
            return self.model_class(Z=Z, kernel=self.kernel, likelihood=self.likelihood,
                                    whiten=self.whiten, q_diag=self.q_diag)
        else:
            return self.model_class(Z=Z, kernel=self.kernel, likelihood=self.likelihood)

model_setups = [
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=False, q_diag=True),
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=True, q_diag=False),
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=True, q_diag=True),
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=False, q_diag=False),
    ModelSetup(model_class=gpflow.models.SGPR),
    ModelSetup(model_class=gpflow.models.GPRF),
    ModelSetup(model_class=gpflow.models.VGP, requires_Z_as_input = False),
    ModelSetup(model_class=gpflow.models.GPMC, requires_Z_as_input = False ),
    ModelSetup(model_class=gpflow.models.SGPMC)
]


@pytest.mark.parametrize('model_setup', [model_setups])
@pytest.mark.parametrize('input_dim, output_dim, N, Ntest, M', [
    [3, 2, 20, 30, 5]
])
def test_other_models_full_cov(model_setup, input_dim, output_dim, N, Ntest, M):
    covar_shape = (output_dim, Ntest, Ntest)
    X, Y, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    model_gp = model_setup.get_model(Z)

    mu1, var = model_gp.predict_f(Xtest, full_cov=False)
    mu2, covar = model_gp.predict_f(Xtest, full_cov=True)

    assert np.allclose(mu1, mu2, atol=1.e-10)
    assert covar.shape == covar_shape
    assert var.shape == (Ntest, output_dim)
    for i in range(output_dim):
        assert np.allclose(var[:, i], np.diag(covar[i, :, :]))


@pytest.mark.parametrize('model_setup', [model_setups])
@pytest.mark.parametrize('input_dim, output_dim, N, Ntest, M, num_samples', [
    [3, 2, 20, 30, 5, 5]
])
def test_other_models_full_cov_samples(model_setup, input_dim, output_dim, N, Ntest, M,
                                       num_samples):
    samples_shape = (num_samples, Ntest, output_dim)
    X, Y, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    model_gp = model_setup.get_model(Z)

    samples = model_gp.predict_f_samples(Xtest, num_samples)
    assert samples.shape == samples_shape












class TestFullCov():
    """
    this base class requires inherriting to specify the model.

    This test structure is more complex that, say, looping over the models, but
    makses all the tests much smaller and so less prone to erroring out. Also,
    if a test fails, it should be clearer where the error is.
    """

    input_dim = 3
    output_dim = 2
    N = 20
    Ntest = 30
    M = 5
    rng = np.random.RandomState(0)
    num_samples = 5
    samples_shape = (num_samples, Ntest, output_dim)
    covar_shape = (output_dim, Ntest, Ntest)
    X = rng.randn(N, input_dim)
    Y = rng.randn(N, output_dim)
    Z = rng.randn(M, input_dim)

    @classmethod
    def kernel(cls):
        return gpflow.kernels.Matern32(cls.input_dim)

    def prepare(self):
        return gpflow.models.GPR(self.X, self.Y, kern=self.kernel())

    def test_cov(self):
        with self.test_context():
            m = self.prepare()
            mu1, var = m.predict_f(self.Xtest)
            mu2, covar = m.predict_f_full_cov(self.Xtest)
            self.assertTrue(np.all(mu1 == mu2))
            self.assertTrue(covar.shape == self.covar_shape)
            self.assertTrue(var.shape == (self.Ntest, self.output_dim))
            for i in range(self.output_dim):
                self.assertTrue(np.allclose(var[:, i], np.diag(covar[i, :, :])))

    def test_samples(self):
        with self.test_context():
            m = self.prepare()
            samples = m.predict_f_samples(self.Xtest, self.num_samples)
            self.assertTrue(samples.shape == self.samples_shape)


class TestFullCovSGPR(TestFullCov):
    def prepare(self):
        return gpflow.models.SGPR(self.X, self.Y, Z=self.Z, kern=self.kernel())


class TestFullCovGPRFITC(TestFullCov):
    def prepare(self):
        return gpflow.models.GPRFITC(self.X, self.Y, Z=self.Z, kern=self.kernel())


class TestFullCovSVGP1(TestFullCov):
    def prepare(self):
        return gpflow.models.SVGP(
            self.X, self.Y, Z=self.Z, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian(),
            whiten=False, q_diag=True)


class TestFullCovSVGP2(TestFullCov):
    def prepare(self):
        return gpflow.models.SVGP(
            self.X, self.Y, Z=self.Z, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian(),
            whiten=True, q_diag=False)


class TestFullCovSVGP3(TestFullCov):
    def prepare(self):
        return gpflow.models.SVGP(
            self.X, self.Y, Z=self.Z, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian(),
            whiten=True, q_diag=True)


class TestFullCovSVGP4(TestFullCov):
    def prepare(self):
        return gpflow.models.SVGP(
            self.X, self.Y, Z=self.Z, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian(),
            whiten=True, q_diag=False)


class TestFullCovVGP(TestFullCov):
    def prepare(self):
        return gpflow.models.VGP(
            self.X, self.Y, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian())


class TestFullCovGPMC(TestFullCov):
    def prepare(self):
        return gpflow.models.GPMC(
            self.X, self.Y, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian())


class TestFullCovSGPMC(TestFullCov):
    def prepare(self):
        return gpflow.models.SGPMC(
            self.X, self.Y, kern=self.kernel(),
            likelihood=gpflow.likelihoods.Gaussian(),
            Z=self.Z)


if __name__ == "__main__":
    tf.test.main()
