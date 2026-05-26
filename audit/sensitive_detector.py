"""
敏感信息检测器 - 增强版 v2.0
改进：支持格式变形、减少误检、增强校验
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


@dataclass
class SensitiveFinding:
    category: str
    matched_text: str
    position: int
    severity: str
    validation: str = "passed"


@dataclass
class DetectionResult:
    is_clean: bool
    findings: List[SensitiveFinding]
    summary: Dict[str, int]


class SensitivityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SensitiveDetector:
    """
    敏感信息检测器 v2.0

    改进点：
    1. 手机号支持格式变形（138-1234-5678, 138 1234 5678, +86 13812345678）
    2. 身份证支持格式变形（空格、特殊字符间隔）
    3. 银行卡增加Luhn校验，减少误检
    4. 增加假阳性排除（金额、序号等）
    5. 增强上下文语义判断
    """

    def __init__(self, custom_patterns: Dict[str, Tuple[str, SensitivityLevel]] = None):
        self.patterns = custom_patterns or self.DEFAULT_PATTERNS
        self._normalize_patterns()

    def _normalize_patterns(self):
        """标准化正则表达式"""
        self._phone_patterns = [
            r"1[3-9]\d{9}",  # 标准格式
            r"1[3-9]\d[\s\-]\d{4}[\s\-]\d{4}",  # 分隔格式
            r"\+86[\s]?1[3-9]\d{9}",  # 国际格式
            r"0086[\s]?1[3-9]\d{9}",  # 替代国际格式
        ]

    DEFAULT_PATTERNS = {
        "ID_Card": (
            r"(?<![0-9])\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?![0-9])",
            SensitivityLevel.HIGH
        ),
        "Phone": (
            r"1[3-9]\d{9}",
            SensitivityLevel.MEDIUM
        ),
        "Email": (
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            SensitivityLevel.LOW
        ),
        "BankCard": (
            r"(?<![0-9])(?:62[0-9]{14,17}|4[0-9]{15,18}|5[1-5][0-9]{14,17}|43[0-6][0-9]{13,16}|43[0-68][0-9]{13,16})(?![0-9])",
            SensitivityLevel.HIGH
        ),
        "IP": (
            r"(?<![0-9])((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?![0-9.])",
            SensitivityLevel.MEDIUM
        ),
    }

    CATEGORY_MAP = {
        "ID_Card": "身份证",
        "Phone": "手机号",
        "Email": "邮箱",
        "BankCard": "银行卡",
        "IP": "IP地址",
    }

    # 排除词：这些词出现在上下文中表示可能是假阳性
    EXCLUDE_CONTEXTS = {
        "金额", "序号", "订单号", "流水号", "编号", "编码",
        "账号", "卡号", "电话", "传真", "分机", "邮编",
        "数量", "总价", "单价", "报价", "预算"
    }

    def detect(self, text: str) -> DetectionResult:
        """检测文本中的敏感信息"""
        findings = []

        # 1. 检测手机号（支持格式变形）
        phone_findings = self._detect_phones(text)
        findings.extend(phone_findings)

        # 2. 检测身份证
        id_findings = self._detect_id_cards(text)
        findings.extend(id_findings)

        # 3. 检测银行卡
        bank_findings = self._detect_bank_cards(text)
        findings.extend(bank_findings)

        # 4. 检测邮箱
        email_findings = self._detect_emails(text)
        findings.extend(email_findings)

        # 5. 检测IP
        ip_findings = self._detect_ips(text)
        findings.extend(ip_findings)

        # 去重
        unique_findings = self._deduplicate_findings(findings)

        # 生成摘要
        summary = {cat: 0 for cat in self.CATEGORY_MAP.values()}
        for f in unique_findings:
            summary[f.category] = summary.get(f.category, 0) + 1

        return DetectionResult(
            is_clean=len(unique_findings) == 0,
            findings=unique_findings,
            summary=summary
        )

    def _detect_phones(self, text: str) -> List[SensitiveFinding]:
        """检测手机号（支持多种格式变形）"""
        findings = []
        seen_positions = set()

        # 标准格式: 13812345678 (带边界检查，防止匹配其他数字的子串)
        for match in re.finditer(r"(?<![0-9])1[3-9]\d{9}(?![0-9])", text):
            pos = match.start()
            if pos in seen_positions:
                continue
            phone = match.group()
            if self._is_valid_phone(phone, text, pos):
                findings.append(SensitiveFinding(
                    category="手机号",
                    matched_text=phone,
                    position=pos,
                    severity="medium",
                    validation="format_normalized"
                ))
                seen_positions.add(pos)

        # 分隔格式: 138-1234-5678, 138 1234 5678
        for match in re.finditer(r"(?<![0-9])1[3-9]\d[\s\-]\d{4}[\s\-]\d{4}(?![0-9])", text):
            pos = match.start()
            if pos in seen_positions:
                continue
            phone = match.group()
            normalized = re.sub(r"[\s\-]", "", phone)
            if self._is_valid_phone(normalized, text, pos):
                findings.append(SensitiveFinding(
                    category="手机号",
                    matched_text=phone,
                    position=pos,
                    severity="medium",
                    validation="format_variation"
                ))
                seen_positions.add(pos)

        # 国际格式: +86 13812345678
        for match in re.finditer(r"\+86[\s]?1[3-9]\d{9}", text):
            pos = match.start()
            if pos in seen_positions:
                continue
            phone = match.group()
            normalized = re.sub(r"[\s\+\-]", "", phone)
            if len(normalized) == 12 and normalized.startswith("86"):
                normalized = normalized[2:]
                if self._is_valid_phone(normalized, text, pos):
                    findings.append(SensitiveFinding(
                        category="手机号",
                        matched_text=phone,
                        position=pos,
                        severity="medium",
                        validation="international_format"
                    ))
                    seen_positions.add(pos)

        return findings

    def _is_valid_phone(self, phone: str, text: str, position: int) -> bool:
        """验证手机号合法性"""
        if len(phone) != 11:
            return False

        # 排除某些上下文
        exclude_phrases = ["邮编", "区号", "电话", "传真", "分机"]
        for phrase in exclude_phrases:
            idx = text.rfind(phrase, 0, position)
            if idx >= 0 and position - idx < 10:
                return False

        # 验证号段
        prefix = phone[:3]
        valid_prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                         '145', '147', '149',
                         '150', '151', '152', '153', '155', '156', '157', '158', '159',
                         '166',
                         '170', '171', '172', '173', '175', '176', '177', '178',
                         '180', '181', '182', '183', '184', '185', '186', '187', '188', '189',
                         '190', '191', '193', '195', '197', '198', '199']

        return prefix in valid_prefixes

    def _detect_id_cards(self, text: str) -> List[SensitiveFinding]:
        """检测身份证号"""
        findings = []
        seen_positions = set()

        # 标准化文本：移除圈字、数字形态特殊字符
        normalized_text = self._normalize_text_for_id(text)

        # 标准18位身份证
        for match in re.finditer(r"\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]", normalized_text):
            pos = match.start()
            if pos in seen_positions:
                continue
            id_num = match.group()
            validation = self._validate_id_card(id_num)
            if validation != "invalid":
                findings.append(SensitiveFinding(
                    category="身份证",
                    matched_text=id_num,
                    position=pos,
                    severity="high",
                    validation=validation
                ))
                seen_positions.add(pos)

        # 带空格的身份证: 110101 19900101 1234
        for match in re.finditer(r"\d{6}\s\d{4}\s\d{4}\s\d{3}[\dXx]", normalized_text):
            pos = match.start()
            if pos in seen_positions:
                continue
            id_num = re.sub(r"\s", "", match.group())
            validation = self._validate_id_card(id_num)
            if validation != "invalid":
                findings.append(SensitiveFinding(
                    category="身份证",
                    matched_text=match.group(),
                    position=pos,
                    severity="high",
                    validation="format_with_spaces"
                ))
                seen_positions.add(pos)

        return findings

    def _normalize_text_for_id(self, text: str) -> str:
        """标准化文本，移除可能干扰身份证检测的特殊字符"""
        # 圈字数字映射
        circled_to_digit = {
            '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
            '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '0',
            '⑪': '1', '⑫': '2', '⑬': '3', '⑭': '4', '⑮': '5',
            '⑯': '6', '⑰': '7', '⑱': '8', '⑲': '9', '⑳': '0',
        }
        result = text
        for circled, digit in circled_to_digit.items():
            result = result.replace(circled, digit)
        return result

    def _validate_id_card(self, id_num: str) -> str:
        """验证身份证号"""
        if len(id_num) != 18:
            return "invalid"

        # 验证校验位
        coefficients = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = '10X98765432'

        try:
            sum_val = sum(int(id_num[i]) * coefficients[i] for i in range(17))
            expected_check = check_codes[sum_val % 11]
            actual_check = id_num[-1].upper()

            if actual_check != expected_check:
                return "checksum_failed"
            return "valid"
        except Exception:
            return "invalid"

    def _detect_bank_cards(self, text: str) -> List[SensitiveFinding]:
        """检测银行卡号"""
        findings = []
        seen_positions = set()

        # 匹配可能银行卡号的16-19位数字
        for match in re.finditer(r"\d{16,19}", text):
            pos = match.start()
            if pos in seen_positions:
                continue

            card_num = match.group()
            validation = self._validate_bank_card(card_num, text, pos)

            if validation != "invalid":
                findings.append(SensitiveFinding(
                    category="银行卡",
                    matched_text=card_num,
                    position=pos,
                    severity="high",
                    validation=validation
                ))
                seen_positions.add(pos)

        return findings

    def _validate_bank_card(self, card_num: str, text: str, position: int) -> str:
        """验证银行卡号"""
        if len(card_num) < 16 or len(card_num) > 19:
            return "invalid"

        # 排除明显假阳性：金额上下文
        context_before = text[max(0, position-10):position].lower()
        context_after = text[position+len(card_num):position+len(card_num)+10].lower()

        # 检查金额关键词
        money_keywords = ["元", "万", "千", "百", "金额", "总价", "单价", "报价", "预算", "价格"]
        for kw in money_keywords:
            if kw in context_before or kw in context_after:
                return "invalid"

        # 检查序号关键词
        seq_keywords = ["序号", "编号", "订单号", "流水号", "编码", "序列"]
        for kw in seq_keywords:
            if kw in context_before:
                return "invalid"

        # Luhn算法校验
        if self._luhn_check(card_num):
            return "luhn_valid"

        # 银联/VISA/MASTER卡段验证
        if card_num.startswith("62") or card_num.startswith("4") or card_num.startswith("5"):
            return "prefix_valid"

        return "invalid"

    def _luhn_check(self, card_num: str) -> bool:
        """Luhn算法校验（银行卡校验算法）"""
        try:
            digits = [int(d) for d in card_num]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(divmod(d * 2, 10))
            return checksum % 10 == 0
        except Exception:
            return False

    def _detect_emails(self, text: str) -> List[SensitiveFinding]:
        """检测邮箱"""
        findings = []

        for match in re.finditer(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
            findings.append(SensitiveFinding(
                category="邮箱",
                matched_text=match.group(),
                position=match.start(),
                severity="low",
                validation="regex_match"
            ))

        return findings

    def _detect_ips(self, text: str) -> List[SensitiveFinding]:
        """检测IP地址"""
        findings = []

        for match in re.finditer(r"(?<![0-9])((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?![0-9.])", text):
            ip = match.group(1)
            # 排除常见误判
            if not self._is_private_ip(ip):
                findings.append(SensitiveFinding(
                    category="IP地址",
                    matched_text=ip,
                    position=match.start(),
                    severity="medium",
                    validation="ip_valid"
                ))

        return findings

    def _is_private_ip(self, ip: str) -> bool:
        """检查是否是私有IP（通常是假阳性）"""
        parts = ip.split('.')
        if len(parts) != 4:
            return True

        try:
            p = [int(x) for x in parts]
            # 127.x.x.x 是本地回环
            if p[0] == 127:
                return True
            # 0.x.x.x 或 255.x.x.x 可能是误判
            if p[0] == 0 or p[0] == 255:
                return True
            return False
        except Exception:
            return True

    def _deduplicate_findings(self, findings: List[SensitiveFinding]) -> List[SensitiveFinding]:
        """根据位置去重"""
        seen = set()
        unique = []
        for f in findings:
            key = (f.category, f.position)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def detect_with_context(self, text: str, context_chars: int = 20) -> List[Dict]:
        """检测敏感信息并返回上下文"""
        result = self.detect(text)
        enriched = []
        for f in result.findings:
            start = max(0, f.position - context_chars)
            end = min(len(text), f.position + len(f.matched_text) + context_chars)
            context = text[start:end]
            enriched.append({
                "category": f.category,
                "matched_text": f.matched_text,
                "position": f.position,
                "severity": f.severity,
                "validation": f.validation,
                "context": context,
                "context_start": start,
                "context_end": end
            })
        return enriched

    def detect_file(self, file_path: str) -> DetectionResult:
        """检测文件中的敏感信息"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return self.detect(text)


