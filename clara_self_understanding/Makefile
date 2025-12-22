.PHONY: update-prices docstrings

PRICING_HTML ?= OpenAIPricingInfoDowloaded.html

update-prices:
	PYTHONPATH=.. python3 -m clara_self_understanding.update_prices --html $(PRICING_HTML)

docstrings:
	PYTHONPATH=.. python3 -c "from clara_self_understanding.docstring_metadata import generate_docstrings_for_all_discovered_views; generate_docstrings_for_all_discovered_views(model='gpt-5.1-codex-max')"
