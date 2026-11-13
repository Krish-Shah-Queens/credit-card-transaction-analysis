from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_all_python_dashboard_pages_render_without_exceptions():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    for page in ["Transaction activity", "Source fraud labels", "Model evaluation", "Score transactions", "Data explorer", "Data & method"]:
        app.radio(key="page").set_value(page).run()
        assert not app.exception, page


def test_model_threshold_changes_predictions_and_preserves_source_analysis():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    original_count = app.metric[1].value
    app.radio(key="page").set_value("Model evaluation").run()
    assert app.metric[0].value == "64"
    app.slider(key="threshold").set_value(0.).run()
    assert not app.exception
    assert app.metric[0].value == "56,746"
    assert app.metric[2].value == "100.00%"
    app.radio(key="page").set_value("Payments overview").run()
    assert not app.exception
    assert app.metric[1].value == original_count == "284,807"


def test_empty_analysis_filters_do_not_crash():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.number_input(key="minimum").set_value(30000.)
    app.number_input(key="maximum").set_value(40000.)
    app.run()
    assert not app.exception
    assert app.metric[1].value == "0"
    assert app.warning


def test_analysis_filters_survive_a_visit_to_model_pages():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.slider(key="hours").set_value((12, 23)).run()
    count = app.metric[1].value
    app.radio(key="page").set_value("Model evaluation").run()
    app.radio(key="page").set_value("Payments overview").run()
    assert not app.exception
    assert app.slider(key="hours").value == (12, 23)
    assert app.metric[1].value == count
