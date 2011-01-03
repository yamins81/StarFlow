import os
from starflow.de import DataEnvironment
from starflow.tests import StarFlowTest
from starflow import static

class TestDE(StarFlowTest):

    def test_de(self):
        myde = '/tmp/myde'
        os.system('rm -rf %s' % myde)
        os.mkdir(myde)
        de = DataEnvironment(myde)
        assert not de.is_data_environ()
        de.create()
        assert de.is_data_environ()
        assert de.path == myde
        assert os.path.exists(os.path.join(myde,static.STARFLOW_CFG_DIR)) 

if __name__ == "__main__":
    import nose
    nose.main(module='starflow.tests')
