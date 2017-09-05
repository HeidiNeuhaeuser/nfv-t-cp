"""
Copyright (c) 2017 Manuel Peuster
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

Manuel Peuster, Paderborn University, manuel@peuster.de
"""
import numpy as np
import simpy
import logging
import os

LOG = logging.getLogger(os.path.basename(__file__))


class Profiler(object):

    def __init__(self,
                 pmodel,
                 pmodel_inputs,
                 selector,
                 predictor,
                 error):
        """
        Initialize profiler for one experiment configuration.
        """
        self.pm = pmodel
        self.pm_inputs = pmodel_inputs
        self.s = selector
        self.p = predictor
        self.e = error
        self._tmp_train_c = list()
        self._tmp_train_r = list()
        self._sim_t_total = 0
        self._sim_t_mean = list()
        # initialize simulation environment
        self.env = simpy.Environment()
        self.profile_proc = self.env.process(self.do_measurement())

    def do_measurement(self):
        while self.s.has_next():
            c = self.s.next()
            _start_t = self.env.now
            LOG.debug("t={} measuring config: {}".format(_start_t, c))
            r = self.pm.evaluate(c)
            self._tmp_train_c.append(c)  # store configs ...
            self._tmp_train_r.append(r)  # ... and results of profiling run
            self.s.feedback(c, r)  # inform selector about result
            # Note: Timing could be randomized, or a more complex function:
            yield self.env.timeout(60)  # Fix: assumes 60s per measurement
            # sim time bookkeeping (needed for more complex timing models)
            _end_t = self.env.now
            self._sim_t_total = _end_t
            self._sim_t_mean.append(_end_t - _start_t)
            
            LOG.debug("t={} result: {}".format(self._sim_t_total, r))
        LOG.debug("No configurations left. Stopping simulation.")

    def run(self, until=None):
        # TODO refactor: initialize, postprocess, do_comparison measurement(?)
        # reset tmp. results
        self._tmp_train_c = list()
        self._tmp_train_r = list()
        # simulate profiling process
        self.env.run(until=until)  # time limit in seconds
        # predict full result using training sets
        self.p.train(self._tmp_train_c, self._tmp_train_r)
        r_hat = self.p.predict(self.pm_inputs)
        # calculate reference result (evaluate pmodel for all configs)
        r = [self.pm.evaluate(c) for c in self.pm_inputs]
        # calculate error between prediction (r_hat) and reference results (r)
        mse = self.e.calculate(r, r_hat)
        #  build/return result dict (used as row of a Pandas DF)
        result = dict()
        result.update(self.pm.get_results())
        result.update(self.s.get_results())
        result.update(self.p.get_results())
        result.update({"sim_t_total": self._sim_t_total,
                       "sim_t_mean": np.mean(self._sim_t_mean),
                       "mse": mse})
        LOG.debug("Done. Resulting MSE={0:.4g}, sim_t_total={1}s".format(
            mse, self._sim_t_total))
        return result

        
def run(pmodel, pmodel_inputs, selector, predictor, error):
    p = Profiler(pmodel, pmodel_inputs, selector, predictor, error)
    return p.run(until=400)