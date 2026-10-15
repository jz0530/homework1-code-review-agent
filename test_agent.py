import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from agent import Agent, Client, DemoClient, ToolBox, main


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'buggy.py').write_text('def f(x=[]):\n    return x\n', encoding='utf-8')
        self.box = ToolBox(self.root)

    def test_real_tools_in_demo_loop(self):
        agent = Agent(DemoClient(), self.box, trace=lambda _: None)
        result = agent.ask('审查代码')
        self.assertIn('可变默认参数', result)
        self.assertEqual([m['role'] for m in agent.turns[0]],
                         ['user', 'assistant', 'tool', 'tool', 'assistant'])

    def test_traversal_and_absolute_paths_blocked(self):
        for path in ['../outside.py', str(self.root / 'buggy.py')]:
            self.assertIn('error', self.box.call('read_file', json.dumps({'path': path})))

    def test_hidden_files_and_large_files_blocked(self):
        (self.root / '.secret.py').write_text('secret=1')
        (self.root / 'large.py').write_bytes(b'x' * 32769)
        for path in ['.secret.py', 'large.py']:
            self.assertIn('error', self.box.call('read_file', json.dumps({'path': path})))

    def test_bad_arguments_and_unknown_tool(self):
        for name, args in [('read_file', '{'), ('read_file', '[]'),
                           ('read_file', '{"path":3}'), ('shell', '{"path":"buggy.py"}')]:
            self.assertIn('error', self.box.call(name, args))

    def test_syntax_error(self):
        (self.root / 'invalid.py').write_text('def broken(:')
        result = self.box.call('check_python', '{"path":"invalid.py"}')
        self.assertFalse(result['syntax_ok'])
        self.assertEqual(result['line'], 1)

    def test_mutable_default_check_scope(self):
        code = ('def f(a=[], b={}, c={1}, d=list(), e=dict(), f=set()):\n'
                '    pass\n')
        (self.root / 'defaults.py').write_text(code, encoding='utf-8')
        result = self.box.call('check_python', '{"path":"defaults.py"}')
        self.assertTrue(result['syntax_ok'])
        self.assertEqual([w['line'] for w in result['warnings']], [1])
        (self.root / 'calls.py').write_text(
            'def f(a=list(), b=dict(), c=set()):\n    pass\n', encoding='utf-8')
        self.assertEqual(self.box.call('check_python', '{"path":"calls.py"}')['warnings'], [])

    def test_missing_root_checked_before_client(self):
        with patch('sys.argv', ['agent.py', '--root', str(self.root / 'missing'), '--ask', 'hi']):
            with patch('agent.Client') as client, patch('builtins.print') as output:
                self.assertEqual(main(), 1)
        client.assert_not_called()
        self.assertIn('missing', str(output.call_args))

    def test_memory_bounded_and_used(self):
        class RecordingClient:
            def complete(self, messages):
                self.seen = messages
                return {'content': 'answer'}
        client = RecordingClient()
        agent = Agent(client, self.box)
        for i in range(5):
            agent.ask(str(i))
        self.assertEqual(len(agent.turns), 3)
        self.assertTrue(any(m.get('content') == '3' for m in client.seen))
        self.assertFalse(any(m.get('content') == '0' for m in client.seen))

    def test_loop_limit_rolls_back(self):
        class EndlessClient:
            def complete(self, messages):
                return {'tool_calls': [{'type': 'function', 'id': 'x',
                        'function': {'name': 'list_files', 'arguments': '{}'}}]}
        agent = Agent(EndlessClient(), self.box, trace=lambda _: None, max_steps=2)
        with self.assertRaisesRegex(RuntimeError, '上限'):
            agent.ask('审查')
        self.assertEqual(agent.turns, [])

    def test_failed_turn_does_not_damage_memory(self):
        class BrokenClient:
            def complete(self, messages):
                return {'tool_calls': [{'id': 'missing_function'}]}
        agent = Agent(BrokenClient(), self.box)
        with self.assertRaises(RuntimeError):
            agent.ask('审查')
        self.assertEqual(agent.turns, [])

    @patch.dict('os.environ', {'LLM_API_KEY': 'test-only', 'LLM_BASE_URL': 'https://example.invalid/v1'})
    def test_transient_errors_retry_three_times(self):
        with patch('agent.urllib.request.urlopen', side_effect=urllib.error.URLError('offline')) as call:
            with patch('agent.time.sleep'):
                with self.assertRaisesRegex(RuntimeError, '3次'):
                    Client().complete([])
        self.assertEqual(call.call_count, 3)

    @patch.dict('os.environ', {'LLM_API_KEY': 'test-only', 'LLM_BASE_URL': 'https://example.invalid/v1'})
    def test_auth_error_not_retried(self):
        error = urllib.error.HTTPError('https://example.invalid', 401, 'Unauthorized', {}, None)
        with patch('agent.urllib.request.urlopen', side_effect=error) as call:
            with self.assertRaisesRegex(RuntimeError, '401'):
                Client().complete([])
        self.assertEqual(call.call_count, 1)

    @patch.dict('os.environ', {'LLM_API_KEY': 'test-only', 'LLM_BASE_URL': 'https://example.invalid/v1'})
    def test_http_errors_give_relevant_hints(self):
        cases = [(503, '服务端', 3), (429, '限流', 3), (402, '余额', 1)]
        for status, hint, attempts in cases:
            with self.subTest(status=status):
                error = urllib.error.HTTPError('https://example.invalid', status, 'test', {}, None)
                with patch('agent.urllib.request.urlopen', side_effect=error) as call:
                    with patch('agent.time.sleep'):
                        with self.assertRaisesRegex(RuntimeError, hint) as result:
                            Client().complete([])
                self.assertEqual(call.call_count, attempts)
                if status >= 500:
                    self.assertNotIn('密钥', str(result.exception))

    def test_fixed_sample_boundaries(self):
        from examples.fixed import average, add_item
        self.assertEqual(average([2, 4]), 3)
        with self.assertRaises(ValueError):
            average([])
        self.assertEqual(add_item(1), [1])
        self.assertEqual(add_item(2), [2])

    @patch.dict('os.environ', {'LLM_API_KEY': 'test-only',
                            'LLM_BASE_URL': 'https://api.deepseek.com',
                            'LLM_MODEL': 'deepseek-flash'})
    def test_deepseek_request_configuration(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {'choices': [{'message': {'content': 'ok'}}]}).encode()
        with patch('agent.urllib.request.urlopen', return_value=response) as call:
            self.assertEqual(Client().complete([])['content'], 'ok')
        request = call.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://api.deepseek.com/chat/completions')
        self.assertEqual(payload['thinking'], {'type': 'disabled'})
        self.assertEqual(payload['max_tokens'], 2000)


if __name__ == '__main__':
    unittest.main()
