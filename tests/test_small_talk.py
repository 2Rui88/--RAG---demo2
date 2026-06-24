from app.small_talk import TemplateSmallTalkResponder


def test_small_talk_responder_handles_greeting():
    responder = TemplateSmallTalkResponder()

    reply = responder.respond("你好")

    assert "您好" in reply
    assert "学历提升" in reply


def test_small_talk_responder_handles_presence_check():
    responder = TemplateSmallTalkResponder()

    reply = responder.respond("在吗")

    assert "我在" in reply
    assert "报考条件" in reply


def test_small_talk_responder_handles_thanks():
    responder = TemplateSmallTalkResponder()

    reply = responder.respond("谢谢")

    assert "不客气" in reply
    assert "继续问" in reply


def test_small_talk_responder_handles_goodbye():
    responder = TemplateSmallTalkResponder()

    reply = responder.respond("再见")

    assert "随时" in reply
    assert "学历提升" in reply


def test_small_talk_responder_handles_off_topic():
    responder = TemplateSmallTalkResponder()

    reply = responder.respond("今天天气怎么样？", off_topic=True)

    assert "这个我帮不上" in reply
    assert "学历提升" in reply
