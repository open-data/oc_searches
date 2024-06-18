from common.util import search_path
from playwright.sync_api import Page, expect
import re


def test_page_title_en(page: Page):
    page.goto(search_path('contracts', 'en'))
    expect(page).to_have_title("Search Government Contracts over $10,000")


def test_page_title_fr(page: Page):
    page.goto(search_path('contracts', 'fr'))
    expect(page).to_have_title("Recherche des contrats gouvernementaux de plus de 10 000 $")


def test_simple_search_en(page: Page):
    page.goto(search_path('contracts', 'en', path="?sort=contract_date+desc&search_text=microsoft&page=1"))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_simple_search_fr(page: Page):
    page.goto(search_path('contracts', 'en', path="?sort=contract_date+desc&search_text=microsoft&page=1"))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_submit_simple_search_en(page: Page):
    page.goto(search_path('contracts', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('microsoft')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_submit_simple_search_fr(page: Page):
    page.goto(search_path('contracts', 'fr'))
    tb = page.get_by_label("Search text")
    tb.fill('microsoft')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_search_by_procurement_id(page: Page):
    page.goto(search_path('contracts', 'en', path="?search_text=2406224262"))
    count = page.get_by_test_id("itemsfound")
    expect(count).to_have_text("one")


def test_record_by_procurement_id(page: Page):
    page.goto(search_path('contracts', 'en', path="/record/tbs-sct,C-2023-2024-Q3-00033"))
    proc_id = page.get_by_test_id("procurement_id")
    expect(proc_id).to_contain_text("2406224262")


def test_amendment_by_procurement_id(page: Page):
    page.goto(search_path('contracts', 'en', path="/record/cic,7118307?amendments"))
    proc_id = page.get_by_test_id("procurement_id").first
    expect(proc_id).to_contain_text("7118307")
