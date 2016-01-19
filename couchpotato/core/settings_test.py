import mock
from mock import patch, Mock 
import unittest
from unittest import TestCase

from couchpotato.core.settings import Settings

class DoNotUseMe:
    """ Do not use this class, it is just for storing Mock ' s of Settings-class

    Usage:
        Select appropriate Mocks and copy-paste them to your test-method
    """
    def __do_not_call(self):
        # s = Settings
        s = Mock()

        # methods:
        s.isOptionWritable = Mock(return_value=True)
        s.set = Mock(return_value=None)
        s.save = Mock()

        # props:
        s.log = Mock()
       
class SettingsSaveWritableNonWritable(TestCase):
    def setUp(self):
        self.s = Settings()

    def test_save_writable(self):
        s = self.s

        # set up Settings-mocks :
        # lets assume, that option is writable:
        mock_isOptionWritable = s.isOptionWritable = Mock(return_value=True)
        mock_set = s.set = Mock(return_value=None)
        mock_p_save = s.save = Mock()

        section = 'core'
        option = 'option_non_exist_be_sure'
        value = "1000"
        params = { 'section' : section, 'name' : option, 'value' : value }
 
        # call method:
        env_mock = Mock()

        # HERE is an example of mocking LOCAL 'import'
        with patch.dict('sys.modules', {'couchpotato.environment.Env': env_mock}):
            result = s.saveView(**params)

        self.assertIsInstance(s, Settings)
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])

        # -----------------------------------------
        # check mock
        # -----------------------------------------
        mock_isOptionWritable.assert_called_with(section, option)

        # check, that Settings tried to save my value:
        mock_set.assert_called_with(section, option, value)


    def test_save_non_writable(self):
        s = self.s

        # set up Settings-mocks :
        # lets assume, that option is not writable:
        mock_is_w = s.isOptionWritable = Mock(return_value=False)
        mock_set = s.set = Mock(return_value=None)
        mock_p_save = s.save = Mock()
        mock_log_s = s.log = Mock()

        section = 'core'
        option = 'option_non_exist_be_sure'
        value = "1000"
        params = { 'section' : section, 'name' : option, 'value' : value }
 
        # call method:
        env_mock = Mock()

        # HERE is an example of mocking LOCAL 'import'
        with patch.dict('sys.modules', {'couchpotato.environment.Env': env_mock}):
            result = s.saveView(**params)


        self.assertIsInstance(s, Settings)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['success'])

        # -----------------------------------------
        # check mock
        # -----------------------------------------
        # lets check, that 'set'-method was not called:
        self.assertFalse(mock_set.called, 'Method `set` was called')
        mock_is_w.assert_called_with(section, option)
