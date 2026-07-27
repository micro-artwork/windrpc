import unittest
import sys
import os

# windrpc 패키지 경로를 추가하여 임포트 가능하도록 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from windrpc.utils import spec_validator

class TestSpecValidator(unittest.TestCase):
    def setUp(self):
        # 기본 정상 딕셔너리 스펙 구성
        self.valid_spec = {
            'package': 'test_pkg',
            'platform_version_code': 1,
            'types': {
                'messages': [
                    {
                        'name': 'CommonMsg',
                        'fields': [
                            {'number': 1, 'name': 'status_code', 'type': 'uint32'}
                        ]
                    }
                ],
                'enums': [
                    {
                        'name': 'CommonEnum',
                        'members': [
                            {'name': 'NONE', 'value': 0},
                            {'name': 'ACTIVE', 'value': 1}
                        ]
                    }
                ]
            },
            'services': [
                {
                    'id': 11,
                    'name': 'led_control',
                    'messages': [
                        {
                            'name': 'PixelData',
                            'fields': [
                                {'number': 1, 'name': 'colors', 'type': 'fixed32', 'property': 'repeated'}
                            ]
                        }
                    ],
                    'rpcs': [
                        {
                            'id': 1,
                            'name': 'display_pixels',
                            'type': 'REQUEST_ONLY',
                            'command': 'PixelData'
                        }
                    ]
                }
            ]
        }

    def test_valid_spec_passes(self):
        # 정상 스펙은 sys.exit() 없이 통과해야 함
        try:
            spec_validator.validate(self.valid_spec, verbose=False)
        except SystemExit:
            self.fail("Valid spec raised SystemExit unexpectedly.")

    def test_invalid_package_name(self):
        # 패키지명에 특수문자(하이픈) 포함 -> 식별자 규칙 위반으로 SystemExit 발생해야 함
        self.valid_spec['package'] = 'test-pkg'
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_invalid_service_name(self):
        # 서비스명에 PascalCase 사용 -> snake_case 위반으로 SystemExit 발생해야 함
        self.valid_spec['services'][0]['name'] = 'LedControl'
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_invalid_message_name(self):
        # 메시지명에 snake_case 사용 -> PascalCase 위반으로 SystemExit 발생해야 함
        self.valid_spec['services'][0]['messages'][0]['name'] = 'pixel_data'
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_invalid_field_name(self):
        # 필드명에 PascalCase 사용 -> snake_case 위반으로 SystemExit 발생해야 함
        self.valid_spec['services'][0]['messages'][0]['fields'][0]['name'] = 'ColorsVal'
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_invalid_rpc_name(self):
        # RPC명에 하이픈 및 PascalCase 사용 -> snake_case/식별자 위반으로 SystemExit 발생해야 함
        self.valid_spec['services'][0]['rpcs'][0]['name'] = 'Display-Pixels'
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_invalid_enum_member_name(self):
        # Enum 멤버명에 소문자 사용 -> UPPER_SNAKE_CASE 위반으로 SystemExit 발생해야 함
        self.valid_spec['types']['enums'][0]['members'][0]['name'] = 'none_member'
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_invalid_reserved_service_id(self):
        # 서비스 ID가 예약 영역(1~6)인 5로 설정되면 SystemExit가 발생해야 함
        self.valid_spec['services'][0]['id'] = 5
        with self.assertRaises(SystemExit):
            spec_validator.validate(self.valid_spec, verbose=False)

    def test_request_response_aliases_pass(self):
        # request/response 및 params/returns 별칭 구문 테스트
        spec_request_response = {
            'package': 'test_pkg',
            'types': {
                'messages': [{'name': 'Empty'}]
            },
            'services': [
                {
                    'id': 10,
                    'name': 'power',
                    'messages': [{'name': 'PowerInfo', 'fields': [{'number': 1, 'name': 'v', 'type': 'uint32'}]}],
                    'rpcs': [
                        {'id': 1, 'name': 'get_power_req', 'type': 'REQUEST_RESPONSE', 'request': 'types.Empty', 'response': 'PowerInfo'},
                        {'id': 2, 'name': 'get_power_param', 'type': 'REQUEST_RESPONSE', 'params': 'types.Empty', 'returns': 'PowerInfo'}
                    ]
                }
            ]
        }
        # spec_validator.validate가 SystemExit 없이 성공해야 함
        try:
            spec_validator.validate(spec_request_response, verbose=False)
        except SystemExit:
            self.fail("request/response or params/returns spec raised SystemExit unexpectedly.")


if __name__ == '__main__':
    unittest.main()

