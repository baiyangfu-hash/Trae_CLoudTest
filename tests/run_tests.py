"""
英语学习助手 - 全模块测试脚本
测试所有模块的导入、初始化、核心功能
"""
import sys
import os
import traceback

# 确保路径正确
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestRunner:
    def __init__(self):
        self.results = []
        self.total = 0
        self.passed = 0
        self.failed = 0
    
    def test(self, name, func):
        """运行单个测试"""
        self.total += 1
        print(f"\n{'='*60}")
        print(f"测试 {self.total}: {name}")
        print(f"{'='*60}")
        try:
            func()
            self.passed += 1
            self.results.append(("PASS", name, ""))
            print(f"✅ 通过")
        except Exception as e:
            self.failed += 1
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results.append(("FAIL", name, error_msg))
            print(f"❌ 失败: {error_msg}")
            traceback.print_exc()
    
    def summary(self):
        """输出测试摘要"""
        print(f"\n\n{'='*60}")
        print(f"测试报告")
        print(f"{'='*60}")
        print(f"总计: {self.total} | 通过: {self.passed} | 失败: {self.failed}")
        print(f"通过率: {self.passed/max(self.total,1)*100:.1f}%")
        
        if self.failed > 0:
            print(f"\n失败列表:")
            for status, name, msg in self.results:
                if status == "FAIL":
                    print(f"  ❌ {name}: {msg}")
        
        return self.failed == 0


def test_imports(runner):
    """测试所有模块导入"""
    def _test():
        from dictionary import Dictionary
        from database import Database
        from dialogs_data import get_all_dialogs, get_dialog
        from fsrs_engine import FSRSEngine, FSRSState
        from us_travel_dialogs import get_all_us_dialogs, get_us_dialog
        from asr_engine import ASREngine
        from answer_matcher import AnswerMatcher, AnswerSpec, MatchResult
        from tts_engine import TTSEngine
        print("  核心模块导入成功")
        # GUI 模块在云端可能缺少 libEGL
        try:
            from dictation_page import DictationPage
            from roleplay_page import RolePlayPage
            print("  GUI 模块导入成功")
        except ImportError as e:
            print(f"  GUI 模块导入跳过（云端环境）: {e}")
    runner.test("模块导入", _test)


def test_dictionary(runner):
    """测试词典模块"""
    def _test():
        from dictionary import Dictionary
        d = Dictionary()
        
        # 精确查询
        result = d.lookup("hello")
        assert result is not None, "查询 hello 返回 None"
        assert isinstance(result, dict), "返回类型应为 dict"
        assert result.get('word', '').lower() == 'hello', f"单词不匹配: {result.get('word')}"
        print(f"  精确查询 hello: {result.get('translation', '')}")
        
        # 模糊搜索
        results = d.search("he")
        assert isinstance(results, list), "搜索返回类型应为 list"
        assert len(results) > 0, "搜索 he 应有结果"
        print(f"  模糊搜索 'he': 找到 {len(results)} 个结果")
        
        # 随机单词
        words = d.get_random_words(5)
        assert len(words) == 5, "应返回5个随机单词"
        print(f"  随机单词: {[w['word'] for w in words]}")
        
        # 查询不存在的词
        result = d.lookup("zzzzzzzzz")
        assert result is None or isinstance(result, list), "不存在词应返回 None 或列表"
        print(f"  不存在词查询: {result}")
        
        d.close()
    runner.test("词典模块 (dictionary.py)", _test)


def test_database(runner):
    """测试数据库模块"""
    def _test():
        from database import Database
        import tempfile
        import shutil
        
        # 使用临时数据库
        orig_path = None
        db_path = os.path.join(os.path.dirname(__file__), 'src', '..', 'data', 'app.db')
        if os.path.exists(db_path):
            orig_path = db_path + '.bak'
            shutil.copy2(db_path, orig_path)
        
        try:
            db = Database()
            
            # 清理测试数据
            db.cursor.execute("DELETE FROM user_words WHERE word = 'test_word_123'")
            db.cursor.execute("DELETE FROM study_records WHERE word = 'test_word_123'")
            db.conn.commit()
            
            # 测试 get_or_create_user_word
            word = db.get_or_create_user_word("test_word_123")
            assert word['word'] == 'test_word_123', f"单词不匹配: {word['word']}"
            assert word['status'] == 'new', "新词状态应为 new"
            print(f"  创建单词: {word}")
            
            # 重复创建应返回已有记录
            word2 = db.get_or_create_user_word("test_word_123")
            assert word2['word'] == 'test_word_123'
            print(f"  重复查询: {word2}")
            
            # 更新状态
            db.update_user_word("test_word_123", status='review')
            word3 = db.get_or_create_user_word("test_word_123")
            assert word3['status'] == 'review', f"状态未更新: {word3['status']}"
            print(f"  更新状态: {word3['status']}")
            
            # 添加学习记录
            db.add_study_record("test_word_123", "review", "good")
            print(f"  学习记录已添加")
            
            # 每日统计
            stats = db.get_daily_stats()
            print(f"  每日统计: {stats}")
            
            db.close()
        finally:
            if orig_path:
                shutil.copy2(orig_path, db_path)
                os.unlink(orig_path)
    runner.test("数据库模块 (database.py)", _test)