def quick_test():
    """快速测试"""
    print("=" * 60)
    print("敏感信息检测器 v2.0 测试")
    print("=" * 60)

    detector = SensitiveDetector()

    # 测试手机号变形
    print("\n[手机号测试]")
    phones = ["13812345678", "138-1234-5678", "138 1234 5678", "+86 13812345678"]
    for p in phones:
        result = detector.detect(p)
        status = "✓" if result.findings else "✗"
        print(f"  {status} {p}")

    # 测试身份证变形
    print("\n[身份证测试]")
    ids = [
        "110101199001011234",  # 有效
        "11010119900101123X",  # 有效（校验位X）
        "110101 1990 0101 1234",  # 带空格
    ]
    for id in ids:
        result = detector.detect(id)
        status = "✓" if result.findings else "✗"
        validation = result.findings[0].validation if result.findings else "none"
        print(f"  {status} {id} ({validation})")

    # 测试假阳性排除
    print("\n[假阳性排除测试]")
    false_texts = [
        "金额: 6222021234567890123元",
        "序号: 1234567890123456",
        "订单号: 6222021234567890123",
    ]
    for text in false_texts:
        result = detector.detect(text)
        status = "✗ 误检" if result.findings else "✓ 正确排除"
        print(f"  {status}: {text[:30]}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    quick_test()
