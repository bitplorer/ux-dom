- **Fix: a comment ends where a browser ends it.** ``<!-->`` and ``<!--->`` are
  empty comments, so ``<!-->a<b>b</b>-->c`` keeps ``a<b>b</b>--&gt;c`` instead of
  dropping it all as one comment. The parser no longer imports the private
  ``html.parser.commentclose``; the WHATWG rule is ux-dom's own, and the stream
  sanitizer cuts right after ``<!-->``. ``sanitize_html_stream`` documents its
  memory budget; ``MAX_BUFFER_CHARS`` stays ``1 << 20`` (#124).