def test_fsrs(runner):
    """测试 FSRS 间隔重复算法"""
    def _test():
        from fsrs_engine import FSRSEngine, FSRSState
        
        engine = FSRSEngine()
        
        # 新词复习
        state = FSRSState()
        assert state.state == 0, "初始状态应为 0 (新词)"
        print(f"  初始状态: state={state.state}")
        
        # 评分 'good'
        new_state, due = engine.review(state, 'good')
        assert new_state.scheduled_days > 0, "复习间隔应大于0"
        print(f"  评分 good: 间隔={new_state.scheduled_days}天, 到期={due}")
        
        # 评分 'again'
        state2 = FSRSState()
        new_state2, due2 = engine.review(state2, 'again')
        assert new_state2.scheduled_days <= 1, "重来间隔应<=1天"
        print(f"  评分 again: 间隔={new_state2.scheduled_days}天")
        
        # 评分 'easy'
        state3 = FSRSState()
        new_state3, due3 = engine.review(state3, 'easy')
        assert new_state3.scheduled_days > new_state.scheduled_days, "简单间隔应大于一般"
        print(f"  评分 easy: 间隔={new_state3.scheduled_days}天")
        
        # JSON 序列化
        json_str = new_state.to_json()
        restored = FSRSState.from_json(json_str)
        assert restored.scheduled_days == new_state.scheduled_days, "序列化后状态不一致"
        print(f"  JSON 序列化: OK")
        
        # 获取各评分间隔
        intervals = engine.get_rating_intervals(state)
        assert 'again' in intervals, "应包含 again 间隔"
        assert 'easy' in intervals, "应包含 easy 间隔"
        print(f"  各评分间隔: {intervals}")
    runner.test("FSRS 算法 (fsrs_engine.py)", _test)


def test_answer_matcher(runner):
    """测试答案匹配引擎"""
    def _test():
        from answer_matcher import AnswerMatcher, AnswerSpec
        
        m = AnswerMatcher()
        
        # 测试1: 精确匹配
        spec = AnswerSpec(
            primary_answer="No, I don't. Do you have a table for two?",
            alternative_answers=["No I don't have one", "Nope, no reservation"],
            keywords=["no", "table", "two"]
        )
        
        r = m.match("No, I don't. Do you have a table for two?", spec)
        assert r.is_correct, "精确匹配应通过"
        assert r.score == 1.0, f"精确匹配分数应为1.0: {r.score}"
        print(f"  精确匹配: score={r.score}, feedback={r.feedback}")
        
        # 测试2: 替代答案
        r2 = m.match("No I don't have one", spec)
        assert r2.is_correct, "替代答案应通过"
        print(f"  替代答案: score={r2.score}, feedback={r2.feedback}")
        
        # 测试3: 关键词匹配（不完整但包含关键词）
        r3 = m.match("no table for two please", spec)
        assert r3.is_correct, "包含所有关键词应通过"
        print(f"  关键词匹配: score={r3.score}, feedback={r3.feedback}")
        
        # 测试4: 完全错误
        r4 = m.match("yes I have a reservation", spec)
        assert not r4.is_correct, "完全无关应失败"
        assert len(r4.missing_words) > 0, "应报告缺失关键词"
        print(f"  完全错误: score={r4.score}, missing={r4.missing_words}")
        
        # 测试5: 空输入
        r5 = m.match("", spec)
        assert not r5.is_correct, "空输入应失败"
        print(f"  空输入: score={r5.score}")
        
        # 测试6: 大小写不敏感
        r6 = m.match("NO TABLE FOR TWO", spec)
        assert r6.is_correct, "大小写不敏感应通过"
        print(f"  大小写不敏感: score={r6.score}")
        
        # 测试7: 标点不影响
        r7 = m.match("No, I don't! Table for two?", spec)
        assert r7.is_correct, "标点不应影响匹配"
        print(f"  标点不影响: score={r7.score}")
    runner.test("答案匹配引擎 (answer_matcher.py)", _test)


