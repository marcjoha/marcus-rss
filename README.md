# marcus-rss
This very crude RSS to email service will  monitor an arbitrary amount of RSS/Atom feeds and send them (reasonably) well-formatted to an email account of your choice.

Before deploying to Google App Engine yo need to
* Rename `main.config.example` to `main.config` and modify to your liking
* Install dependencies into lib/ using `pip install -r requirements.txt -t lib/`
