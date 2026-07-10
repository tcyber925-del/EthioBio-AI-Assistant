from src.guardrails.output.topic_enforcer import TopicEnforcer


def test_on_topic_biology():
    t = TopicEnforcer()
    result = t.check("Cells are the basic unit of life.")
    assert result.on_topic


def test_on_topic_with_topic_match():
    t = TopicEnforcer()
    result = t.check("Photosynthesis converts light to energy.", topic="Photosynthesis")
    assert result.on_topic


def test_politics_flagged():
    t = TopicEnforcer()
    result = t.check("The election results were surprising this year.")
    assert not result.on_topic
    assert len(result.off_topic_segments) > 0


def test_religion_flagged():
    t = TopicEnforcer()
    result = t.check("God created all living things according to the bible.")
    assert not result.on_topic
