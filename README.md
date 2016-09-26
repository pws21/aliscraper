# aliscraper

Scraper of Aliexpress product variants. Take url, scrape all variants and save to local db.

Consists of two parts:

1. Web front end on Flask, which allow to take requests with url for scraping and save result to db

2. Threaded runner for mass scrapping, which use Tor network for hidding from anti-spiders. It works with multiple retrys, identity changing and other tricky staff.