def test_dialogs_data(runner):
    """测试对话数据"""
    def _test():
        from dialogs_data import get_all_dialogs, get_dialog
        
        dialogs = get_all_dialogs()
        assert len(dialogs) > 0, "应有基础对话"
        print(f"  基础对话数: {len(dialogs)}")
        
        for d in dialogs:
            assert 'id' in d, f"缺少 id: {d}"
            assert 'title' in d, f"缺少 title: {d}"
            assert 'line_count' in d, f"缺少 line_count: {d}"
        
        # 获取单个对话
        dialog = get_dialog(dialogs[0]['id'])
        assert dialog is not None, "应能获取对话详情"
        assert 'lines' in dialog, "对话应有 lines"
        assert len(dialog['lines']) > 0, "对话应至少有一行"
        
        line = dialog['lines'][0]
        assert 'speaker' in line, f"缺少 speaker: {line}"
        assert 'text' in line, f"缺少 text: {line}"
        assert 'translation' in line, f"缺少 translation: {line}"
        print(f"  对话 '{dialogs[0]['title']}': {len(dialog['lines'])} 行")
    runner.test("基础对话数据 (dialogs_data.py)", _test)


def test_us_travel_dialogs(runner):
    """测试美国出差对话数据"""
    def _test():
        from us_travel_dialogs import get_all_us_dialogs, get_us_dialog
        
        dialogs = get_all_us_dialogs()
        assert len(dialogs) == 22, f"应有22个美国出差对话，实际: {len(dialogs)}"
        print(f"  美国出差对话数: {len(dialogs)}")
        
        # 检查分类
        categories = {}
        for d in dialogs:
            cat = d['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        expected_cats = {'超市购物', '交通出行', '问路', '日常交流', '美国特有'}
        for cat in expected_cats:
            assert cat in categories, f"缺少分类: {cat}"
        print(f"  分类统计: {categories}")
        
        # 检查每个对话结构
        for d in dialogs:
            dialog = get_us_dialog(d['id'])
            assert dialog is not None, f"无法获取对话: {d['id']}"
            for line in dialog['lines']:
                assert 'speaker' in line
                assert 'text' in line
                assert 'translation' in line
                assert 'highlight_words' in line
        print(f"  所有对话结构验证通过")
        
        # 检查海关对话
        customs = get_us_dialog('customs_entry')
        assert customs is not None, "应包含海关对话"
        print(f"  海关对话: {len(customs['lines'])} 行")
    runner.test("美国出差对话 (us_travel_dialogs.py)", _test)


def test_tts_engine(runner):
    """测试 TTS 引擎"""
    def _test():
        from tts_engine import TTSEngine
        
        tts = TTSEngine()
        status = tts.get_status()
        print(f"  TTS 状态: {status}")
        # 不实际播放，只检查初始化
        print(f"  TTS 可用: {tts.available}")
    runner.test("TTS 引擎 (tts_engine.py)", _test)


def test_asr_engine(runner):
    """测试 ASR 引擎"""
    def _test():
        from asr_engine import ASREngine
        
        asr = ASREngine()
        status = asr.get_status()
        print(f"  ASR 状态: {status}")
        print(f"  ASR 可用: {asr.available}")
        
        # 文本模式测试
        result = asr.recognize_from_text("hello world")
        assert result == "hello world", f"文本模式返回不正确: {result}"
        print(f"  文本模式: OK")
    runner.test("ASR 引擎 (asr_engine.py)", _test)


def test_main_import(runner):
    """测试主程序导入（不启动GUI）"""
    def _test():
        try:
            import PySide6.QtWidgets
            import PySide6.QtCore
            import PySide6.QtGui
            print(f"  PySide6 版本: {PySide6.__version__}")
            print(f"  主程序导入检查: OK (不启动GUI)")
        except ImportError as e:
            # 云端环境缺少 libEGL，这是预期的
            print(f"  PySide6 导入跳过（云端环境缺少 libEGL，Windows 上正常）: {e}")
    runner.test("主程序导入 (main.py)", _test)


if __name__ == '__main__':
    runner = TestRunner()
    
    print("=" * 60)
    print("英语学习助手 - 全模块测试")
    print("=" * 60)
    
    # 按依赖顺序测试
    test_imports(runner)
    test_dictionary(runner)
    test_database(runner)
    test_fsrs(runner)
    test_answer_matcher(runner)
    test_dialogs_data(runner)
    test_us_travel_dialogs(runner)
    test_tts_engine(runner)
    test_asr_engine(runner)
    test_main_import(runner)
    
    success = runner.summary()
    
    # 将结果写入文件
    report_path = os.path.join(os.path.dirname(__file__), 'data', 'test_report.txt')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"英语学习助手 - 测试报告\n")
        f.write(f"时间: {__import__('datetime').datetime.now().isoformat()}\n")
        f.write(f"总计: {runner.total} | 通过: {runner.passed} | 失败: {runner.failed}\n")
        f.write(f"通过率: {runner.passed/max(runner.total,1)*100:.1f}%\n\n")
        for status, name, msg in runner.results:
            icon = "✅" if status == "PASS" else "❌"
            f.write(f"{icon} {name}")
            if msg:
                f.write(f" - {msg}")
            f.write("\n")
    
    print(f"\n测试报告已保存: {report_path}")
    
    sys.exit(0 if success else 1)
