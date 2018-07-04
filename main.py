from google.appengine.ext import ndb
from google.appengine.api import mail
from flask import Flask
from flask import abort
import feedparser
import time
import ConfigParser

DATE_FORMAT = "%a, %d %b %Y %H:%M:%S UTC"
MAIL_TEMPLATE = """
<html>
    <body>
        <p><a href='%s'>Original post</a> published %s</p>
        <h1>%s</h1>
        <div>%s</div>
    </body>
</html>
"""

app = Flask(__name__)

config = ConfigParser.RawConfigParser()
config.read("main.config")

feedparser.SANITIZE_HTML = False

@app.route('/')
def start_page():
    num_sent = 0

    feedgroups = [s for s in config.sections() if s != "mail"]
    for feedgroup_name in feedgroups:
        url_list = [u.strip() for u in config.get(feedgroup_name, "feeds").split(",")]
        for url in url_list:
            num_sent += poll_blog(url, feedgroup_name)

    return "Polled groups (%s), sent %d updates." % (" ".join(feedgroups), num_sent)


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500

class BlogPost(ndb.Model):
    @classmethod
    def is_post_new(self, ancestor_key, post_id):
        return self.get_by_id(post_id, parent=ancestor_key) == None

def poll_blog(url, feedgroup_name):
    # Count number of e-mails sent
    num_sent = 0

    # Download and parse blog RSS/Atom
    d = feedparser.parse(url)

    # Create an ancestor key based on the blog's url
    ancestor_key = ndb.Key("blog_id", url)

    # Loop over all posts, starting with the oldest
    for entry in d['entries'][::-1]:

        # Figure out if the post is new, or has been seen before
        if BlogPost.is_post_new(ancestor_key, entry.id):

            # Store post's unique id for future reference
            new_post = BlogPost(id = entry.id, parent = ancestor_key)
            new_post.put()

            # Try to create a date/time string
            try:
                formatted_timestamp = time.strftime(DATE_FORMAT, entry.published_parsed)
            except AttributeError:
                try:
                    formatted_timestamp = time.strftime(DATE_FORMAT, entry.updated_parsed)
                except AttributeError:
                    formatted_timestamp = "UNKNOWN"

            # Try and find the posts content
            try:
                content = entry.content[0].value

                # also raise exception if field is just empty
                if not content:
                    raise AttributeError

            except AttributeError:
                try:
                    content = entry.summary_detail.value
                except AttributeError:
                    # give up, we couldn't fine the post's content so might as well skip this one
                    continue

            # Send email containing the new post
            message = mail.EmailMessage()
            message.sender = d.feed.title + " <%s>" % (sender_address(feedgroup_name))
            message.to = [email.strip() for email in config.get("mail", "recipients").split(",")]
            message.subject = entry.title
            message.html = MAIL_TEMPLATE % (entry.link, formatted_timestamp, entry.title, content)
            message.check_initialized()
            message.send()

            num_sent += 1

    return num_sent

def sender_address(feedgroup_name):
    if config.has_option("mail", "sender"):
        return config.get("mail", "sender")
    elif config.has_option("mail", "sender_domain"):
        return "rss+%s@%s" % (feedgroup_name, config.get("mail", "sender_domain"))
    else:
        raise ValueError("No mail.sender nor mail.sender_domain configured.")
