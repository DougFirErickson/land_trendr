import boto
import os
import shutil

from mrjob.job import MRJob

import utils

DOWNLOAD_DIR = '/tmp'

class MRLandTrendrJob(MRJob):
    def __init__(self, *args, **kwargs):
        index_eqn = kwargs.pop('index_eqn', 'B1')
        extra_job_runner_kwargs = kwargs.pop('job_runner_kwargs', {})
        extra_emr_job_runner_kwargs = kwargs.pop('emr_job_runner_kwargs', {})
        super(MRLandTrendrJob, self).__init__(*args, **kwargs)
        self.index_eqn = index_eqn
        self.extra_job_runner_kwargs = extra_job_runner_kwargs
        self.extra_emr_job_runner_kwargs = extra_emr_job_runner_kwargs

    def parse_mapper(self, _, line):
        s3_bucket, s3_key = line.split('\t')
        connection = boto.connect_s3()
        bucket = connection.get_bucket(s3_bucket)
        key = bucket.get_key(s3_key)
        filename = os.path.join(DOWNLOAD_DIR, os.path.basename(key.key))
        key.get_contents_to_filename(filename)
        rast_fn = utils.decompress(filename)[0]
        datestring = utils.filename2date(rast_fn)
        index_rast = utils.rast_algebra(rast_fn, self.index_eqn)
        shutil.rmtree(os.path.dirname(rast_fn))
        return utils.serialize_rast(index_rast, {'date': datestring})

    def analysis_mapper(self, point, values):
        LINE_COST = 10 #TODO arg
        yield point, utils.analyze(values, LINE_COST)

    def date_mapper(self, point, values):
        for value in values:
            date = value.pop('date')
            value['point'] = point
            yield date, value

    def steps(self):
        return [
            self.mr(mapper=self.parse_mapper),
            self.mr(mapper=self.analysis_mapper),
            self.mr(mapper=self.date_mapper)
        ]
    
    def job_runner_kwargs(self):
        kwargs = super(MRLandTrendrJob, self).job_runner_kwargs()
        kwargs.update(self.extra_job_runner_kwargs)        
        return kwargs

    def emr_job_runner_kwargs(self):
        kwargs = super(MRLandTrendrJob, self).emr_job_runner_kwargs()
        kwargs.update(self.extra_emr_job_runner_kwargs)        
        return kwargs

if __name__ == '__main__':
    MRLandTrendrJob.run()
