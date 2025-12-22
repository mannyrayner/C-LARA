.PHONY: update-prices docstrings

PRICING_HTML ?= OpenAIPricingInfoDowloaded.html
DOC_MODEL ?= gpt-5.1-codex-max
ONE_VIEW ?= export_zipfile_views

update-prices:
	PYTHONPATH=.. python3 -m clara_self_understanding.update_prices --html $(PRICING_HTML)

docstrings-one:
	PYTHONPATH=.. python3 -c "from clara_self_understanding.docstring_metadata import generate_docstrings_for_one_view_module; generate_docstrings_for_one_view_module('$(ONE_VIEW)', model='$(DOC_MODEL)')"

docstrings:
	PYTHONPATH=.. python3 -c "from clara_self_understanding.docstring_metadata import generate_docstrings_for_all_discovered_views; generate_docstrings_for_all_discovered_views(model='$(DOC_MODEL)')"
