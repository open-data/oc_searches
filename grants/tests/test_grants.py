from common.util import search_path
from playwright.sync_api import Page, expect
import re


def test_page_title_en(page: Page):
    page.goto(search_path('grants', 'en'))
    expect(page).to_have_title("Grants and Contributions")


def test_page_title_fr(page: Page):
    page.goto(search_path('grants', 'fr'))
    expect(page).to_have_title("Subventions et contributions gouvernementales")


def test_not_empty_en(page: Page):
    page.goto(search_path('grants', 'en'))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_simple_search_fr(page: Page):
    page.goto(search_path('grants', 'fr'))
    tb = page.get_by_label("Search text")
    tb.fill('"GC-2018-2019-Q3-00001"')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Should find exactly one record
    expect(count).to_have_text("un")


def test_simple_search_en(page: Page):
    page.goto(search_path('grants', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('"GC-2018-2019-Q3-00001"')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Should find exactly one record
    expect(count).to_have_text("one")


def test_click_facet(page: Page):
    page.goto(search_path('grants', 'en'))
    cb = page.get_by_label("facet-owner_org-tbs-sct")
    # Because of the way Search handles facets, need to use a clock event
    cb.dispatch_event('click')
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text(re.compile(r"[1-9][0-9]*"))


def test_click_amendment(page: Page):
    page.goto(search_path('grants', 'en'))
    cb = page.get_by_label("facet-owner_org-nrc-cnrc")
    # Because of the way Search handles facets, need to use a click event
    cb.dispatch_event('click')
    cb = page.get_by_label("facet-agreement_value_range_en-(g) More than $5,000,000")
    cb.dispatch_event('click')
    cb = page.get_by_label("facet-has_amendments-1")
    cb.dispatch_event('click')
    page.get_by_label("nrc-cnrc,172-2021-2022-Q3-981653,current").click()
    an = page.get_by_test_id("ref_number")
    expect(an).to_contain_text("172-2021-2022-Q3-981653")






